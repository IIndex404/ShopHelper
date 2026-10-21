"""把用户自然语言转换为可执行的三轨 TurnPlan。"""

import json
import re
from typing import Any

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate

from atguigu.domain.state import DialogueState
from atguigu.infrastructure.llm import llm
from atguigu.knowledge.intents import KnowledgeIntent
from atguigu.plan.models import TurnPlan
from atguigu.prompts.history_builder import HistoryBuilder
from atguigu.prompts.loader import load_prompt
from atguigu.task.flow.flows import FlowsList
from atguigu.task.flow.steps import CollectFlowStep


class TurnPlanner:
    async def predict(
        self,
        state: DialogueState,
        flows: FlowsList,
        intents: dict[str, KnowledgeIntent],
    ) -> TurnPlan:
        text = (state.pending_turn.user_message.text or '').strip()
        # While collecting a reason, '不再需要' is data, not an inferred cancellation.
        active = state.active_task
        if active and active.flow_id == 'refund_request':
            flow = flows.get_flow_by_id(active.flow_id)
            step = flow.get_step_by_id(active.step_id)
            if isinstance(step, CollectFlowStep) and step.slot_name == 'refund_reason':
                if text in {'取消', '取消退款', '取消申请', '算了', '不办了'}:
                    return TurnPlan.from_dict({'task': {'commands': [{'command': 'cancel_flow'}]}})
                if not any(w in text for w in ('查物流', '查询物流', '查订单', '查询订单', '退款进度')):
                    return TurnPlan.from_dict({'task': {'commands': [
                        {'command': 'set_slots', 'slots': {'refund_reason': text}}]}})
        if state.pending_refund:
            # A pending write is never confirmed by model inference.
            if not ('退款' in text and any(w in text for w in ('进度', '记录', '申请编号', '审核结果', '成功了吗', '到账了吗', '处理到哪', '处理了吗'))) and state.active_task is None:
                return TurnPlan.from_dict({'chitchat': {}})
        if '退款' in text and any(w in text for w in ('进度', '记录', '申请编号', '审核结果', '成功了吗', '到账了吗', '处理到哪', '处理了吗')):
            return self._fallback_predict(state, flows)
        inputs = self._build_prompt_inputs(state, flows, intents)
        if llm is None:
            return self._fallback_predict(state, flows)
        try:
            template = PromptTemplate.from_template(
                load_prompt("turn_plan"), template_format="jinja2"
            )
            response: dict[str, Any] = await (
                template | llm | JsonOutputParser()
            ).ainvoke(inputs)
            plan = TurnPlan.from_dict(response)
            # Bind an explicitly typed order id even when the model omits that slot.
            match = re.search(r"[A-Za-z][0-9]{6,}", text)
            if plan.task and match:
                from atguigu.task.command.models import StartFlowCommand, SetSlotsCommand
                starts = [cmd for cmd in plan.task.commands if isinstance(cmd, StartFlowCommand)]
                if starts:
                    flow = flows.get_flow_by_id(starts[0].flow)
                    if flow and any(slot.name == 'order_number' for slot in flow.slots):
                        plan.task.commands.append(SetSlotsCommand(command='set_slots', slots={'order_number': match.group(0)}))
            return plan
        except Exception:
            return self._fallback_predict(state, flows)

    @staticmethod
    def _build_prompt_inputs(
        state: DialogueState,
        flows: FlowsList,
        intents: dict[str, KnowledgeIntent],
    ) -> dict[str, Any]:
        pending = state.pending_turn
        if pending is None:
            raise RuntimeError("规划前必须先 begin_turn")
        session = state.current_session()
        flow_summaries = []
        for flow in flows.flows:
            if flow.id.startswith("system_"):
                continue
            data = flow.model_dump(mode="json", exclude={"steps"})
            flow_summaries.append(data)
        return {
            "user_message": HistoryBuilder.render_user_message(pending.user_message),
            "current_conversation": HistoryBuilder.build(
                session.turns[-10:] if session else []
            ),
            "active_task_json": state.active_task.model_dump_json()
            if state.active_task
            else None,
            "interrupted_tasks_json": json.dumps(
                [task.model_dump(mode="json") for task in state.paused_tasks],
                ensure_ascii=False,
            ),
            "focused_object_json": state.focused_object.model_dump_json()
            if state.focused_object
            else None,
            "available_flows_json": json.dumps(
                {"flows": flow_summaries}, ensure_ascii=False
            ),
            "knowledge_intents_json": json.dumps(
                [
                    {"id": intent.id, "description": intent.description}
                    for intent in intents.values()
                ],
                ensure_ascii=False,
            ),
        }

    @staticmethod
    def _fallback_predict(state: DialogueState, flows: FlowsList) -> TurnPlan:
        """没有配置 LLM 时仍可完整演示流程。"""
        text = (state.pending_turn.user_message.text or "").strip()
        lower = text.lower()

        if text in {"取消", "取消退款", "取消申请", "算了", "不办了"}:
            return TurnPlan.from_dict(
                {"task": {"commands": [{"command": "cancel_flow"}]}}
            )
        if any(word in text for word in ("继续", "恢复", "接着")):
            return TurnPlan.from_dict(
                {"task": {"commands": [{"command": "resume_flow"}]}}
            )

        if "退款" in text and any(w in text for w in ("进度", "记录", "申请编号", "审核结果", "成功了吗", "到账了吗", "处理到哪", "处理了吗")):
            requested_flow = "refund_status_query"
        elif "退款" in text and not any(w in text for w in ("政策", "规则", "多久到账")):
            requested_flow = "refund_request"
        elif "物流" in text or "快递" in text:
            requested_flow = "logistics_tracking"
        elif "订单状态" in text or ("查" in text and "订单" in text):
            requested_flow = "order_status_query"
        else:
            requested_flow = ""

        active = state.active_task
        if requested_flow and (active is None or active.flow_id != requested_flow):
            match = re.search(r"[A-Za-z][A-Za-z0-9_-]{4,}", text)
            if match:
                return TurnPlan.from_dict({'task': {'commands': [
                    {'command': 'start_flow', 'flow': requested_flow},
                    {'command': 'set_slots', 'slots': {'order_number': match.group(0)}}]}})
            return TurnPlan.from_dict(
                {
                    "task": {
                        "commands": [
                            {"command": "start_flow", "flow": requested_flow}
                        ]
                    }
                }
            )

        if active is not None:
            flow = flows.get_flow_by_id(active.flow_id)
            step = flow.get_step_by_id(active.step_id) if flow else None
            if isinstance(step, CollectFlowStep):
                value = text
                if step.slot_name == "order_number":
                    match = re.search(r"[A-Za-z][A-Za-z0-9_-]{4,}", text)
                    value = match.group(0) if match else text.replace("订单号", "").strip()
                return TurnPlan.from_dict(
                    {
                        "task": {
                            "commands": [
                                {
                                    "command": "set_slots",
                                    "slots": {step.slot_name: value},
                                }
                            ]
                        }
                    }
                )

        if requested_flow:
            return TurnPlan.from_dict(
                {
                    "task": {
                        "commands": [
                            {"command": "start_flow", "flow": requested_flow}
                        ]
                    }
                }
            )

        if "退款" in text:
            intent = "refund_policy"
        elif "退货" in text or "七天" in text:
            intent = "return_policy"
        elif "发货" in text or "配送" in text:
            intent = "shipping_policy"
        elif state.focused_object and state.focused_object.type == "product":
            intent = "product_info"
        elif state.focused_object and state.focused_object.type == "order":
            intent = "order_info"
        elif any(word in lower for word in ("商品", "价格", "材质", "product")):
            intent = "product_info"
        else:
            intent = ""
        if intent:
            return TurnPlan.from_dict({"knowledge": {"intents": [intent]}})
        return TurnPlan.from_dict({"chitchat": {}})

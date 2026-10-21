from typing import Any

from atguigu.domain.state import DialogueState
from atguigu.task.action.base import Action, ActionResult
from atguigu.task.action.custom.shared import fetch_order


class LookupOrderStatusAction(Action):
    name = "action_lookup_order_status"

    async def run(
        self, state: DialogueState, action_kwargs: dict[str, Any]
    ) -> ActionResult:
        order_number = state.active_task.slots.get("order_number")
        data = await fetch_order(str(order_number))
        if data is None:
            return ActionResult(
                slot_updates={
                    "order_status": "查询失败",
                    "order_summary": "暂时无法查到该订单信息，请检查订单号或稍后再试。",
                }
            )
        items = data.get("items") or []
        title = items[0].get("title") if items else "未知商品"
        suffix = "" if len(items) <= 1 else "等"
        summary = f"订单金额 ¥{data.get('amount')}。商品：{title}{suffix}。"
        return ActionResult(
            slot_updates={
                "order_status": data.get("status_desc") or data.get("status") or "未知",
                "order_summary": summary,
            }
        )

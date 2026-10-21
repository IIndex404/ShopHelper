from typing import Any

from atguigu.domain.state import DialogueState
from atguigu.task.action.base import Action, ActionResult
from atguigu.task.action.custom.shared import fetch_logistics


class LookupLogisticsAction(Action):
    name = "action_lookup_logistics"

    async def run(
        self, state: DialogueState, action_kwargs: dict[str, Any]
    ) -> ActionResult:
        order_number = state.active_task.slots.get("order_number")
        data = await fetch_logistics(str(order_number))
        if data is None:
            return ActionResult(
                slot_updates={
                    "tracking_number": "未知",
                    "logistics_company": "未知",
                    "logistics_status": "暂时无法查到物流信息，请稍后再试。",
                }
            )
        return ActionResult(
            slot_updates={
                "tracking_number": data.get("tracking_number") or "未知",
                "logistics_company": data.get("logistics_company") or "未知",
                "logistics_status": data.get("status_desc") or data.get("status") or "未知",
            }
        )

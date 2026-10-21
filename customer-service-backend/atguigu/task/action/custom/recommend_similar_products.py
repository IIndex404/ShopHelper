from typing import Any

from atguigu.domain.state import DialogueState
from atguigu.task.action.base import Action, ActionResult
from atguigu.task.action.custom.shared import fetch_product


class RecommendSimilarProductsAction(Action):
    name = "action_recommend_similar_products"

    async def run(
        self, state: DialogueState, action_kwargs: dict[str, Any]
    ) -> ActionResult:
        product_id = state.active_task.slots.get("product_id")
        data = await fetch_product(str(product_id))
        return ActionResult(
            slot_updates={
                "product_title": (
                    data.get("title")
                    if data
                    else "暂时无法查到商品，请稍后再试。"
                )
            }
        )

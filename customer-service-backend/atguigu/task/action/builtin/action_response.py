from typing import Any

from jinja2 import Template
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from atguigu.domain.messages import BotMessage
from atguigu.domain.state import DialogueState
from atguigu.infrastructure.llm import llm
from atguigu.prompts.history_builder import HistoryBuilder
from atguigu.task.action.base import Action, ActionResult


class ActionResponse(Action):
    name = "action_response"

    async def run(
        self, state: DialogueState, action_kwargs: dict[str, Any]
    ) -> ActionResult:
        mode = action_kwargs.get("mode", "static")
        rendered = self._render_text(action_kwargs.get("text", ""), state)
        if mode == "static" or llm is None:
            return ActionResult(messages=[BotMessage(text=rendered)])

        prompt_text = action_kwargs.get("prompt")
        if not prompt_text:
            return ActionResult(messages=[BotMessage(text=rendered)])
        try:
            prompt = PromptTemplate.from_template(prompt_text)
            chain = prompt | llm | StrOutputParser()
            session = state.current_session()
            message = await chain.ainvoke(
                {
                    "history": HistoryBuilder.build(session.turns if session else []),
                    "user_message": HistoryBuilder.render_user_message(
                        state.pending_turn.user_message
                    ),
                    "current_response": rendered,
                }
            )
        except Exception:
            message = rendered
        return ActionResult(messages=[BotMessage(text=message)])

    @staticmethod
    def _render_text(text: str, state: DialogueState) -> str:
        return Template(text).render(
            slots=state.active_task.slots if state.active_task else {},
            context=state.active_system_task or state.active_task,
        )

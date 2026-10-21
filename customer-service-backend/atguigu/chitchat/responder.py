from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from atguigu.domain.messages import BotMessage, UserMessage
from atguigu.domain.state import Turn
from atguigu.infrastructure.llm import llm
from atguigu.prompts.history_builder import HistoryBuilder
from atguigu.prompts.loader import load_prompt


class ChitChatResponder:
    async def respond(
        self, user_message: UserMessage, recent_turns: list[Turn]
    ) -> list[BotMessage]:
        if llm is None:
            return [
                BotMessage(
                    text="你好，我可以帮你查订单状态、查物流、咨询商品信息或申请退款。"
                )
            ]
        try:
            prompt = PromptTemplate.from_template(
                load_prompt("chitchat_respond"), template_format="jinja2"
            )
            answer = await (prompt | llm | StrOutputParser()).ainvoke(
                {
                    "user_message": HistoryBuilder.render_user_message(user_message),
                    "history": HistoryBuilder.build(recent_turns),
                }
            )
            return [BotMessage(text=answer)]
        except Exception:
            return [BotMessage(text="你好，请问有什么电商问题需要我帮忙？")]

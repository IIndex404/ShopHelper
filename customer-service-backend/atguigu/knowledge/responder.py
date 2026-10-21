from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from atguigu.domain.messages import BotMessage, UserMessage
from atguigu.domain.state import Turn
from atguigu.infrastructure.llm import llm
from atguigu.knowledge.providers import KnowledgeChunk
from atguigu.prompts.history_builder import HistoryBuilder
from atguigu.prompts.loader import load_prompt


class KnowledgeResponder:
    async def respond(
        self,
        user_message: UserMessage,
        recent_turns: list[Turn],
        chunks: list[KnowledgeChunk],
    ) -> list[BotMessage]:
        content = "\n\n".join(chunk.content for chunk in chunks)
        if llm is None:
            return [BotMessage(text=content or "暂时没有检索到相关信息。")]
        try:
            prompt = PromptTemplate.from_template(
                load_prompt("knowledge_respond"), template_format="jinja2"
            )
            answer = await (prompt | llm | StrOutputParser()).ainvoke(
                {
                    "user_message": HistoryBuilder.render_user_message(user_message),
                    "history": HistoryBuilder.build(recent_turns),
                    "knowledge_content": content,
                }
            )
            return [BotMessage(text=answer)]
        except Exception:
            return [BotMessage(text=content or "暂时没有检索到相关信息。")]

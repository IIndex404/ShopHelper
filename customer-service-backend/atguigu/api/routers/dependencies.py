from pathlib import Path
from functools import lru_cache
from fastapi import Depends
from atguigu.infrastructure import database
from atguigu.repository.dialogue_state_repository import DialogueStateRepository
from atguigu.service.dialogue_service import DialogueService
from atguigu.engine.dialogue_engine import DialogueEngine
from atguigu.plan.turn_planner import TurnPlanner
from atguigu.plan.turn_validator import TurnPlanValidator
from atguigu.task.handler import TaskHandler
from atguigu.task.command.processor import CommandProcessor
from atguigu.task.action.builder import build_action_runner
from atguigu.task.flow.executor import FlowExecutor
from atguigu.task.flow.loader import FlowLoader
from atguigu.knowledge.handler import KnowledgeHandler
from atguigu.knowledge.intents import KNOWLEDGE_INTENTS
from atguigu.knowledge.providers import FAQProvider, RAGProvider, ProductAPIProvider, OrderAPIProvider
from atguigu.knowledge.registry import KnowledgeProviderRegistry
from atguigu.knowledge.responder import KnowledgeResponder
from atguigu.chitchat.handler import ChitChatHandler
from atguigu.chitchat.responder import ChitChatResponder
from atguigu.clarify.responder import ClarifyResponder

@lru_cache
def get_flows():
    config = Path(__file__).resolve().parents[3] / 'flow_config'
    return FlowLoader().load_many([config / 'system_flows.yml', config / 'user_flows.yml'])

async def get_session():
    async with database.async_session() as session:
        yield session

async def get_dialogue_state_repository(session=Depends(get_session)):
    return DialogueStateRepository(session)

def get_engine():
    return DialogueEngine(
        turn_planner=TurnPlanner(),
        task_handler=TaskHandler(get_flows(), CommandProcessor(), build_action_runner(), FlowExecutor()),
        knowledge_handler=KnowledgeHandler(KNOWLEDGE_INTENTS,
            KnowledgeProviderRegistry([FAQProvider(), RAGProvider(), ProductAPIProvider(), OrderAPIProvider()]),
            KnowledgeResponder()),
        chitchat_handler=ChitChatHandler(ChitChatResponder()),
        clarify_responder=ClarifyResponder(), turn_plan_validator=TurnPlanValidator())

async def get_dialogue_service(repository=Depends(get_dialogue_state_repository), engine=Depends(get_engine)):
    return DialogueService(repository, engine)

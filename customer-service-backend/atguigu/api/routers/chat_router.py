from atguigu.api.routers.dependencies import get_dialogue_service
import uuid

from fastapi import APIRouter, Depends

from atguigu.api.routers.dependencies import get_dialogue_service
from atguigu.api.schemas import (
    ChatRequest,
    ChatResponse,
    ChatBotMessage,
    ChatObject,
    HistoryResponse,
    HistoryMessage
)
from atguigu.domain.messages import (
    ProcessResult,
    UserMessage,
    MessageType,
    FocusedObject
)
from atguigu.service.dialogue_service import DialogueService
# 创建一个路由对象
router = APIRouter()
@router.post("/api/chat")
async def chat_endpoint(
    chat_request: ChatRequest,
    dialogue_service:DialogueService = Depends(get_dialogue_service)
)-> ChatResponse:
    # 1. 把前端传来的ChatRequest转成内部使用的UserMessage
    user_message = _build_user_message(chat_request)
    # 2. 交给Service处理这一轮消息
    process_result:ProcessResult = await dialogue_service.process_message(user_message)
    # 3. 把Service返回的ProcessResult转成前端需要的ChatResponse
    return _build_chat_response(process_result)
def _build_user_message(chat_request: ChatRequest) -> UserMessage : 
    """
    把前端请求对象转成内部UserMessage
    """  
    return UserMessage(
        sender_id = chat_request.sender_id,
        message_id = chat_request.message_id 
        if chat_request.message_id 
        else str(uuid.uuid4()),
        type=MessageType.TEXT
        if chat_request.text
        else MessageType.OBJECT,
        text=chat_request.text,
        object=FocusedObject(
            id=chat_request.object.id,
            type=chat_request.object.type,
            title=chat_request.object.title,
            attributes=chat_request.object.attributes
        ) if chat_request.object else None
    )
def _build_chat_response(process_result: ProcessResult) -> ChatResponse:
    """
    把内部处理结果转成前端需要的返回格式
    """
    return ChatResponse(
        sender_id=process_result.sender_id,
        message_id=process_result.message_id,
        messages=[
            ChatBotMessage(
                text=bot_message.text,
                suggestions=bot_message.suggestions,
                object=ChatObject(
                    id=bot_message.object.id,
                    type=bot_message.object.type,
                    title=bot_message.object.title,
                    attributes=bot_message.object.attributes
                ) if bot_message.object else None
            )
            for bot_message in process_result.messages
        ]
    )
@router.get('/api/chat/history', response_model=HistoryResponse)
async def history(sender_id: str, dialogue_service=Depends(get_dialogue_service)):
    return HistoryResponse(sender_id=sender_id, messages=await dialogue_service.load_chat_history(sender_id))

@router.post('/api/chat/new-session')
async def new_session(request: ChatRequest, dialogue_service=Depends(get_dialogue_service)):
    await dialogue_service.new_session(request.sender_id)
    return {'status': 'ok'}

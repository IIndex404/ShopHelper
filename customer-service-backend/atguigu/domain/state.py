"""整个用户会话的聚合状态。"""

import time
import uuid
from typing import Any

from pydantic import BaseModel, Field

from atguigu.domain.contexts import SystemContextUnion, TaskContext
from atguigu.domain.messages import BotMessage, FocusedObject, UserMessage


class Turn(BaseModel):
    turn_id: str
    user_message: UserMessage
    bot_messages: list[BotMessage] = Field(default_factory=list)


class Session(BaseModel):
    session_id: str
    started_at: float
    last_activity_at: float
    closed_at: float | None = None
    turns: list[Turn] = Field(default_factory=list)


class DialogueState(BaseModel):
    sender_id: str
    pending_refund: dict[str, Any] | None = None
    active_task: TaskContext | None = None
    paused_tasks: list[TaskContext] = Field(default_factory=list)
    active_system_task: SystemContextUnion | None = None
    focused_object: FocusedObject | None = None
    sessions: list[Session] = Field(default_factory=list)
    current_session_id: str | None = None
    pending_turn: Turn | None = None

    def start_active_task(self, active_task: TaskContext) -> None:
        self.active_task = active_task

    def end_active_task(self) -> None:
        self.active_task = None

    def cancel_active_task(self) -> None:
        self.active_task = None
        self.active_system_task = None

    def interrupted_active_task(self) -> bool:
        if self.active_task is None:
            return False
        self.paused_tasks.append(self.active_task)
        self.active_task = None
        return True

    def resumed_active_task(self, flow_id: str | None = None) -> bool:
        if not self.paused_tasks:
            return False
        if flow_id is None:
            self.active_task = self.paused_tasks.pop()
            return True
        for index in range(len(self.paused_tasks) - 1, -1, -1):
            if self.paused_tasks[index].flow_id == flow_id:
                self.active_task = self.paused_tasks.pop(index)
                return True
        return False

    def start_active_system_task(self, active_system_task: SystemContextUnion) -> None:
        self.active_system_task = active_system_task

    def end_active_system_task(self) -> None:
        self.active_system_task = None

    def current_active_task(self) -> SystemContextUnion | TaskContext | None:
        return self.active_system_task or self.active_task

    def set_slots(self, slots: dict[str, Any]) -> None:
        if self.active_task is not None:
            self.active_task.slots.update(slots)

    def remove_slot(self, slot_name: str) -> None:
        if self.active_task is not None:
            self.active_task.slots.pop(slot_name, None)

    def current_session(self) -> Session | None:
        return next(
            (s for s in self.sessions if s.session_id == self.current_session_id),
            None,
        )

    def start_session(self) -> Session:
        current = self.current_session()
        if current is not None:
            return current
        now = time.time()
        session = Session(
            session_id=str(uuid.uuid4()),
            started_at=now,
            last_activity_at=now,
        )
        self.sessions.append(session)
        self.current_session_id = session.session_id
        return session

    def close_current_session(self) -> None:
        current = self.current_session()
        if current is not None:
            current.closed_at = time.time()
        self.current_session_id = None

    def reset_runtime_state_for_new_session(self) -> None:
        self.active_task = None
        self.paused_tasks = []
        self.active_system_task = None
        self.focused_object = None
        self.pending_refund = None
        self.current_session_id = None
        self.pending_turn = None

    def begin_turn(self, message: UserMessage) -> None:
        if self.current_session() is None:
            self.start_session()
        self.pending_turn = Turn(
            turn_id=str(uuid.uuid4()),
            user_message=message,
        )

    def commit_turn(self) -> None:
        session = self.current_session()
        if session is None or self.pending_turn is None:
            return
        session.turns.append(self.pending_turn)
        session.last_activity_at = time.time()
        self.pending_turn = None

    def set_focused_object(self, focused_object: FocusedObject) -> None:
        self.focused_object = focused_object

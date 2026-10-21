import unittest

from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from atguigu.api.app import app
from atguigu.api.routers.dependencies import get_dialogue_service
from atguigu.domain.messages import BotMessage, ProcessResult


class StubDialogueService:
    async def process_message(self, message):
        return ProcessResult(
            sender_id=message.sender_id,
            message_id=message.message_id,
            messages=[BotMessage(text=f"收到：{message.text}")],
        )

    async def load_chat_history(self, sender_id):
        return []


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.dependency_overrides[get_dialogue_service] = lambda: StubDialogueService()
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        cls.client.close()
        app.dependency_overrides.clear()

    def test_chat_endpoint_converts_models(self):
        response = self.client.post(
            "/api/chat",
            json={"sender_id": "u1001", "text": "你好"},
        )
        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual("u1001", payload["sender_id"])
        self.assertEqual("收到：你好", payload["messages"][0]["text"])

    def test_history_endpoint(self):
        response = self.client.get("/api/chat/history?sender_id=u1001")
        self.assertEqual(200, response.status_code)
        self.assertEqual([], response.json()["messages"])

    def test_empty_message_is_rejected(self):
        response = self.client.post("/api/chat", json={"sender_id": "u1001"})
        self.assertEqual(422, response.status_code)

    def test_database_failure_returns_friendly_json(self):
        def unavailable():
            raise OperationalError("SELECT 1", {}, RuntimeError("private connection info"))

        app.dependency_overrides[get_dialogue_service] = unavailable
        try:
            response = self.client.post(
                "/api/chat", json={"sender_id": "test", "text": "查询订单状态"}
            )
            self.assertEqual(503, response.status_code)
            self.assertIn("数据库连接失败", response.json()["detail"])
            self.assertNotIn("private connection info", response.text)
        finally:
            app.dependency_overrides[get_dialogue_service] = lambda: StubDialogueService()


if __name__ == "__main__":
    unittest.main()

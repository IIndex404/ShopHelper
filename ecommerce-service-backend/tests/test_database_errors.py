import unittest

from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.app import app
from app.database import get_db


class DatabaseErrorTests(unittest.TestCase):
    def test_database_failure_returns_json_without_credentials(self):
        def unavailable():
            raise OperationalError("SELECT 1", {}, RuntimeError("private connection info"))

        app.dependency_overrides[get_db] = unavailable
        try:
            with TestClient(app) as client:
                response = client.get("/users/u1001/orders")
            self.assertEqual(503, response.status_code)
            self.assertIn("数据库连接失败", response.json()["detail"])
            self.assertNotIn("private connection info", response.text)
        finally:
            app.dependency_overrides.clear()


if __name__ == "__main__":
    unittest.main()

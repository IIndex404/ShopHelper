import unittest
from datetime import datetime
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.app import app
from app.database import get_db
from app.models import Base, User, Order, RefundRequest

class RefundApiTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(self.engine)
        with self.Session() as db:
            user = User(user_id='u1001', nickname='测试用户', level='普通', mobile_masked='138****0000', created_at=datetime.now())
            db.add(user)
            db.flush()
            db.add(Order(order_id='A123456', user_id=user.id, status='待发货', status_desc='备货中',
                amount=Decimal('10.00'), created_at=datetime.now(), receiver_name='测试', receiver_phone_masked='138****0000', receiver_address='测试地址'))
            db.commit()
        def get_session():
            with self.Session() as db:
                yield db
        app.dependency_overrides[get_db] = get_session
        self.client = TestClient(app)
        self.body = {'submitted_by': 'u1001', 'reason': '不再需要', 'request_id': 'R12345678'}
        self.url = '/orders/A123456/refund-applications'

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()
        self.engine.dispose()

    def test_submit_query_and_idempotent_replay(self):
        first = self.client.post(self.url, json=self.body)
        self.assertEqual(200, first.status_code, first.text)
        self.assertEqual(first.json(), self.client.post(self.url, json=self.body).json())
        response = self.client.get(self.url, params={'submitted_by': 'u1001'})
        self.assertEqual(1, len(response.json()['data']['applications']))
        with self.Session() as db:
            self.assertEqual(1, db.query(RefundRequest).count())

    def test_second_request_id_conflicts(self):
        self.client.post(self.url, json=self.body)
        self.body['request_id'] = 'R87654321'
        self.assertEqual(409, self.client.post(self.url, json=self.body).status_code)

    def test_other_demo_user_cannot_operate_order(self):
        self.body['submitted_by'] = 'u1002'
        self.assertEqual(404, self.client.post(self.url, json=self.body).status_code)
        self.assertEqual(404, self.client.get(self.url, params={'submitted_by': 'u1002'}).status_code)

    def test_cancelled_order_rejected(self):
        with self.Session() as db:
            db.query(Order).update({'status': '已取消'})
            db.commit()
        self.assertEqual(422, self.client.post(self.url, json=self.body).status_code)

    def test_empty_reason_rejected(self):
        self.body['reason'] = '  '
        self.assertEqual(422, self.client.post(self.url, json=self.body).status_code)

    def test_same_request_id_with_different_reason_rejected(self):
        self.client.post(self.url, json=self.body)
        self.body['reason'] = '其他原因'
        self.assertEqual(409, self.client.post(self.url, json=self.body).status_code)

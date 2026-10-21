"""Refund tools: preview first; only the raw, next user turn can authorize submission."""
import time
from uuid import uuid4
from urllib.parse import quote
import httpx
from atguigu.conf.config import settings
from atguigu.infrastructure import http_client
from atguigu.domain.messages import BotMessage
from atguigu.task.action.base import Action, ActionResult

async def call_api(state, order, method='GET', body=None):
    client = http_client.http_client
    if client is None:
        raise RuntimeError('业务服务未连接，请稍后重试。')
    url = settings.commerce_api_base_url.rstrip('/') + '/orders/' + quote(order, safe='') + '/refund-applications'
    response = await client.request(method, url, params={'submitted_by': state.sender_id} if method == 'GET' else None,
                                    json=body if method == 'POST' else None)
    if response.status_code >= 400:
        try:
            detail = response.json().get('detail')
        except ValueError:
            detail = None
        raise RuntimeError(detail if isinstance(detail, str) else f'业务服务请求失败（{response.status_code}），未确认提交成功。')
    payload = response.json()
    data = payload.get('data') if isinstance(payload, dict) else None
    if not isinstance(data, dict):
        raise RuntimeError('业务服务返回格式异常，请查询退款进度核对。')
    return data

class PrepareRefundAction(Action):
    name = 'action_prepare_refund'
    async def run(self, state, action_kwargs):
        slots = state.active_task.slots
        order, reason = str(slots.get('order_number', '')).strip(), str(slots.get('refund_reason', '')).strip()
        # Starting a new preview invalidates any earlier confirmation.
        state.pending_refund = None
        if not 2 <= len(reason) <= 255:
            return ActionResult(messages=[BotMessage(text='退款原因需要 2 到 255 个字，请重新发起并补充原因。')])
        try:
            data = await call_api(state, order)
            if not data['eligible']:
                return ActionResult(messages=[BotMessage(text=data['eligibility_reason'])])
            active = next((r for r in data['applications'] if r['status'] in {'submitted', 'processing'}), None)
            if active:
                return ActionResult(messages=[BotMessage(text=f"订单已有退款申请 {active['request_id']}：{active['status_desc']}，未重复提交。")])
        except (RuntimeError, httpx.HTTPError, ValueError, KeyError) as exc:
            detail = str(exc) if isinstance(exc, RuntimeError) else '业务服务暂时不可用，请稍后重试。'
            return ActionResult(messages=[BotMessage(text=detail)])
        state.pending_refund = {'order_id': order, 'reason': reason,
            'request_id': 'R' + uuid4().hex.upper(), 'created_at': time.time()}
        return ActionResult(messages=[BotMessage(text=f'请核对退款申请：\n订单：{order}\n原因：{reason}\n'
            '回复“确认提交”创建申请，回复“取消”放弃，或输入“修改原因：新的原因”。申请提交后仍需审核，不代表退款到账。', suggestions=['确认提交', '取消'])])

class LookupRefundAction(Action):
    name = 'action_lookup_refund'
    async def run(self, state, action_kwargs):
        order = str(state.active_task.slots.get('order_number', ''))
        try:
            data = await call_api(state, order)
            lines = [f"{r['request_id']}：{r['status_desc']}（原因：{r['reason']}）" for r in data['applications']]
            message = f'订单 {order} 的退款记录：\n' + '\n'.join(lines) if lines else f'订单 {order} 暂无退款申请。'
        except (RuntimeError, httpx.HTTPError, ValueError, KeyError) as exc:
            message = str(exc) if isinstance(exc, RuntimeError) else '退款记录查询失败，请稍后重试。'
        return ActionResult(messages=[BotMessage(text=message)])

async def submit_pending(state):
    pending = state.pending_refund
    if time.time() - pending['created_at'] > 600:
        state.pending_refund = None
        return [BotMessage(text='确认已超过 10 分钟，请重新发起退款申请并核对。')]
    pending['attempted'] = True
    try:
        data = await call_api(state, pending['order_id'], 'POST',
            {'submitted_by': state.sender_id, 'reason': pending['reason'], 'request_id': pending['request_id']})
        if data.get('status') not in {'submitted', 'processing'} or data.get('request_id') != pending['request_id']:
            raise RuntimeError('返回状态异常，请查询退款进度核对。')
        state.pending_refund = None
        return [BotMessage(text=f"订单 {pending['order_id']} 的退款申请已提交。申请编号：{data['request_id']}。"
            '当前等待审核，尚未退款到账。可以发送“查询退款进度”查看记录。')]
    except (httpx.HTTPError, ValueError):
        # Retain the same request id: retries must never create another application.
        return [BotMessage(text='提交结果暂时无法确认，请先查询退款进度。再次回复“确认提交”将使用同一申请编号核对，不会另建申请。')]
    except RuntimeError as exc:
        return [BotMessage(text=str(exc))]

def confirmation_reminder(state):
    p = state.pending_refund
    return f"仍有待核对的退款申请：订单 {p['order_id']}，原因：{p['reason']}。请回复“确认提交”或“取消”。"

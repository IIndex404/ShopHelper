import test from 'node:test'
import assert from 'node:assert/strict'
import { requestJson } from '../src/api.js'

test('JSON API responses and friendly failures', async (t) => {
  const originalFetch = globalThis.fetch
  t.after(() => { globalThis.fetch = originalFetch })
  globalThis.fetch = async () => new Response('{"messages":[]}', { status: 200 })
  assert.deepEqual(await requestJson('/api/chat'), { messages: [] })
  globalThis.fetch = async () => new Response('Internal Server Error', { status: 500 })
  await assert.rejects(requestJson('/api/chat'), /HTTP 500/)
  globalThis.fetch = async () => new Response('{"detail":"数据库连接失败"}', { status: 503 })
  await assert.rejects(requestJson('/api/chat'), /数据库连接失败/)
  globalThis.fetch = async () => new Response('<html>wrong route</html>', { status: 200 })
  await assert.rejects(requestJson('/api/chat'), /接口返回格式不正确/)
  globalThis.fetch = async () => { throw new TypeError('Failed to fetch') }
  await assert.rejects(requestJson('/api/chat'), /无法连接服务/)
  globalThis.fetch = async () => { throw new DOMException('Aborted', 'AbortError') }
  await assert.rejects(requestJson('/api/chat'), /请求超时/)
})

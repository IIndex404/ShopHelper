// 接口报错时不直接解析 JSON，否则真正的错误会被 JSON.parse 掩盖。
export async function requestJson(url, options = {}) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), 45000)
  try {
    const response = await fetch(url, { ...options, signal: controller.signal })
    const text = await response.text()
    let data
    try {
      data = JSON.parse(text)
    } catch {
      if (!response.ok) {
        throw new Error(`服务暂时不可用（HTTP ${response.status}），请检查后端和数据库是否正常运行。`)
      }
      throw new Error('接口返回格式不正确，请检查后端服务和接口地址。')
    }
    if (!response.ok) {
      const detail = typeof data?.detail === 'string' ? data.detail : ''
      throw new Error(detail || `请求失败（HTTP ${response.status}），请稍后重试。`)
    }
    return data
  } catch (error) {
    if (error.name === 'AbortError') {
      throw new Error('请求超时，请检查后端、数据库或模型服务后重试。')
    }
    if (error instanceof TypeError) {
      throw new Error('无法连接服务，请确认前后端已启动。')
    }
    throw error
  } finally {
    clearTimeout(timer)
  }
}

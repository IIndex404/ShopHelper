# ShopHelper 客服服务

接收聊天消息，判断用户要查订单、查物流还是申请退款，再调用对应的业务接口。保存当前对话和聊天历史。

从项目根目录查看 [完整运行步骤](../README.md)。本服务启动命令是 `uv run python -m atguigu.main`，默认端口 `18082`。

- `POST /api/chat`：发送消息。
- `GET /api/chat/history?sender_id=u1001`：读取聊天历史。
- `POST /api/chat/new-session`：开启新对话，结束当前待处理流程，保留历史。
- `GET /health`：检查服务和数据库连接。

不填模型密钥时使用规则处理基础流程。`atguigu` 是沿用的内部 Python 包名，不影响页面名称。

# ShopHelper

**电商智能客服与售后助手。用聊天的方式查订单、查物流、申请退款。**

用户可以直接说“查一下这个订单”“我的快递到哪了”或“我要退款”。信息不够时，助手会继续询问；需要提交申请时，会先让用户核对并确认。

## 能做什么

| 功能 | 使用方式 |
| --- | --- |
| 查询订单 | 发送订单卡片，或在聊天里输入订单号，查看状态和商品信息。 |
| 查询物流 | 查看快递公司、运单号和物流进度。 |
| 商品咨询 | 根据商品资料回答价格、规格等问题。 |
| 申请退款 | 收集订单号和退款原因，核对后提交，返回申请编号。 |
| 查询退款进度 | 继续问“退款成功了吗”，读取当前订单的退款记录。 |
| 多轮对话 | 记住当前订单，缺少信息时追问，并保存聊天历史。 |

## 一个完整例子

```text
用户：我要给订单 A20260410001 申请退款。
助手：请简单说一下退款原因。
用户：重复下单，不再需要。
助手：展示订单号和退款原因，请用户核对。
用户：修改原因：尺寸不合适。
助手：更新原因，等待确认。
用户：确认提交。
助手：返回申请编号，说明正在等待审核。
用户：退款成功了吗？
助手：读取这笔订单的退款记录，告诉用户当前状态。
```

**这里的“提交成功”表示数据库里确实创建了退款申请，不代表钱已经退回。** 同一订单已有进行中的申请时，会展示原申请，不重复创建。

## AI 在哪里发挥作用

AI 负责理解用户要办什么、提取订单号等信息，并组织咨询回答。后端负责真正查询数据、推进业务流程和保存申请。

退款提交必须由用户明确确认。模型不能自己替用户点击确认，也不能把接口超时说成提交成功。没有配置模型，或模型调用失败时，会使用规则处理基础业务流程。

## 先看清当前范围

- 自带演示订单、商品和物流数据，方便在本机体验。
- 页面可切换 `u1001`、`u1002`、`u1003` 三个演示用户，**尚未接入正式登录**。
- 退款申请会真正保存，但没有连接支付渠道，也没有退款审核后台。
- 售后问答使用基础资料；还没有完成向量知识库检索。

## 在自己电脑上运行

需要 Python 3.12、Node.js、uv，以及 MySQL 8。下面的命令以 PowerShell 为例。

### 1. 下载项目

```powershell
git clone https://github.com/IIndex404/ShopHelper.git
cd ShopHelper
```

### 2. 准备数据库

如果已经装了 MySQL，把 `sql` 里的两个 SQL 文件依次导入：

```text
sql/001_init_customer_service.sql
sql/002_init_commerce.sql
```

它们会创建客服数据库 `customer_service` 和业务数据库 `commerce`，并导入演示数据。只在新建的演示库中执行，不要用来覆盖已有业务数据。

也可以使用项目提供的 Docker 配置：

```powershell
docker compose up -d db
```

第一次启动会自动导入上述 SQL。数据库使用本机 `3307` 端口，示例密码是 `shophelper_demo`，与后面的配置示例一致。如果端口已占用，请修改端口和两个后端的数据库连接地址。

### 3. 启动电商业务服务

打开一个终端：

```powershell
cd ecommerce-service-backend
Copy-Item .env.example .env
uv sync
uv run python main.py
```

已有 `.env` 就保留原文件，不要重复覆盖。使用自己的 MySQL 时，先把 `.env` 中的账号、密码、端口改成自己的配置。

### 4. 启动客服服务

再打开一个终端，从项目根目录执行：

```powershell
cd customer-service-backend
Copy-Item .env.example .env
uv sync
uv run python -m atguigu.main
```

同样保留已有 `.env`。想使用模型时，在里面填写 `LLM_API_KEY`、`LLM_BASE_URL` 和 `LLM_MODEL`；不填密钥也能先体验基础流程。

### 5. 启动页面

再打开一个终端，从项目根目录执行：

```powershell
cd customer-service-frontend
npm ci
npm run dev
```

打开 **http://127.0.0.1:5173/**。

| 服务 | 地址 |
| --- | --- |
| 页面 | http://127.0.0.1:5173 |
| 客服接口文档 | http://127.0.0.1:18082/docs |
| 电商业务接口文档 | http://127.0.0.1:18081/docs |

## 项目结构

```text
customer-service-frontend/  聊天页面、订单卡片和商品列表
customer-service-backend/   理解用户需求、管理对话、调用业务工具
ecommerce-service-backend/  查询订单、物流和商品，保存退款申请
sql/                       数据表和演示数据
docs/                      业务流程及代码说明
```

前端使用 Vue 3；后端使用 FastAPI、SQLAlchemy 和 MySQL；模型通过兼容 OpenAI 的接口接入，规划与回答使用 LangChain。

## 检查项目是否正常

在两个后端目录分别执行：

```powershell
uv run python -m unittest discover -s tests -v
```

在前端目录执行：

```powershell
npm run build
```

已通过 29 项后端测试和前端构建，也做过本机退款申请、进度查询及重复申请的实际接口验证。

更多说明：[业务流程](docs/业务流程.md) · [代码说明](docs/代码说明.md)

# Agent 助手 (Agent Assistant)

基于 **DeepSeek API + LangGraph** 的多智能体（Multi-Agent）对话助手：通过自然语言即可完成**文件操作**、**知识库问答（RAG）**与**联网搜索**，并提供流式输出的网页聊天界面与多会话持久化记忆。

## ✨ 功能特性

- 🤖 **主管-子代理架构**：`create_supervisor` 智能路由到 3 个专职子代理
  - 📁 `file_agent`：文件/文件夹的创建、读取、写入、删除、重命名、列目录
  - 📚 `rag_agent`：知识库（向量数据库）的查询与文档管理
  - 🌐 `web_agent`：联网搜索、网页正文抓取、链接提取
- 💬 **网页聊天界面**：流式输出（打字机效果）、Enter 发送 / Shift+Enter 换行、自动加载历史会话
- 🧠 **多会话持久化记忆**：LangGraph + SQLite 检查点（`db/agent_memory.db`），按 `thread_id` 隔离会话
- ✂️ **上下文裁剪**：`before_model` 中间件只保留最近 6 条消息，防止超出上下文窗口
- 🔎 **混合检索 RAG**：ChromaDB 向量召回 + 关键词召回（多路召回），CrossEncoder 重排
- 📤 **知识库导入**：`/api/upload` 接口上传文本文件自动分块入库
- 🔒 **安全限制**：相对路径的文件操作默认被限制在 `agent_work/` 工作区内，越界拒绝

## 🏗️ 系统架构

```
用户输入
   │
   ▼
Supervisor Agent（DeepSeek，负责路由 & 总结）
   │
   ├─► file_agent ──► 文件工具集（工作区 agent_work/）
   ├─► rag_agent  ──► ChromaDB 知识库（embedding + rerank + LLM 生成）
   └─► web_agent  ──► Bing 搜索 / 网页抓取（requests + BeautifulSoup）
   │
   ▼
LangGraph Checkpointer（SQLite）← 多会话记忆，消息裁剪中间件
```

## 📁 目录结构

```
agent_assistant/
├── src/
│   ├── app.py            # FastAPI 入口：路由 / 上传 / 历史接口
│   ├── agent.py          # 主管-子代理编排、记忆检查点、消息裁剪
│   ├── tools.py          # 文件 / 知识库 / 联网 三大工具集定义
│   ├── rag_util.py       # RAG 实现：ChromaDB 存储、检索、重排
│   ├── config.py         # 读取 .env 配置（API Key、模型、工作区）
│   └── chroma_db/        # ChromaDB 向量库持久化目录（运行时生成）
├── templates/
│   └── chat.html         # 聊天页面
├── static/
│   ├── css/chat.css
│   └── js/chat.js        # 流式对话、会话 ID 管理
├── db/
│   └── agent_memory.db   # SQLite 会话记忆（运行时生成）
├── agent_work/           # 默认工作区（Agent 操作文件的位置）
├── models/               #  # 模型文件夹（需自行下载，见 README）（all-MiniLM-L6-v2,ms-marco-MiniLM-L6-v2）
├── .env                  # 密钥与模型配置（勿提交到版本库）
├── requirements.txt
├── pyproject.toml
├── Dockerfile            # 容器化部署
├── start.bat             # Windows 一键启动脚本
└── README.md
```

## 🚀 快速开始

### 1. 准备环境

```bash
# 建议使用虚拟环境（Windows）
python -m venv .venv
.venv\Scripts\Activate.ps1        # PowerShell
# 或 .venv\Scripts\activate.bat   # CMD

pip install -r requirements.txt
```

### 2. 配置 `.env`

在项目根目录创建 `.env` 文件（参考模板）：

```ini
DEEPSEEK_API_KEY=sk-你的密钥
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
```

API Key 在 [DeepSeek 开放平台](https://platform.deepseek.com) 申请。可选配置项见下文 [配置项](#-配置项)。

### 3. 配置本地模型路径（RAG 必需）

`src/rag_util.py` 顶部从**固定绝对路径**加载 embedding 与 rerank 模型：

```python
model = SentenceTransformer(".../models/all-MiniLM-L6-v2")
reranker = CrossEncoder(".../models/ms-marco-MiniLM-L6-v2")
```

> 项目 `models/` 目录已自带 `all-MiniLM-L6-v2`（embedding 模型）；`ms-marco-MiniLM-L6-v2`（重排模型）需自行下载。请将上述两行路径改为你机器上的实际路径，例如 `os.path.join(<项目根>, "models", "all-MiniLM-L6-v2")`。RAG 在导入时即加载模型，路径错误会导致服务启动失败。

### 4. 启动服务

**必须在项目根目录启动**（`templates/` 与 `static/` 位于根目录，不在 `src` 包内）：

```bash
uvicorn src.app:app --reload --port 8000
```

Windows 下也可直接双击 `start.bat`：使用 `.venv` 启动并自动打开浏览器，首次加载模型约需 10~20 秒。

浏览器访问 <http://127.0.0.1:8000> 即可对话。

### 5. 使用示例

- “在 agent_work 里新建一个 `notes` 文件夹，里面写一份 `todo.txt`，内容是……”
- “总结一下知识库里关于 XX 的资料” —— 先通过上传接口导入资料
- “帮我搜一下今天 DeepSeek 的新闻，并抓取第一条链接的正文”

## 🐳 Docker 部署

```bash
docker build -t agent-assistant .
docker run -p 8000:8000 --env-file .env agent-assistant
```

> 镜像内模型位于 `/app/models`，若使用 Docker 部署，请先按上一步说明把 `src/rag_util.py` 中的模型路径改为容器内路径（或挂载卷），否则服务无法启动。

## 🔌 API 接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/` | 聊天页面 |
| `POST` | `/api/chat` | 对话接口，JSON `{messages: [{role, content}], thread_id}`，流式返回文本 |
| `POST` | `/api/upload` | 上传文本文件（`multipart`，字段名 `files`）导入知识库 |
| `GET` | `/api/history/{thread_id}` | 获取某会话的历史消息 |

示例：导入文件到知识库

```bash
curl -F "files=@./资料.txt" http://127.0.0.1:8000/api/upload
```

## 🛠️ 可用工具

### 文件工具（`file_agent`，作用于工作区）

| 工具 | 说明 |
| --- | --- |
| `create_files` | 创建文件夹（可递归创建多级目录） |
| `create_file` | 创建空文件 |
| `get_file` | 读取文本文件内容 |
| `save_file` | 覆盖写入 / 修改文件内容 |
| `list_files` | 列出文件夹内容（文件 / 目录） |
| `delete_file` | 删除文件 |
| `rename_file` | 重命名文件或文件夹 |
| `delete_files` | 递归删除文件夹（禁止删除工作区根目录） |

### 知识库工具（`rag_agent`）

| 工具 | 说明 |
| --- | --- |
| `query_ch_documents` | 向量 + 关键词多路召回，重排后生成回答 |
| `add_ch_document` | 添加文档到向量库 |
| `get_ch_file` | 列出知识库中的文件 |
| `delete_ch_file` | 删除知识库中的文件 |

### 联网工具（`web_agent`）

| 工具 | 说明 |
| --- | --- |
| `web_search` | Bing 联网搜索，返回前 5 条结果 |
| `fetch_webpage` | 抓取网页正文（去除脚本 / 样式，取前 3000 字） |
| `get_links` | 提取网页中的外链 |

## ⚙️ 配置项

| 环境变量 | 默认值 | 说明 |
| --- | --- | --- |
| `DEEPSEEK_API_KEY` | 无（必填） | DeepSeek API 密钥 |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | API 地址 |
| `DEEPSEEK_MODEL` | `deepseek-chat` | 使用的模型名 |
| `WORKSPACE_ROOT` | `<项目根>/agent_work` | 文件操作的工作区根目录 |

## 🧠 记忆与会话

- 每个浏览器会话在 `localStorage` 中生成独立的 `thread_id`，对话记录按会话隔离并持久化到 SQLite；
- 刷新页面后自动通过 `/api/history/{thread_id}` 恢复历史；
- 每次调用前由 `trim_messages` 中间件裁剪消息，仅保留最近 6 条。

## ⚠️ 安全与注意事项

- 相对路径操作被限制在 `WORKSPACE_ROOT` 内，绝对路径操作不受限制——请勿让不可信用户直接调用接口；
- `.env` 已加入 `.gitignore`，**切勿将真实 API Key 提交到版本库**；
- `db/`、`src/chroma_db/`、`models/` 为运行时数据 / 本地资源，按需备份；
- 联网搜索基于 Bing 页面解析，未使用官方搜索 API，结果可能受网络与页面结构影响。

## 🛠️ 技术栈

- **编排**：LangGraph、langgraph-supervisor、langgraph-checkpoint-sqlite
- **模型**：DeepSeek Chat（OpenAI 兼容接口，`langchain-openai`）
- **RAG**：ChromaDB、sentence-transformers（embedding + CrossEncoder 重排）
- **后端**：FastAPI、Uvicorn
- **联网**：requests + BeautifulSoup
- **前端**：原生 HTML / CSS / JavaScript（流式 fetch 读取）

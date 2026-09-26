from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL, validate_config
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent, AgentState
from langgraph_supervisor import create_supervisor
from tools import file_tools, rag_tools, web_tools
from langchain.agents.middleware import before_model
from langchain_core.messages import RemoveMessage
from langgraph.graph.message import REMOVE_ALL_MESSAGES
from langgraph.runtime import Runtime
from typing import Any
from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3


llm = ChatOpenAI(
    model=DEEPSEEK_MODEL,
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL,
    temperature=0.7,
    max_tokens=1000
)
    

@before_model
def trim_messages(state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
    """只保留最近几条消息，防止超出上下文窗口"""
    messages = state["messages"]
    if len(messages) <= 6:
        return None
    recent = messages[-6:]
    return {
        "messages": [
            RemoveMessage(id=REMOVE_ALL_MESSAGES),
            *recent
        ]
    }

validate_config()

conn = sqlite3.connect("db/agent_memory.db", check_same_thread=False)
checkpointer = SqliteSaver(conn)

file_agent = create_agent(llm, file_tools, name="file_agent",system_prompt="你是文件专家。当用户问到关于文件操作的问题时，你的第一反应是调用 file_agent 工具，而不是凭自己的知识回答。")
rag_agent = create_agent(llm, rag_tools, name="rag_agent",system_prompt="你是知识库专家。当用户问到关于数据库查询的问题时，你的第一反应是调用 rag_query 工具查询知识库，而不是凭自己的知识回答。")
web_agent = create_agent(llm, web_tools, name="web_agent",system_prompt="你是联网搜索专家。当用户问任何问题时，你的第一反应是调用 web_search 工具搜索，而不是凭自己的知识回答。")

agent = create_supervisor(
    agents=[file_agent, rag_agent, web_agent],
    model=llm,
    middlewares=[trim_messages],
    prompt="""请根据以下规则选择合适的 Agent 来回答问题：
1. 如果用户需要创建、读取、修改、删除、重命名文件或文件夹，请使用 file_agent。
2. 如果用户需要查询知识库或管理知识库（向量数据库）中的文档，请使用 rag_agent。
3. 如果用户需要实时、最新或具体的事实信息（天气、新闻、股价等），或向量数据库查不到，或用户明确说"上网"，"搜索""联网""查一下"，必须调用 web_agent，不要直接回答不知道。
4. 如果以上情况都不符合，可以调用web_agent,给出回答。"""
).compile(checkpointer=checkpointer)


def get_history(thread_id: str = "default") -> list:
    config = {"configurable": {"thread_id": thread_id}}
    state = agent.get_state(config)
    messages = []
    last_assistant_text = None

    if state and state.values:
        for msg in state.values.get("messages", []):
            if msg.type == "human":
                content = getattr(msg, "content", "")
                if isinstance(content, list):
                    content = "".join(str(c) for c in content)
                if content:
                    messages.append({"role": "user", "content": content})
                    last_assistant_text = None  # 新问题，重置
            elif msg.type == "ai":
                if getattr(msg, "tool_calls", None):
                    continue
                content = getattr(msg, "content", "")
                if isinstance(content, list):
                    content = "".join(str(c) for c in content)
                if content and "Transferring" not in content and "Successfully" not in content:
                    # 同一轮对话只保留最后一条
                    if last_assistant_text is None:
                        messages.append({"role": "assistant", "content": content})
                    else:
                        messages[-1] = {"role": "assistant", "content": content}
                    last_assistant_text = content
    return messages


def run_agent(messages: list, thread_id: str = "default") -> str:
    config = {"configurable": {"thread_id": thread_id}}
    result = agent.invoke({"messages": messages}, config)

    for msg in reversed(result["messages"]):
        if getattr(msg, "tool_calls", None):
            continue
        content = getattr(msg, "content", "")
        if isinstance(content, list):
            content = "".join(str(c) for c in content)
        if content and "Transferring" not in content and "Successfully" not in content:
            return content

    return "(无文本回复)"
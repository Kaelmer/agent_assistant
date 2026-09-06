"""
LangGraph 多Agent连接简单示例
================================
演示三个Agent如何通过图（Graph）进行连接：
  1. 数据分析Agent（data_agent）
  2. 代码生成Agent（code_agent）
  3. 最终审查Agent（review_agent）

连接方式：
  - 普通边：data_agent → code_agent → review_agent
  - 条件边：根据任务类型动态路由
"""

from typing import TypedDict, Literal
from langgraph.graph import StateGraph, END

# ========== 1. 定义状态（State）==========
# 状态是Agent之间传递数据的载体
class State(TypedDict):
    """全局共享状态"""
    task: str              # 输入任务
    data_result: str       # 数据分析结果
    code_result: str       # 代码生成结果
    final: str             # 最终结果


# ========== 2. 定义Agent节点函数 ==========

def data_agent(state: State) -> dict:
    """Agent 1: 数据分析"""
    print(f"[数据分析Agent] 正在分析任务: {state['task']}")
    result = f"已完成数据分析: {state['task']}"
    return {"data_result": result}


def code_agent(state: State) -> dict:
    """Agent 2: 代码生成（依赖Agent 1的结果）"""
    print(f"[代码生成Agent] 基于分析结果生成代码")
    result = f"已生成代码: {state['data_result']}"
    return {"code_result": result}


def review_agent(state: State) -> dict:
    """Agent 3: 最终审查"""
    print(f"[审查Agent] 正在审查最终结果")
    result = f"最终审查通过: {state['code_result']}"
    return {"final": result}


# ========== 3. 定义条件路由函数 ==========

def route(state: State) -> Literal["code_agent", "review_agent"]:
    """
    根据任务类型决定流程走向：
    - 简单任务：跳过代码生成，直接审查
    - 复杂任务：需要经过代码生成
    """
    if state["task"] == "简单任务":
        print(">>> 检测到简单任务，跳过代码生成Agent")
        return "review_agent"
    else:
        print(">>> 检测到复杂任务，需要代码生成Agent")
        return "code_agent"


# ========== 4. 构建图（Graph）==========

def build_graph():
    """构建多Agent图"""
    graph = StateGraph(State)

    # 添加节点（Agent）
    graph.add_node("data_agent", data_agent)
    graph.add_node("code_agent", code_agent)
    graph.add_node("review_agent", review_agent)

    # 设置入口点
    graph.set_entry_point("data_agent")

    # 添加条件边：data_agent 根据路由函数决定下一个
    graph.add_conditional_edges(
        "data_agent",
        route,
        {
            "code_agent": "code_agent",    # 复杂任务 → 代码生成
            "review_agent": "review_agent", # 简单任务 → 直接审查
        }
    )

    # 添加普通边
    graph.add_edge("code_agent", "review_agent")  # 代码生成 → 审查
    graph.add_edge("review_agent", END)            # 审查 → 结束

    # 编译图
    return graph.compile()


# ========== 5. 主程序 ==========

def main():
    print("=" * 50)
    print("LangGraph 多Agent连接示例")
    print("=" * 50)

    # 构建图
    app = build_graph()

    # 测试1：复杂任务（走完整流程）
    print("\n【测试1】复杂任务")
    print("-" * 30)
    result1 = app.invoke({"task": "分析销售数据并生成报表"})
    print(f"\n最终结果: {result1['final']}")

    # 测试2：简单任务（跳过代码生成）
    print("\n【测试2】简单任务")
    print("-" * 30)
    result2 = app.invoke({"task": "简单任务"})
    print(f"\n最终结果: {result2['final']}")


if __name__ == "__main__":
    main()

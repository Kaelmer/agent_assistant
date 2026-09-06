# test_stream.py
from agent import agent


config = {"configurable": {"thread_id": "test-1"}}

for token, metadata in agent.stream(
    {"messages": [{"role": "user", "content": "非常感谢有这次机会，向大家汇报我大一这一学年的学习与生活情况。过去一年，我快速适应了大学全新的学习节奏与生活环境，在抓好课堂专业学习的基础上，主动走出课本，参与校园实践活动，不断充实自我。写一段像这样的"}]},
    config=config,
    stream_mode="messages"
):
    if token.content:
        print(token.content, end="", flush=True)
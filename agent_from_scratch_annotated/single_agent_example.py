# ============================================================
# single_agent_example.py：单 Agent 示例（中文详细注释版）
# ============================================================
# 这个文件展示最小可运行思路：
#   1. 定义几个普通 Python 函数作为工具
#   2. 创建一个 Agent，把工具挂到 Agent.functions 上
#   3. 用 while True 持续读取用户输入
#   4. 每次输入都追加到 messages
#   5. 调用 Swarm.run() 让 Agent 决定是否调用工具
#   6. 把本轮新增消息追加回 messages，形成上下文
#
# 对照你 day11：
#   这个文件 ≈ 你的 main.py 入口逻辑
#   get_weather/send_email ≈ 你的 tools/*.py 里的具体工具函数
#   weather_agent.functions ≈ 你的 tool_registry.py
#   client.run(...) ≈ 你的 run_agent(...)
# ============================================================

from dotenv import load_dotenv
_ = load_dotenv()  # 读取 .env 文件，把 OPENAI_API_KEY 等配置加载到环境变量里。

import json
from agent import pretty_print_messages, Agent, Swarm


# ------------------------------------------------------------
# 工具 1：get_weather
# ------------------------------------------------------------
# 这是一个普通 Python 函数，但因为后面被放进 Agent(functions=[...])，
# 它就变成了模型可以选择调用的“工具”。
#
# 参数：
#   location：地点，没有默认值，所以模型调用工具时必须提供。
#   time：时间，有默认值 "now"，所以模型可以不提供。
#
# 返回：
#   JSON 字符串。这里是 mock 数据，不是真的查天气。
def get_weather(location, time="now"):
    # 这里返回固定温度 65，只是为了演示工具调用链路。
    # json.dumps 把 dict 转成字符串，因为很多 tool result 最后都会以文本形式进入 messages。
    return json.dumps({"location": location, "temperature": "65", "time": time})


# ------------------------------------------------------------
# 工具 2：send_email
# ------------------------------------------------------------
# 这个工具演示“一个 Agent 可以同时拥有多个工具”。
# 真实系统里 send_email 会有副作用；这个示例只是返回一段文本，不会真的发邮件。
def send_email(recipient, subject, body):
    return f"Sent! email to {recipient} with the subject: {subject} and body: {body}"


# ------------------------------------------------------------
# 创建 Agent
# ------------------------------------------------------------
# Agent 是配置容器，不是执行器。
#
# name：方便打印和追踪是哪一个 Agent 在说话。
# instructions：system prompt，规定 Agent 的身份和任务范围。
# functions：这个 Agent 能调用的工具列表。
weather_agent = Agent(
    name="Weather Agent",
    instructions="You are a helpful agent for giving information on weather.",
    functions=[get_weather, send_email],
)

# Swarm 是执行器，负责：
#   - 把 messages + tools 发给模型
#   - 接收模型返回
#   - 执行工具
#   - 把工具结果放回 messages
client = Swarm()

print("Starting Single Agent - Weather Agent")
print('Ask me how is the weather today in Brussels?')

# ------------------------------------------------------------
# messages：对话历史容器
# ------------------------------------------------------------
# messages 是一个 list。
# 每次用户输入，会追加一条：
#   {"role": "user", "content": user_input}
#
# Swarm.run() 之后，会产生 assistant/tool 等消息。
# 这些消息也会追加回 messages。
#
# 所以 messages 不是“当前这一句话”，而是“到目前为止的完整轨迹”。
messages = []

# 当前活跃 Agent。
# 单 Agent 示例里基本一直是 weather_agent。
# 但仍然保留 agent 变量，是为了和 multi_agent_example.py 的写法统一。
agent = weather_agent


# ------------------------------------------------------------
# 主输入循环
# ------------------------------------------------------------
# 这个 while True 是“程序一直等待用户输入”的外层循环。
# 注意它和 agent.py 里的 Swarm.run() 内部循环不是同一个东西：
#
#   这里的 while True：
#       一次循环 = 用户输入一轮
#
#   Swarm.run() 里的 while：
#       一次循环 = 模型决策/工具执行的一步
while True:
    # 读取终端输入。
    user_input = input("\033[90mUser\033[0m: ")

    # 把用户输入变成标准 message，加入历史。
    # 这是模型后面能看到用户问题的原因。
    messages.append({"role": "user", "content": user_input})

    # 运行 Agent。
    # 这里会进入 agent.py 的 Swarm.run()：
    #   模型看 messages 和 tools
    #   如果需要工具，就返回 tool_calls
    #   Swarm 执行工具
    #   工具结果放回 history
    #   模型可能继续回答
    response = client.run(agent=agent, messages=messages)

    # 打印本轮新增消息。
    # response.messages 只包含这次 run 新增的 assistant/tool 消息，不包含旧 messages。
    pretty_print_messages(response.messages)

    # 把本轮新增消息追加回总 messages。
    # 如果不做这一步，下一次用户输入时，模型就不知道上一轮发生了什么。
    messages.extend(response.messages)

    # 保存当前活跃 Agent。
    # 单 Agent 时变化不明显；多 Agent 时 response.agent 可能已经切换。
    agent = response.agent

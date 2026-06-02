# ============================================================
# multi_agent_example.py：多 Agent 转交示例（中文详细注释版）
# ============================================================
# 这个文件展示一个重要思想：
#   工具函数不只能返回普通字符串，也可以返回另一个 Agent。
#
# 当工具返回 Agent 时，Swarm.handle_function_result() 会识别出来，
# 然后 Swarm.run() 会把 active_agent 切换成新的 Agent。
#
# 这就是“handoff / transfer / 多 Agent 转交”的最小原理。
#
# 对你当前阶段：
#   先读懂，不急着实现。
#   重点看 active_agent 是怎么从 triage_agent 变成 sales_agent/refunds_agent 的。
# ============================================================

from dotenv import load_dotenv
_ = load_dotenv()  # 读取 .env 中的 OPENAI_API_KEY 等环境变量。

from agent import Agent, Swarm

# Swarm 是执行器。
# 所有 Agent 都由同一个 Swarm.run() 来运行。
client = Swarm()


# ------------------------------------------------------------
# 退款工具：process_refund
# ------------------------------------------------------------
# 这个工具属于 Refunds Agent。
# docstring 会被 function_to_json() 读取，变成工具 description。
#
# 注意：这里只是 mock，不是真的退款。
def process_refund(item_id, reason="NOT SPECIFIED"):
    """Refund an item. Refund an item. Make sure you have the item_id of the form item_... Ask for user confirmation before processing the refund."""
    print(f"[mock] Refunding item {item_id} because {reason}...")
    return "Success!"


# ------------------------------------------------------------
# 打折工具：apply_discount
# ------------------------------------------------------------
# 同样属于 Refunds Agent。
# 它没有参数，所以模型调用时 arguments 可以是 {}。
def apply_discount():
    """Apply a discount to the user's cart."""
    print("[mock] Applying discount...")
    return "Applied discount of 11%"


# ------------------------------------------------------------
# Agent 1：Triage Agent
# ------------------------------------------------------------
# triage 的意思是“分诊”。
# 它不直接解决问题，只判断用户应该交给哪个专业 Agent。
#
# 它的 instructions 明确要求：
#   - 购买/价格/折扣/产品问题 -> Sales Agent
#   - 退款/退货/投诉 -> Refunds Agent
#   - 不要自己处理，必须转交
triage_agent = Agent(
    name="Triage Agent",
    instructions="""Determine which agent is best suited to handle the user's request, and transfer the conversation to that agent.
    - For purchases, pricing, discounts and product inquiries -> Sales Agent
    - For refunds, returns and complaints -> Refunds Agent
    Never handle requests directly - always transfer to the appropriate specialist.""",
)


# ------------------------------------------------------------
# Agent 2：Sales Agent
# ------------------------------------------------------------
# 负责销售相关问题。
# 这个 Agent 初始没有业务工具，后面会给它加一个 transfer_back_to_triage 工具。
sales_agent = Agent(
    name="Sales Agent",
    instructions="Be super enthusiastic about selling bees.",
)


# ------------------------------------------------------------
# Agent 3：Refunds Agent
# ------------------------------------------------------------
# 负责退款相关问题。
# 它拥有两个业务工具：process_refund 和 apply_discount。
refunds_agent = Agent(
    name="Refunds Agent",
    instructions="Help the user with a refund. If the reason is that it was too expensive, offer the user a refund code. If they insist, then process the refund.",
    functions=[process_refund, apply_discount],
)


# ------------------------------------------------------------
# 转交工具 1：回到 Triage Agent
# ------------------------------------------------------------
# 这个函数的返回值不是字符串，而是 triage_agent 对象。
# Swarm.handle_function_result() 看到返回的是 Agent，就会包装成 Result(agent=triage_agent)。
# Swarm.run() 随后会把 active_agent 切回 triage_agent。
def transfer_back_to_triage():
    """Call this function if a user is asking about a topic that is not handled by the current agent."""
    return triage_agent


# ------------------------------------------------------------
# 转交工具 2：转到 Sales Agent
# ------------------------------------------------------------
# 模型调用这个工具，就等于请求把当前任务交给 sales_agent。
def transfer_to_sales():
    return sales_agent


# ------------------------------------------------------------
# 转交工具 3：转到 Refunds Agent
# ------------------------------------------------------------
# 模型调用这个工具，就等于请求把当前任务交给 refunds_agent。
def transfer_to_refunds():
    return refunds_agent


# ------------------------------------------------------------
# 给 Agent 注册工具
# ------------------------------------------------------------
# triage_agent 的工具不是“查数据/执行业务动作”，而是“转交给别的 Agent”。
# 所以它的 functions 是 transfer_to_sales 和 transfer_to_refunds。
triage_agent.functions = [transfer_to_sales, transfer_to_refunds]

# sales_agent / refunds_agent 也需要能把不属于自己的问题转回分诊 Agent。
# 所以给它们追加 transfer_back_to_triage。
sales_agent.functions.append(transfer_back_to_triage)
refunds_agent.functions.append(transfer_back_to_triage)

print("Starting Multiple Agents - Triage Agent, Refunds Agent and Bee Sales Agent")

# messages 保存整个对话历史。
# 多 Agent 切换时，history 不会丢；新的 Agent 会继续看同一段 messages。
messages = []

# 初始由 triage_agent 接待用户。
# 后面每次 response.agent 都可能改变这个变量。
agent = triage_agent


# ------------------------------------------------------------
# 外层用户输入循环
# ------------------------------------------------------------
while True:
    # 读取用户输入。
    user_input = input("\033[90mUser\033[0m: ")

    # 把用户输入加入 messages。
    messages.append({"role": "user", "content": user_input})

    # 运行当前 active agent。
    # 如果当前是 triage_agent，它可能调用 transfer_to_sales / transfer_to_refunds。
    # 如果当前是 refunds_agent，它可能调用 process_refund / apply_discount。
    response = client.run(agent=agent, messages=messages)

    # response.messages 是本轮新增消息。
    # 这里根据消息类型选择不同打印方式。
    for message in response.messages:
        if message["role"] == "assistant" and message.get("content"):
            # assistant 普通回答：打印 Agent 名字和内容。
            print(f"\033[94m{message['sender']}\033[0m: {message['content']}")
        elif message["role"] == "tool":
            # tool 消息是工具执行结果。
            # 这里只把退款/打折工具的结果作为 System 打印出来。
            tool_name = message.get("tool_name", "")
            if tool_name in ["process_refund", "apply_discount"]:
                print(f"\033[93mSystem\033[0m: {message['content']}")

    # 把本轮新增消息并入总历史。
    # 如果不追加，下一轮 Agent 就不知道刚刚已经转交或执行了什么工具。
    messages.extend(response.messages)

    # 更新当前 active agent。
    # 这是多 Agent 示例的关键：
    #   response.agent 可能是 triage_agent
    #   也可能是 sales_agent
    #   也可能是 refunds_agent
    agent = response.agent

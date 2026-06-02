import requests
import json


def ask_local_model(prompt, model_name="qwen3:8b"):
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": model_name,
            "prompt": prompt,
            "stream": False
        }
    )

    result = response.json()
    return result["response"]


def get_tool_call_from_model(
    user_input,
    available_tools,
    messages,
    step,
    max_steps,
    model_name="qwen3:8b"
):
    prompt = f"""
你是一个 Agent 的工具调用决策模块。

你的唯一任务是：
判断当前这一步是否需要调用工具。

你不能回答用户问题。
你不能聊天。
你不能总结工具结果。
你不能解释工具列表。
你只能返回一个 JSON 对象，供 Python 程序解析。

用户原始问题：
{user_input}

当前循环轮次：
{step}

最大允许轮次：
{max_steps}

当前消息轨迹：
{json.dumps(messages, ensure_ascii=False, indent=2)}

当前可用工具列表：
{json.dumps(available_tools, ensure_ascii=False, indent=2)}

判断规则：

1. 只有当用户问题必须依赖外部工具才能完成时，才返回 need_tool=true。

2. 如果用户是在普通聊天、闲聊、问你怎么看、问代码概念、问刚才/之前聊了什么、问你有什么工具，
   都不要调用工具，返回 need_tool=false。

3. 如果当前消息轨迹里已经有 tool 角色的工具结果，并且该结果足够回答用户问题，
   不要重复调用工具，返回 need_tool=false。

4. 如果当前轮次已经达到最大允许轮次，
   不要继续调用工具，返回 need_tool=false。

5. 如果需要调用工具，tool_name 必须来自“当前可用工具列表”，不能编造工具名。

6. arguments 必须是 JSON object。

7. 如果不需要工具，tool_name 必须是 null，arguments 必须是空对象 {{}}。

8. 不要输出 Python 写法。
   只能使用 JSON 的 true、false、null。
   不能使用 Python 的 True、False、None。

如果需要调用 web_search，arguments 必须包含：
{{
  "query": "搜索关键词",
  "max_result": 5
}}

如果用户没有指定返回数量，max_result 使用 JSON 数字 5。
max_result 不能写成字符串 "5"。

返回格式只能是下面两种之一。

需要调用工具时返回：
{{
  "success": true,
  "need_tool": true,
  "tool_name": "工具名称",
  "arguments": {{
    "参数名": "参数值"
  }},
  "message": "需要调用工具的原因"
}}

不需要调用工具时返回：
{{
  "success": true,
  "need_tool": false,
  "tool_name": null,
  "arguments": {{}},
  "message": "不需要调用工具的原因"
}}

现在只返回 JSON。
"""

    model_text = ask_local_model(prompt, model_name)

    return model_text


def get_direct_answer_from_model(
    user_input,
    available_tools,
    messages,
    model_name="qwen3:8b",
    memory=None
):
    prompt = f"""
你是一个本地 Agent 助手。

用户问题：
{user_input}

记忆：
{memory}

当前可用工具列表：
{json.dumps(available_tools, ensure_ascii=False, indent=2)}

当前消息轨迹：
{json.dumps(messages, ensure_ascii=False, indent=2)}

请直接回答用户问题。
回答时按下面优先级处理：
1. 如果用户询问“刚刚、刚才、之前、上次、上一轮”做了什么，
   优先查看“记忆”和“当前消息轨迹”。
   如果记忆中能找到相关历史，就根据记忆回答。
   不要因为没有专门的“搜索历史工具”就说无法查询。
2. 只有当用户明确询问“你有什么工具、你能使用哪些工具、工具列表”时，
   才根据“当前可用工具列表”回答。
   其他问题不要主动围绕工具列表回答。
3. 如果用户是普通聊天或普通提问，直接自然语言回答。
回答要求：
1. 用自然语言回答。
2. 不要输出 JSON。
3. 不要使用 Markdown 代码块。
4. 如果用户明确询问工具列表，工具名称要准确来自 available_tools。
5. 如果用户没有询问工具列表，不要主动介绍工具。
6. 每次回答之前都要检查记忆和当前消息轨迹，确保回答的连贯性。
"""

    model_text = ask_local_model(prompt, model_name)

    return model_text


def get_final_answer_from_model(
    user_input,
    messages,
    model_name="qwen3:8b"
):
    prompt = f"""
你是一个 Agent 的最终回答生成模块。

用户原始问题：
{user_input}

完整消息轨迹：
{json.dumps(messages, ensure_ascii=False, indent=2)}

请根据上面的消息轨迹，给用户一个最终回答。

要求：
1. 如果工具执行成功，就根据工具结果回答。
2. 如果工具执行失败，要如实说明失败原因。
3. 如果没有调用工具，就根据已有消息直接回答。
4. 不要编造工具结果里没有的信息。
5. 直接回答用户，不要输出 JSON。
"""

    model_text = ask_local_model(prompt, model_name)

    return model_text
import requests
import json
import os


def ask_deepseek_model(prompt, model_name='deepseek-chat'):
    api_key = os.getenv("DEEPSEEK_API_KEY")

    response = requests.post(
        "https://api.deepseek.com/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        json={
            "model": model_name,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "stream": False
        }
    )

    result = response.json()

    if "choices" not in result:
        return json.dumps(result, ensure_ascii=False)

    return result["choices"][0]["message"]["content"]


def ask_local_model(prompt, model_name='deepseek-chat'):
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
    model_name='deepseek-chat'
):
    prompt = f"""
你是一个 Agent 的工具调用决策模块。

你的唯一任务：根据用户原始问题、当前轮次、消息轨迹和可用工具，决定“当前这一步”是否还要调用一个工具。

硬性输出要求：
1. 你只能返回一个 JSON 对象。
2. 不要回答用户问题。
3. 不要总结工具结果。
4. 不要输出 Markdown。
5. JSON 中只能使用 true、false、null，不能使用 Python 的 True、False、None。

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

任务拆分规则：
1. 先按用户原始描述顺序拆分所有明确子任务。
2. 多任务必须按用户原始顺序逐个完成。
3. 每次最多只选择一个“最靠前且尚未完成”的子任务调用工具。
4. 不要跳过前面的未完成任务去执行后面的任务。
5. 判断任务是否完成时，只能看 messages 中 role="tool" 的工具结果。
6. role="assistant" 且 type="tool_call" 只表示模型打算调用工具，不算完成。
7. 如果 role="tool" 的 content.success 是 false，这个子任务不算成功完成；但不要重复调用同一个失败子任务，应继续处理下一个独立子任务。

工具映射规则：
1. 用户说“查 GitHub 用户 xxx / 搜索 GitHub 用户 xxx / GitHub xxx”，调用 get_github_user，arguments 必须是 {{"username": "xxx"}}。
2. 用户说“查 C 盘 / 查 E 盘 / 查磁盘 / 查硬盘 / 查盘符情况 / 查电脑磁盘情况”，调用 get_windows_disk_status，arguments 必须是 {{}}。
3. get_windows_disk_status 是通用磁盘状态工具，可以返回 Windows 多个盘符的信息。不要因为没有 get_e_disk_status 或 get_c_disk_status 就跳过 C 盘/E 盘任务。
4. 如果用户同时要求“查 E 盘”和“查 C 盘情况”，一次成功的 get_windows_disk_status 工具结果可以作为两个盘符任务的依据，但前提是 messages 中已经存在该工具的 role="tool" 成功结果。
5. 用户说“查临时文件 / 扫描临时文件 / Windows 临时文件”，调用 scan_windows_temp_files。
6. 用户说“查下载目录 / 扫描下载文件 / Downloads”，调用 scan_windows_downloads。
7. 用户说“联网搜索 / 搜索网页 / 查网上资料”，调用 web_search。

停止规则：
1. 当前轮次是本次可以执行的轮次。
如果 step <= max_steps，仍然允许调用工具。
即使 step == max_steps，也可以调用一个工具，这是最后一次工具调用机会。
不要因为 step == max_steps 就返回 need_tool=false。
只有当所有子任务都完成，或者没有可用工具能处理下一个子任务时，才返回 need_tool=false。
2. 如果所有子任务都已经有对应的成功 role="tool" 结果，返回 need_tool=false。
3. 如果还有未完成子任务，并且当前轮次没有达到最大允许轮次，返回 need_tool=true，并调用最靠前的未完成子任务对应工具。
4. 普通聊天、代码概念问题、问你有什么工具、问刚才/之前/上次聊了什么，都返回 need_tool=false。

参数规则：
1. arguments 必须是 JSON object。
2. get_windows_disk_status 不需要参数，arguments 必须是 {{}}。
3. web_search 的 arguments 必须包含 query 和 max_result；如果用户没有指定返回数量，max_result 使用 JSON 数字 5，不能写成字符串。
4. scan_windows_temp_files 的 arguments 必须包含 min_size_mb 和 max_items；如果用户没有指定，使用 JSON 数字 10 和 30，不能写成字符串。
5. scan_windows_downloads 的 arguments 必须包含 min_size_mb 和 max_items；如果用户没有指定，使用 JSON 数字 10 和 30，不能写成字符串。

需要调用工具时返回：
{{
  "success": true,
  "need_tool": true,
  "tool_name": "工具名称",
  "arguments": {{
    "参数名": "参数值"
  }},
  "message": "当前最靠前未完成子任务是什么，以及为什么调用这个工具"
}}

不需要调用工具时返回：
{{
  "success": true,
  "need_tool": false,
  "tool_name": null,
  "arguments": {{}},
  "message": "不需要调用工具的原因；如果是因为达到最大轮次，要明确说明还有哪些任务未完成"
}}

现在只返回 JSON。
"""

    model_text = ask_deepseek_model(prompt, model_name)

    return model_text


def get_direct_answer_from_model(
    user_input,
    available_tools,
    messages,
    model_name="deepseep-chat",
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

请直接用自然语言回答用户问题。

回答优先级：
1. 如果用户询问“刚刚、刚才、之前、上次、上一轮”做了什么，优先查看“记忆”和“当前消息轨迹”。如果能找到相关历史，就根据历史回答。
2. 不要因为没有专门的“搜索历史工具”就说无法查询历史；先看记忆和当前消息轨迹。
3. 只有当用户明确询问“你有什么工具、你能使用哪些工具、工具列表”时，才根据“当前可用工具列表”回答。
4. 如果用户是普通聊天或普通提问，直接自然回答，不要主动围绕工具列表回答。
5. 如果当前消息轨迹中已有工具结果，只能根据 role="tool" 的 content 回答；不能把 assistant 的 tool_call 当作真实结果。

回答要求：
1. 不要输出 JSON。
2. 不要使用 Markdown 代码块。
3. 不要编造记忆、工具结果或历史记录中不存在的信息。
4. 如果工具结果不足以回答，要明确说缺少什么，而不是假装已经完成。
"""

    model_text = ask_deepseek_model(prompt, model_name)

    return model_text


def get_llm_workflow_next_step_from_model(
    user_input,
    workflow_steps,
    model_name="deepseek-chat"
):
    prompt = f"""
你是一个 LLM workflow 的下一步任务判断模块。

你的任务：根据用户原始任务和已经完成的 workflow 步骤，判断下一步应该做什么。

你不能做的事：
1. 不要执行任务。
2. 不要生成最终答案。
3. 不要调用工具。
4. 只判断下一步任务主题。

用户原始任务：
{user_input}

已经完成的 workflow 步骤：
{json.dumps(workflow_steps, ensure_ascii=False, indent=2)}

判断规则：
1. 先理解用户原始任务里包含哪些连续步骤。
2. 再查看已经完成的 workflow_steps。
3. 如果还有未完成步骤，选择最靠前的未完成步骤作为下一步。
4. 如果所有步骤都完成，is_finished 返回 true，step_name 返回 null。
5. 不要重复选择已经完成的步骤。

返回格式必须是 JSON：
{{
  "success": true,
  "is_finished": false,
  "step_name": "下一步任务名称",
  "reason": "为什么下一步要做这个"
}}

如果已经完成，返回：
{{
  "success": true,
  "is_finished": true,
  "step_name": null,
  "reason": "所有 workflow 步骤已经完成"
}}

现在只返回 JSON。
"""

    model_text = ask_deepseek_model(prompt, model_name)

    try:
        model_result = json.loads(model_text)
    except json.JSONDecodeError:
        return {
            "success": False,
            "is_finished": False,
            "step_name": None,
            "reason": "模型输出不是合法 JSON",
            "raw_output": model_text
        }

    if not isinstance(model_result, dict):
        return {
            "success": False,
            "is_finished": False,
            "step_name": None,
            "reason": "模型输出不是字典",
            "raw_output": model_result
        }

    return model_result


def get_llm_workflow_step_from_model(
    step_name,
    user_input,
    previous_result=None,
    model_name="deepseek-chat"
):
    prompt = f"""
你是一个 LLM workflow 的步骤执行模块。

你的任务：只完成当前 workflow 中的这一步，不要提前完成后续步骤。

原始用户任务：
{user_input}

当前步骤名称：
{step_name}

上一步结果：
{previous_result}

执行规则：
1. 只根据“当前步骤名称”完成这一小步。
2. 如果 previous_result 为空，说明这是 workflow 的第一步。
3. 如果 previous_result 不为空，必须基于上一步结果继续处理。
4. 不要调用工具。
5. 不要输出 JSON。
6. 直接输出当前步骤的自然语言结果。
"""

    model_text = ask_deepseek_model(prompt, model_name)

    return model_text


def check_llm_workflow_completion_from_model(
    user_input,
    workflow_steps,
    model_name="deepseek-chat"
):
    prompt = f"""
你是一个 LLM workflow 的任务完成判断模块。

你的任务：根据用户原始任务和已经完成的 workflow 步骤，判断整个 workflow 是否已经满足用户要求。

你不能做的事：
1. 不要执行新的任务步骤。
2. 不要生成最终答案。
3. 不要调用工具。
4. 只判断任务是否完成。

用户原始任务：
{user_input}

已经完成的 workflow 步骤：
{json.dumps(workflow_steps, ensure_ascii=False, indent=2)}

判断规则：
1. 先拆出用户原始任务要求的所有连续步骤。
2. 再检查 workflow_steps 里是否已经完成这些步骤。
3. 只有所有要求都被满足，is_complete 才能是 true。
4. 如果还缺步骤，is_complete 必须是 false，并把缺失步骤写进 missing_steps。
5. 不要因为已经有一个步骤结果，就默认整个任务完成。

返回格式必须是 JSON：
{{
  "success": true,
  "is_complete": true,
  "missing_steps": [],
  "reason": "为什么认为任务已经完成"
}}

如果没有完成，返回：
{{
  "success": true,
  "is_complete": false,
  "missing_steps": [
    "缺失步骤名称"
  ],
  "reason": "为什么认为任务还没完成"
}}

现在只返回 JSON。
"""

    model_text = ask_deepseek_model(prompt, model_name)

    try:
        model_result = json.loads(model_text)
    except json.JSONDecodeError:
        return {
            "success": False,
            "is_complete": False,
            "missing_steps": [],
            "reason": "模型输出不是合法 JSON",
            "raw_output": model_text
        }

    if not isinstance(model_result, dict):
        return {
            "success": False,
            "is_complete": False,
            "missing_steps": [],
            "reason": "模型输出不是字典",
            "raw_output": model_result
        }

    return model_result


def get_final_answer_from_model(
    user_input,
    messages,
    model_name="deepseek-chat"
):
    prompt = f"""
你是一个 Agent 的最终回答生成模块。

你的唯一任务：根据用户原始问题和完整消息轨迹，生成诚实的最终回答。

用户原始问题：
{user_input}
 
完整消息轨迹：
{json.dumps(messages, ensure_ascii=False, indent=2)}

严格判断规则：
1. 先按用户原始问题的顺序拆出所有明确子任务。
2. 每个子任务是否完成，只能看 messages 中 role="tool" 的工具结果。
3. role="assistant" 且 type="tool_call" 只表示模型打算调用工具，不能当作工具执行成功。
4. role="tool" 的 content.success 必须是 true，才算该工具对应子任务完成。
5. 如果某个子任务没有对应的成功 role="tool" 结果，必须把它列为“未完成”。
6. 只有所有子任务都有对应成功工具结果时，才可以说“所有任务已完成”。
7. 不能因为已经完成了一部分任务，就说全部完成。
8. 不能因为最终回答生成到了这里，就默认任务都完成。

子任务与工具对应规则：
1. GitHub 用户查询必须有对应 username 的 get_github_user 成功工具结果。
2. 多个 GitHub 用户必须分别检查 username，不能用一次 get_github_user 结果覆盖所有用户。
3. 查 C 盘、查 E 盘、查磁盘、查硬盘，都对应 get_windows_disk_status。
4. 一次成功的 get_windows_disk_status 工具结果可以回答多个盘符问题，但必须真的存在这个 role="tool" 成功结果。
5. 查临时文件对应 scan_windows_temp_files。这个工具只表示“扫描候选文件”，不表示已经清理。
6. 查下载目录对应 scan_windows_downloads。这个工具只表示“扫描候选文件”，不表示已经清理。
7. 联网搜索对应 web_search。

回答内容要求：
1. 对已完成的任务，基于对应工具结果简要回答。
2. 对未完成的任务，明确列出任务名称。
3. 如果未完成原因是没有对应 role="tool" 结果，就直接说“本轮没有执行到这个工具调用”或“达到最大轮次前没有执行到该任务”。
4. 不要说“缺少工具”，除非当前可用工具列表或消息轨迹明确证明没有可用工具。
5. 不要编造工具结果里没有的数据。
6. 不要输出 JSON。
7. 直接回答用户。

如果存在未完成任务，回答结构建议：
已完成：
- ...

未完成：
- ...

原因：
- ...

如果所有任务都完成，才使用“所有任务已完成”之类表述。
"""

    model_text = ask_deepseek_model(prompt, model_name)

    return model_text


# 根据消息轨迹检查任务是否完成
def check_task_completion_from_model(user_input, messages, model_name="deepseek-chat"):
    prompt = f"""
你是一个 Agent 的任务完成度判断模块。

你的唯一任务：根据用户原始问题和当前消息轨迹，判断用户要求的所有子任务是否已经完成。

硬性输出要求：
1. 你不能调用工具。
2. 你不能回答用户问题。
3. 你不能总结工具结果给用户。
4. 你只能返回一个 JSON 对象，供 Python 程序解析。
5. 只能输出 JSON，不要输出解释文字。

用户原始问题：
{user_input}

当前消息轨迹：
{json.dumps(messages, ensure_ascii=False, indent=2)}

完成度判断步骤：
1. 先按用户原始描述顺序拆出所有明确子任务。
2. 对每个子任务，寻找 messages 中匹配的 role="tool" 工具结果。
3. 只有 role="tool" 且 content.success=true，才算该子任务完成。
4. role="assistant" 且 type="tool_call" 不能算完成。
5. role="tool" 且 content.success=false 也不能算完成。
6. 如果任何子任务没有匹配的成功工具结果，is_complete 必须是 false，need_more_tool 必须是 true。
7. 只有所有子任务都有匹配的成功工具结果，is_complete 才能是 true。

匹配规则：
1. GitHub 用户查询：必须匹配工具名 get_github_user，并且该工具结果对应用户要求的 username。
2. 如果用户要求多个 GitHub 用户，必须逐个 username 检查；不能用一次 get_github_user 结果覆盖所有 GitHub 子任务。
3. 磁盘查询：查 C 盘、查 E 盘、查磁盘、查硬盘、查盘符情况，都匹配 get_windows_disk_status。
4. 一次成功的 get_windows_disk_status 可以覆盖多个盘符查询，因为它返回 Windows 磁盘总体状态；但前提是 messages 中确实存在该工具的成功结果。
5. 临时文件查询匹配 scan_windows_temp_files。
6. 下载目录查询匹配 scan_windows_downloads。
7. 联网搜索匹配 web_search。

reason 规则：
1. reason 要说明判断依据来自哪些 role="tool" 结果。
2. 如果任务未完成，只说“messages 中缺少对应成功工具结果”。
3. 不要说“缺少直接查询 E 盘的工具”或“缺少工具”，因为 get_windows_disk_status 是通用磁盘工具。
4. 如果缺的是执行步骤，说“本轮没有执行到该子任务对应的工具调用”。

返回格式必须是：
{{
  "success": true,
  "is_complete": true,
  "need_more_tool": false,
  "missing_tasks": [],
  "reason": "判断理由"
}}

如果任务没有完成，返回格式例如：
{{
  "success": true,
  "is_complete": false,
  "need_more_tool": true,
  "missing_tasks": [
    "查 E 盘",
    "查 C 盘情况"
  ],
  "reason": "messages 中缺少 get_windows_disk_status 的成功工具结果，因此磁盘相关子任务未完成"
}}

现在只返回 JSON。
"""
    model_text = ask_deepseek_model(prompt, model_name)
    # 解析 JSON 字符串
    try:
        model_text = json.loads(model_text)
    except json.JSONDecodeError:
        return {
            "success": False,
            "is_complete": False,
            "need_more_tool": False,
            "missing_tasks": [],
            "reason": "模型输出不是合法 JSON",
            "raw_output": model_text
        }

    # 确保返回的是字典
    if not isinstance(model_text, dict):
        return {
            "success": False,
            "is_complete": False,
            "need_more_tool": False,
            "missing_tasks": [],
            "reason": "模型输出不是字典",
            "raw_output": model_text
        }

    return model_text

# 传入压缩过的信息和需要压缩的记忆
def compress_memory_from_model(old_messages,old_summary):
    prompt = f"""
你是 Agent 的记忆压缩模块。

你的任务：把“已有压缩记忆”和“即将被压缩的旧消息”合并成一份新的长期记忆 summary。

已有压缩记忆：
{old_summary}

即将压缩的旧消息：
{json.dumps(old_messages, ensure_ascii=False, indent=2)}

压缩目标：
1. 保留后续对话仍然有用的信息。
2. 删除重复、寒暄、临时过程、无关细节。
3. 不要原文照搬整段消息，要压缩成简洁事实。
4. 如果旧消息和已有压缩记忆冲突，以旧消息中较新的信息为准。

必须保留的信息：
1. 用户当前正在做的项目、文件、模块和目标。
2. 已经确认的设计决定，例如 memory 结构、工具注册方式、Agent loop 逻辑。
3. 最近排查出的关键问题和结论，例如报错原因、修复方向。
4. 用户明确表达的偏好、约束和下一步想做的事。
5. 对后续回答有帮助的变量名、函数名、文件名和职责边界。

不要保留的信息：
1. 大段工具输出、完整报错堆栈、重复解释。
2. 已经过期的中间尝试。
3. 没有长期价值的临时测试内容。
4. 空泛总结，例如“用户在学习 Agent”。

输出要求：
1. 只输出新的 summary 文本。
2. 不要输出 JSON。
3. 不要输出 Markdown 标题。
4. 用中文。
5. 控制在 300 字以内。
"""
    model_text = ask_deepseek_model(prompt, model_name = 'deepseek-chat')
    return model_text

def router_user_input(user_input):
    prompt = f"""
你是 Agent 系统的用户输入路由模块。

你的任务：
根据用户输入，判断这次输入应该进入哪一条执行链路。

你不能做的事：
1. 不要回答用户问题。
2. 不要调用工具。
3. 不要生成最终内容。
4. 不要执行用户任务。
5. 只做路由判断。

用户输入：
{user_input}

可选路由：
1. llm_only
   含义：单步 LLM 自身能力可以完成的任务。
   例如：普通聊天、解释概念、简单写作、单步翻译、单步总结、润色一句话。

2. llm_workflow
   含义：不需要外部工具，但需要多个 LLM 步骤才能完成的任务。
   例如：先写故事再翻译、先总结再改写、先生成大纲再扩写、先分析再给建议。

3. tool_agent
   含义：需要外部工具、外部信息、系统状态或本地环境能力的任务。
   例如：查 GitHub 用户、联网搜索、查磁盘、扫描文件、读取本地文件、调用 API。

4. memory_query
   含义：用户在询问历史对话、刚才、之前、上次、本轮已经做过什么。
   例如：刚才我问了什么、上次查了什么、之前你说了什么、我们刚刚做到哪一步。

判断优先级：
1. 如果用户询问历史、刚才、之前、上次、本轮记录，优先选择 memory_query。
2. 如果任务需要外部信息、真实环境、工具、文件、网络或 API，选择 tool_agent。
3. 如果任务不需要工具，但明显包含多个连续 LLM 步骤，选择 llm_workflow。
4. 其他普通单步任务，选择 llm_only。

输出要求：
1. 只能输出一个 JSON 对象。
2. 不要输出 Markdown。
3. 不要输出解释性正文。
4. route 只能是以下四个值之一：
   llm_only、llm_workflow、tool_agent、memory_query。
5. reason 用一句中文说明为什么选择这个 route。

输出格式：
{{
  "route": "llm_only",
  "reason": "用户只是提出普通单步问题，不需要工具或多步骤处理"
}}
"""
    model_text = ask_deepseek_model(prompt, model_name = 'deepseek-chat')
    return model_text
    
    
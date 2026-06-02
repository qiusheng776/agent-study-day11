# ============================================================
# agent.py：极简 Agent 框架核心源码（中文详细注释版）
# ============================================================
# 这个文件可以理解为一个“小型 Agent 运行时”。
#
# 它把你 day11 项目里拆开的几件事，集中写在了一个文件里：
#
# 你 day11 的结构：
#   main.py                    -> 程序入口、读取用户输入、保存 session
#   model.py                   -> 调用模型，让模型决定是否使用工具
#   tool_registry.py           -> 告诉模型有哪些工具、工具需要什么参数
#   parse_tool_call_result.py  -> 校验模型输出的工具调用 JSON 是否可信
#   run_tool.py                -> 根据 tool_name + arguments 真正执行工具
#   memory_store.py            -> 保存长期/短期上下文
#
# 这个 agent.py 的结构：
#   Agent                      -> 保存 Agent 名字、模型、提示词、工具列表
#   function_to_json()         -> 自动把 Python 函数变成工具 schema
#   Swarm.get_chat_completion  -> 调用模型，让模型看 messages + tools
#   Swarm.handle_tool_calls    -> 执行模型请求的工具
#   Swarm.run                  -> Agent 主循环：模型 -> 工具 -> 模型 -> ...
#
# 阅读重点不要放在“背每一行语法”，而是看清楚数据流：
#   user message
#       ↓
#   history/messages
#       ↓
#   model completion
#       ↓
#   assistant message，可能包含 tool_calls
#       ↓
#   handle_tool_calls 执行工具
#       ↓
#   tool result message 放回 history
#       ↓
#   下一轮模型继续看 history
# ============================================================

import json      # JSON 转换工具：json.loads 把 JSON 字符串变 dict；json.dumps 把 dict/list 变 JSON 字符串。
import copy      # copy.deepcopy 用来复制 messages，避免函数内部直接修改外部传入的原列表。
import inspect   # inspect.signature 用来读取函数签名：参数名、类型注解、默认值。

from openai import OpenAI                 # OpenAI API 客户端。这个示例默认用 OpenAI 的 Chat Completions 接口。
from pydantic import BaseModel            # Pydantic 的 BaseModel 用来声明结构化数据容器。
from typing_extensions import Literal     # Literal 用来限制字段只能取固定值，例如 type 只能是 "function"。
from typing import Union, Callable, List, Optional  # 类型标注：帮助读代码时理解变量里应该放什么。


# ------------------------------------------------------------
# pretty_print_messages：只负责打印，不负责 Agent 决策
# ------------------------------------------------------------
# 参数 messages：一个消息列表。
# 列表里的每个元素通常是一个 dict，形状大概是：
#   {"role": "user", "content": "..."}
#   {"role": "assistant", "content": "...", "tool_calls": [...]}
#   {"role": "tool", "content": "...", "tool_name": "..."}
#
# 这个函数只做“终端展示”：
#   - assistant 的自然语言内容打印出来
#   - assistant 请求的工具调用也打印出来
# 它不改变 messages，也不执行工具。
def pretty_print_messages(messages) -> None:
    # 遍历一整批消息。
    for message in messages:
        # 这里只展示 assistant 消息。
        # user 消息是用户输入，不需要重复打印。
        # tool 消息是工具结果，这个函数也不专门打印。
        if message["role"] != "assistant":
            continue

        # sender 是 Swarm.run() 里后加的字段，用来说明是哪一个 Agent 生成了这条 assistant 消息。
        # 单 Agent 时 sender 基本固定；多 Agent 时 sender 可以是 Triage Agent / Sales Agent / Refunds Agent。
        # \033[94m 和 \033[0m 是终端颜色代码，不影响 Agent 逻辑。
        print(f"\033[94m{message['sender']}\033[0m:", end=" ")

        # 如果 assistant 消息里有 content，说明模型产生了自然语言回答。
        # 注意：有些 assistant 消息可能 content 为空，但 tool_calls 不为空；这表示模型不是回答，而是在请求调用工具。
        if message["content"]:
            print(message["content"])

        # tool_calls 是模型请求调用工具的列表。
        # .get("tool_calls") 是为了避免字段不存在时报错。
        # or [] 是为了把 None 也变成空列表，方便后面 for 循环。
        tool_calls = message.get("tool_calls") or []

        # 如果同一轮模型请求了多个工具，打印时先换行，让输出更清楚。
        if len(tool_calls) > 1:
            print()

        # 逐个打印工具调用。
        for tool_call in tool_calls:
            # OpenAI tool_call 的核心结构是：
            #   tool_call["function"]["name"]       -> 工具名
            #   tool_call["function"]["arguments"]  -> 参数 JSON 字符串
            f = tool_call["function"]
            name, args = f["name"], f["arguments"]

            # args 通常是字符串，例如：'{"location":"Brussels"}'。
            # 这里先 loads 成 dict，再 dumps 回字符串，是为了格式化显示。
            # replace(":", "=") 只是为了显示成 location="Brussels" 的感觉。
            arg_str = json.dumps(json.loads(args)).replace(":", "=")
            print(f"\033[95m{name}\033[0m({arg_str[1:-1]})")


# ------------------------------------------------------------
# function_to_json：把 Python 函数自动变成工具 schema
# ------------------------------------------------------------
# 你现在 day11 的 tool_registry.py 是手动写：
#   工具名是什么
#   工具描述是什么
#   arguments 里有哪些字段
#   字段类型是什么
#
# 这个函数做的是“自动注册工具”：
#   输入：一个 Python 函数，例如 get_weather(location, time="now")
#   输出：OpenAI tools 参数需要的 JSON schema
#
# 这就是很多 Agent 框架都会做的事：
#   普通函数 -> 工具描述 -> 交给模型选择调用。
def function_to_json(func) -> dict:
    """
    作用：把一个普通 Python 函数转换成 OpenAI tools 需要的 JSON schema。

    例子：
    def add_two_numbers(a: int, b: int) -> int:
        # Adds two numbers together
        return a + b

    会被转换成类似：
    {
        'type': 'function',
        'function': {
            'name': 'add_two_numbers',
            'description': 'Adds two numbers together',
            'parameters': {
                'type': 'object',
                'properties': {
                    'a': {'type': 'integer'},
                    'b': {'type': 'integer'}
                },
                'required': ['a', 'b']
            }
        }
    }

    对你当前学习的意义：
    - 你现在是手写 tool_registry.py
    - 这个函数展示了“工具注册表可以从函数签名自动生成”
    - 但你现在不用急着改成自动生成，先理解工具 schema 的来源即可
    """
    # type_map：Python 类型 -> JSON schema 类型。
    # 模型读不懂 Python 的 int/str 类型对象，所以要转成 JSON schema 里的 integer/string。
    type_map = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
        list: "array",
        dict: "object",
        type(None): "null",
    }

    try:
        # inspect.signature(func) 会读取函数签名。
        # 例如：
        #   def get_weather(location, time="now")
        # 会读出两个参数：location 和 time；time 的默认值是 "now"。
        signature = inspect.signature(func)
    except ValueError as e:
        # 有些特殊对象可能无法读取签名，这里直接抛出明确错误。
        raise ValueError(
            f"Failed to get signature for function {func.__name__}: {str(e)}"
        )

    # parameters 最终会变成 JSON schema 里的 properties。
    # 形状类似：
    #   {
    #       "location": {"type": "string"},
    #       "time": {"type": "string"}
    #   }
    parameters = {}

    # signature.parameters.values() 是所有参数对象。
    # param.name 是参数名。
    # param.annotation 是类型注解。
    # param.default 是默认值。
    for param in signature.parameters.values():
        try:
            # 如果函数参数写了类型注解，例如 username: str，就能映射成 string。
            # 如果没写类型注解，param.annotation 可能不是 str/int 这些类型。
            # 这里用默认 string，意思是“不知道类型时先当字符串”。
            param_type = type_map.get(param.annotation, "string")
        except KeyError as e:
            # 这段基本很少触发，因为上面用了 .get。
            # 保留它是为了说明：真实框架里会考虑未知类型的情况。
            raise KeyError(
                f"Unknown type annotation {param.annotation} for parameter {param.name}: {str(e)}"
            )

        # 把当前参数写入 properties。
        parameters[param.name] = {"type": param_type}

    # required 表示模型调用工具时必须提供哪些参数。
    # 判断规则：没有默认值的参数是必填参数。
    #
    # 例子：
    #   def get_weather(location, time="now")
    #   location 没默认值 -> required
    #   time 有默认值 -> 不 required
    required = [
        param.name
        for param in signature.parameters.values()
        if param.default == inspect._empty
    ]

    # 返回的结构会作为 OpenAI API 的 tools 参数传进去。
    # 重点看 function 里的三个字段：
    #   name        -> 工具名
    #   description -> 工具说明，通常来自函数 docstring
    #   parameters  -> 参数 schema
    return {
        "type": "function",
        "function": {
            "name": func.__name__,                 # 工具名直接用 Python 函数名。
            "description": func.__doc__ or "",     # 工具描述直接用函数文档字符串；没有就为空。
            "parameters": {
                "type": "object",
                "properties": parameters,
                "required": required,
            },
        },
    }


# ------------------------------------------------------------
# AgentFunction：工具函数类型标注
# ------------------------------------------------------------
# Callable 表示“可调用对象”，也就是函数。
# Union[str, "Agent", dict] 表示工具函数可能返回：
#   - str：普通工具结果
#   - dict：结构化工具结果
#   - Agent：特殊情况，表示要切换到另一个 Agent
#
# 注意：Callable[[], ...] 这里写得比较粗略，像 get_weather(location) 其实有参数。
# 这段主要是给读者/编辑器看的，不是运行时真正限制工具参数。
AgentFunction = Callable[[], Union[str, "Agent", dict]]


# ------------------------------------------------------------
# Agent：保存一个 Agent 的配置
# ------------------------------------------------------------
# 这个类本身不执行任何东西。
# 它只是一个“配置盒子”，里面放：
#   name                 -> Agent 名字
#   model                -> 使用哪个模型
#   instructions         -> system prompt，决定 Agent 角色和行为
#   functions            -> 这个 Agent 可以调用哪些工具
#   tool_choice          -> 是否强制/限制模型选择工具
#   parallel_tool_calls  -> 是否允许一轮里并行请求多个工具
class Agent(BaseModel):
    name: str = "Agent"
    model: str = "gpt-4o"
    instructions: Union[str, Callable[[], str]] = "You are a helpful agent."
    functions: List[AgentFunction] = []
    tool_choice: str = None
    parallel_tool_calls: bool = True


# ------------------------------------------------------------
# Response：Swarm.run() 的返回值容器
# ------------------------------------------------------------
# messages：本次 run() 新产生的消息，不包含传入前已有的旧消息。
# agent：本次 run() 结束后当前活跃的 Agent。
#
# 为什么要返回 agent？
# 因为多 Agent 场景里，运行过程中可能从 Triage Agent 切到 Sales Agent。
# 下一轮用户输入时，要继续交给上一次结束时的 active_agent。
class Response(BaseModel):
    messages: List = []
    agent: Optional[Agent] = None


# ------------------------------------------------------------
# Function / ChatCompletionMessageToolCall：描述模型请求的工具调用
# ------------------------------------------------------------
# OpenAI 返回 tool_calls 时，里面会包含 function.name 和 function.arguments。
# 这里用 Pydantic 类描述这种结构，方便类型理解。
class Function(BaseModel):
    # arguments 是 JSON 字符串，不是 Python dict。
    # 所以真正执行工具前需要 json.loads(tool_call.function.arguments)。
    arguments: str
    name: str


class ChatCompletionMessageToolCall(BaseModel):
    # id 是本次工具调用的唯一 ID。
    # 后面返回 role=tool 的消息时要带回 tool_call_id，让模型知道这个工具结果对应哪个调用。
    id: str
    function: Function
    # Literal["function"] 表示这个字段只能是字符串 "function"。
    type: Literal["function"]


# ------------------------------------------------------------
# Result：统一包装工具函数的返回值
# ------------------------------------------------------------
# 为什么需要 Result？
# 因为工具函数可能返回不同类型：
#   - 普通字符串："Success!"
#   - dict：{"success": True, ...}
#   - Agent：表示转交给另一个 Agent
#
# handle_function_result() 会把这些不同类型统一包装成 Result，
# 这样后面的 handle_tool_calls() 就能用统一方式生成 tool message。
class Result(BaseModel):
    value: str = ""                 # 工具结果文本，最后会写进 tool 消息的 content。
    agent: Optional[Agent] = None    # 如果工具返回了新 Agent，就放这里。


# ------------------------------------------------------------
# Swarm：真正的 Agent 执行器
# ------------------------------------------------------------
# 如果 Agent 是“配置”，Swarm 就是“运行机器”。
#
# 它负责：
#   1. 把 Agent 的 instructions + history + tools 发给模型
#   2. 读取模型返回的 assistant 消息
#   3. 如果模型要调用工具，就执行工具
#   4. 把工具结果追加回 history
#   5. 如果工具返回另一个 Agent，就切换 active_agent
#   6. 循环直到模型不再调用工具
class Swarm:
    def __init__(
        self,
        client=None,
    ):
        # client 是 OpenAI 客户端。
        # 如果外面没有传 client，就新建一个默认 OpenAI()。
        # 默认 OpenAI() 会从环境变量 OPENAI_API_KEY 读取密钥。
        if not client:
            client = OpenAI()
        self.client = client

    # --------------------------------------------------------
    # get_chat_completion：调用模型
    # --------------------------------------------------------
    # 输入：
    #   agent          -> 当前活跃 Agent，它提供模型名、系统提示词、工具列表
    #   history        -> 当前对话历史，不包含 system message
    #   model_override -> 临时覆盖 agent.model 的模型名
    #
    # 输出：
    #   OpenAI chat completion 对象
    def get_chat_completion(
        self,
        agent: Agent,
        history: List,
        model_override: str
    ):
        # OpenAI messages 需要包含 system/user/assistant/tool 等消息。
        # 这里每次调用模型时，都把 system message 放在最前面。
        # agent.instructions 决定当前 Agent 的身份和任务边界。
        messages = [{"role": "system", "content": agent.instructions}] + history

        # 把当前 Agent 拥有的 Python 工具函数转成 OpenAI tools schema。
        # 如果 agent.functions 为空，tools 就是空列表。
        tools = [function_to_json(f) for f in agent.functions]

        # create_params 是传给 OpenAI API 的参数字典。
        # 写成 dict 的好处是：后面可以按条件添加字段。
        create_params = {
            "model": model_override or agent.model,
            "messages": messages,
            "tools": tools or None,
            "tool_choice": agent.tool_choice,
        }

        # 只有真的有工具时，才设置 parallel_tool_calls。
        # parallel_tool_calls=True 表示模型一轮里可以请求多个工具。
        if tools:
            create_params["parallel_tool_calls"] = agent.parallel_tool_calls

        # 真正发起模型请求。
        # 模型返回结果可能有两种：
        #   1. 普通回答：message.content 有内容，message.tool_calls 为空
        #   2. 工具请求：message.tool_calls 有内容，content 可能为空
        return self.client.chat.completions.create(**create_params)

    # --------------------------------------------------------
    # handle_function_result：统一工具返回值
    # --------------------------------------------------------
    # 工具函数可能返回很多种东西。
    # 为了让后续流程简单，这里把它们统一转换成 Result。
    def handle_function_result(self, result) -> Result:
        # match/case 是 Python 的结构模式匹配。
        # 你可以先把它理解成更强的 if isinstance(...):
        match result:
            case Result() as result:
                # 情况 1：工具已经返回 Result，就直接返回。
                return result

            case Agent() as agent:
                # 情况 2：工具返回 Agent。
                # 这在 multi_agent_example.py 里很重要：
                #   transfer_to_sales() 返回 sales_agent
                #   transfer_to_refunds() 返回 refunds_agent
                #
                # 这不是普通工具结果，而是在告诉 Swarm：
                #   “下一轮请切换到这个 Agent”。
                return Result(
                    value=json.dumps({"assistant": agent.name}),
                    agent=agent
                )

            case _:
                # 情况 3：普通返回值，例如 str、dict、数字等。
                # 这里统一转成字符串，放进 Result.value。
                try:
                    return Result(value=str(result))
                except Exception as e:
                    raise TypeError(e)

    # --------------------------------------------------------
    # handle_tool_calls：执行模型请求的工具
    # --------------------------------------------------------
    # 输入：
    #   tool_calls -> 模型这轮请求调用的工具列表
    #   functions  -> 当前 Agent 允许使用的 Python 工具函数列表
    #
    # 输出：
    #   Response(messages=[tool messages], agent=可能的新 Agent)
    #
    # 对标你 day11：
    #   parse_tool_call_result.py 负责校验模型输出
    #   run_tool.py 负责执行工具
    # 这个函数把两者中的“执行工具部分”集中写在了一起。
    def handle_tool_calls(
        self,
        tool_calls: List[ChatCompletionMessageToolCall],
        functions: List[AgentFunction]
    ) -> Response:
        # function_map 是工具分发表。
        # 形状：
        #   {
        #       "get_weather": get_weather,
        #       "send_email": send_email
        #   }
        #
        # 这样模型给出工具名 name 后，就能通过 function_map[name] 找到真正的 Python 函数。
        function_map = {f.__name__: f for f in functions}

        # partial_response 只保存“工具执行产生的新消息”。
        # 它不是完整历史，只是本轮工具调用的增量结果。
        partial_response = Response(messages=[], agent=None)

        # 一个 assistant 消息可能请求多个工具，所以这里用 for 循环逐个处理。
        for tool_call in tool_calls:
            # 模型想调用的工具名。
            name = tool_call.function.name

            # 如果模型请求的工具不在当前 Agent 的 function_map 里，说明工具不存在或当前 Agent 无权使用。
            # 这里没有让程序崩溃，而是生成一条 role=tool 的错误消息。
            # 这样下一轮模型能看到“工具不存在”的结果，然后自己修正或回答失败。
            if name not in function_map:
                partial_response.messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "tool_name": name,
                        "content": f"Error: Tool {name} not found.",
                    }
                )
                continue

            # arguments 是模型生成的 JSON 字符串。
            # 例子：'{"location": "Brussels", "time": "now"}'
            # json.loads 后变成 Python dict：
            #   {"location": "Brussels", "time": "now"}
            args = json.loads(tool_call.function.arguments)

            # **args 是“字典解包成函数参数”。
            # 如果：
            #   args = {"location": "Brussels", "time": "now"}
            # 那么：
            #   function_map[name](**args)
            # 等价于：
            #   get_weather(location="Brussels", time="now")
            raw_result = function_map[name](**args)
            print(f'Called function {name} with args: {args} and obtained result: {raw_result}')
            print('#############################################')

            # 工具返回值可能是 str/dict/Agent/Result。
            # 先统一包装成 Result，后面就不用分类型处理。
            result: Result = self.handle_function_result(raw_result)

            # 把工具结果写成 OpenAI 需要的 tool message。
            # 这条消息会被追加回 history，下一轮模型就能看到工具执行结果。
            #
            # 关键字段：
            #   role: "tool"                  -> 告诉模型这是工具结果
            #   tool_call_id: tool_call.id     -> 对应模型刚才的哪个工具请求
            #   tool_name: name                -> 方便人类调试阅读
            #   content: result.value          -> 工具返回内容
            partial_response.messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "tool_name": name,
                    "content": result.value,
                }
            )

            # 如果工具返回值里携带了新 Agent，就先放在 partial_response.agent。
            # 真正切换 active_agent 的动作在 run() 里完成。
            if result.agent:
                partial_response.agent = result.agent

        return partial_response

    # --------------------------------------------------------
    # run：Agent 主循环
    # --------------------------------------------------------
    # 这是整个文件最重要的函数。
    #
    # 它做的事情是：
    #   1. 接收当前 Agent 和已有 messages
    #   2. 调用模型
    #   3. 把 assistant 消息加入 history
    #   4. 如果 assistant 没有 tool_calls，结束
    #   5. 如果 assistant 有 tool_calls，执行工具
    #   6. 把 tool 消息加入 history
    #   7. 如果工具返回新 Agent，切换 active_agent
    #   8. 回到第 2 步
    #
    # 这就是你一直在学的 Agent loop。
    def run(
        self,
        agent: Agent,
        messages: List,
        model_override: str = None,
        max_turns: int = float("inf"),
        execute_tools: bool = True,
    ) -> Response:
        # active_agent 表示当前这一轮由哪个 Agent 负责。
        # 多 Agent 时它会变化；单 Agent 时基本不变。
        active_agent = agent

        # history 是本次 run 内部使用的消息列表。
        # 用 deepcopy 是为了不直接修改外部传进来的 messages。
        #
        # 你可以理解为：
        #   外部 messages 是“原始历史”
        #   内部 history 是“运行中的工作副本”
        history = copy.deepcopy(messages)

        # init_len 记录 run 开始前 history 的长度。
        # 函数结束时用 history[init_len:] 只取本次新增消息返回。
        init_len = len(messages)

        print('#############################################')
        print(f'history: {history}')
        print('#############################################')

        # 主循环停止条件有两个：
        #   1. 新增消息数量没有超过 max_turns
        #   2. active_agent 还存在
        #
        # 注意：这个 max_turns 的写法比较粗糙。
        # 你 day11 里如果用 step/max_steps 会更清晰：
        #   step = 0
        #   while step < max_steps:
        #       ...
        #       step += 1
        while len(history) - init_len < max_turns and active_agent:
            # 让当前 active_agent 带着 history 去问模型。
            # 模型会看到：
            #   system instructions
            #   用户消息
            #   之前 assistant 的工具请求
            #   之前 tool 的执行结果
            completion = self.get_chat_completion(
                agent=active_agent,
                history=history,
                model_override=model_override
            )

            # OpenAI 返回 choices 列表，这里取第一个候选回答。
            message = completion.choices[0].message

            # 给 assistant 消息补一个 sender 字段。
            # OpenAI 原生消息里不一定有 sender，这是这个示例框架自己加的。
            message.sender = active_agent.name
            print(f'Active agent: {active_agent.name}')
            print(f"message: {message}")
            print('#############################################')

            # message 是 OpenAI/Pydantic 对象，不是普通 dict。
            # model_dump_json() 先转成 JSON 字符串，再 json.loads 转成普通 dict。
            # 最后追加到 history，形成完整轨迹。
            history.append(json.loads(message.model_dump_json()))

            # 如果模型没有请求工具，说明它已经给出最终回答或不需要工具。
            # 如果 execute_tools=False，也不执行工具。
            # 这两种情况都会 break，结束 Agent loop。
            if not message.tool_calls or not execute_tools:
                print('No tool calls hence breaking')
                print('#############################################')
                break

            # 走到这里，说明模型请求了工具。
            # handle_tool_calls 会：
            #   1. 找到对应 Python 函数
            #   2. json.loads 解析参数
            #   3. 执行函数
            #   4. 生成 role=tool 的消息
            partial_response = self.handle_tool_calls(message.tool_calls, active_agent.functions)

            # 把工具结果消息加入 history。
            # 这是 Agent loop 的关键：工具结果不是只给人看，而是要回填给模型看。
            history.extend(partial_response.messages)

            # 如果工具结果包含新 Agent，则切换 active_agent。
            # 例如 triage_agent 调用了 transfer_to_refunds，工具返回 refunds_agent，
            # 下一轮循环就由 Refunds Agent 继续处理同一段 history。
            if partial_response.agent:
                active_agent = partial_response.agent
                message.sender = active_agent.name

        # 返回本次 run 新增的消息，以及当前最终 active_agent。
        # 外层 single_agent_example.py / multi_agent_example.py 会把 response.messages
        # 再追加回全局 messages，供下一次用户输入继续使用。
        return Response(
            messages=history[init_len:],
            agent=active_agent,
        )

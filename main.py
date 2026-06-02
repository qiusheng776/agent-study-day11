from model import get_tool_call_from_model, get_final_answer_from_model, get_direct_answer_from_model
from json_tools import save_json
from run_tool import run_tool, list_tools
from pathlib import Path
from memory_store import read_memory, save_turn, save_memory
import time
from parse_tool_call_result import parse_tool_call_result
 

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / 'outputs'
# 记录一次对话的所有信息
session_file = OUTPUT_DIR / 'session.json'

def handle_command(user_input):
    if user_input == '/tools':
        print(list_tools())

    elif user_input == '/memory':
        print(read_memory())

    elif user_input == '/clear':
        # 清空内存
        save_memory([])
        print('记忆清除成功')

    else:
        print('未知指令')

def run_agent(user_input, model_name="qwen3:8b"):
    max_steps = 3
    step = 0
    last_tool_call = None
    stetus = 'running'

    tools = list_tools()

    messages = []
    messages.append({
        'role': 'user',
        'content': user_input
    })

    while step < max_steps:

        step += 1

        model_text = get_tool_call_from_model(
            user_input=user_input,
            available_tools=tools,
            messages=messages,
            step=step,
            max_steps=max_steps,
            model_name=model_name
        )

        model_result = parse_tool_call_result(model_text)

        messages.append({
            'role': 'assistant',
            'type': 'tool_call',
            'step': step,
            'content': model_result
        })
        
        if model_result['success'] is False:
            messages.append({
                'role': 'assistant',
                'type': 'error',
                'step': step,
                'content': model_result['error']
            })
            stetus = 'llm_json_failed'
            break   
        
        if model_result['need_tool'] is False:
            messages.append({
                'role': 'assistant',
                'type': 'final_answer',
                'step': step,
                'content': model_result['message']
            })
            break
            
        tool_result = run_tool(
            model_result['tool_name'],
            model_result['arguments']
        )
        
        last_tool_call= {
            'tool_name': model_result['tool_name'],
            'arguments': model_result['arguments'],
            'success': tool_result['success']
        }

        if tool_result['success'] is False:
            stetus = 'tool_failed'
            break

        messages.append({
            'role': 'tool',
            'step': step,
            'name': model_result['tool_name'],
            'content': tool_result
        })

        

    has_tool_result = False

    for message in messages:
        if message["role"] == "tool":
            has_tool_result = True

    if stetus == "llm_json_failed":
        final_answer = "模型工具调用解析失败：" + str(model_result["error"])
        

    elif has_tool_result is False:
        memory = read_memory()

        final_answer = get_direct_answer_from_model(
            user_input=user_input,
            available_tools=tools,
            messages=messages,
            model_name=model_name,
            memory=memory
        )
        stetus = 'final_answer'

    else:
        final_answer = get_final_answer_from_model(
            user_input=user_input,
            messages=messages,
            model_name=model_name
        )
    
    last_topic = None

    if last_tool_call is not None:
        last_topic = {
            'role': 'topic',
            'content': last_tool_call['tool_name']
        }
    elif '工具' in user_input:
        last_topic = 'tools'

    else:
        last_topic = 'chat'

    save_turn(user_input, final_answer, last_tool_call, last_topic)

    messages.append({
        "role": "assistant",
        "type": "final_answer",
        "content": final_answer
    })

    return {
        'messages': messages,
        'user_input': user_input,
        'final_answer': final_answer,
        'stetus': stetus,
        'step': step
    }

while True:
    user_input = input("请用户输入: ")
    if user_input == '/exit':
        break

    if user_input.startswith('/'):
        handle_command(user_input)
    else:
        result = run_agent(user_input)
        print(result['final_answer'])
        save_json(result, session_file)
            

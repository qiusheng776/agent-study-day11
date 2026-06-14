from model import get_tool_call_from_model, get_final_answer_from_model, check_task_completion_from_model
from run_tool import list_tools, run_tool
from memory_store import read_memory, save_turn
from parse_tool_call_result import parse_tool_call_result
from model import get_direct_answer_from_model
from direct_runner import run_direct_agent
from create_context import create_context

# 这里应该直接修改成接收路由llm输出的内容和模型名称
def run_agent(user_input, router_result, model_name='deepseek-chat'):
    context = create_context(user_input, model_name)
    context['router_result'] = router_result
    context['route'] = router_result['route']
    if router_result['route'] == 'tool_agent':

        while context['step'] < context['max_steps']:

            context['step'] += 1

            # 调用llm判断用户输入是否需要工具
            model_text = get_tool_call_from_model(
                user_input=context['user_input'],
                available_tools=context['tools'],
                messages=context['messages'],
                step=context['step'],
                max_steps=context['max_steps'],
                model_name=context['model_name'],
            )
            # 把llm输出的工具调用结果解析出来
            model_result = parse_tool_call_result(model_text)

            # 把工具调用结果添加到消息中
            context['messages'].append({
                'role': 'assistant',
                'type': 'tool_call',
                'step': context['step'],
                'content': model_result
            })
            
            # 如果工具调用失败，记录错误并结束
            if model_result['success'] is False:
                context['messages'].append({
                    'role': 'assistant',
                    'type': 'error',
                    'step': context['step'],
                    'content': model_result['error']
                })
                context['status'] = 'failed'
                context['stop_reason'] = 'llm_json_failed'
                continue 
            
            # 如果不需要工具，结束循环不需要工具不代表任务完成
            if model_result['need_tool'] is False:
                context['status'] = 'finished'
                context['stop_reason'] = 'no_tool_needed'
                break
                
            tool_result = run_tool(
                model_result['tool_name'],
                model_result['arguments']
            )
            
            # 记录最后一次工具调用
            context['last_tool_call'] = {
                'tool_name': model_result['tool_name'],
                'arguments': model_result['arguments'],
                'success': tool_result['success']
            }

            # 把工具执行结果添加到消息中
            context['messages'].append({
                'role': 'tool',
                'step': context['step'],
                'name': model_result['tool_name'],
                'content': tool_result
            })

            if tool_result['success'] is False:
                context['status'] = 'tool_failed'
                context['stop_reason'] = 'tool_failed'
                break

        # 两个判断：1. 达到最大步数 2. 状态仍然是running
        if context['step'] >= context['max_steps'] and context['status'] == 'running':
            # 调用模型检查任务是否完成
            completion_result = check_task_completion_from_model(
                user_input=context['user_input'],
                messages=context['messages'],
                model_name=context['model_name']
            )
        
            context['completion_result'] = completion_result
            
            # 如果模型检查失败，记录错误并结束
            if completion_result['success'] is False:
                context['status'] = 'stopped'
                context['stop_reason'] = 'completion_check_failed'

            # 如果任务全部完成
            elif completion_result['is_complete'] is True:
                context['status'] = 'finished'
                context['stop_reason'] = 'completed_at_max_steps'

            # 如果loop结束还需要更多工具
            elif completion_result['need_more_tool'] is True:
                context['status'] = 'stopped'
                context['stop_reason'] = 'max_steps_reached_need_more_tool'
            
            else:
                context['status'] = 'stopped'
                context['stop_reason'] = 'max_steps_reached'

    has_tool_result = False

    for message in context['messages']:
        if message["role"] == "tool":
            has_tool_result = True

    if context['stop_reason'] == "llm_json_failed":
        context['final_answer'] = "模型工具调用解析失败：" + str(model_result["error"])
        
    elif context['stop_reason'] == 'max_steps_reached':
        context['final_answer'] = get_direct_answer_from_model(
            user_input=context['user_input'],
            available_tools=context['tools'],
            messages=context['messages'],
            model_name=context['model_name'],
            memory=None
        )
    elif router_result['route'] == 'llm_only' or router_result['route'] == memory_query:
        context['final_answer'] = run_direct_agent
    elif has_tool_result is False:
        memory = read_memory()

        context['final_answer'] = get_direct_answer_from_model(
            user_input=context['user_input'],
            available_tools=context['tools'],
            messages=context['messages'],
            model_name=context['model_name'],
            memory=memory
        )
        
        context['status'] = 'chat'
        context['stop_reason'] = 'chat_finished'

    else:
        context['final_answer'] = get_final_answer_from_model(
            user_input=context['user_input'],
            messages=context['messages'],
            model_name=context['model_name']
        )
    
    last_topic = None

    if context['stop_reason'] == 'llm_json_failed':
        last_topic = None

    elif context['last_tool_call'] is not None:
        last_topic = {
            'role': 'topic',
            'content': context['last_tool_call']['tool_name']
        }

    elif '工具' in user_input:
        last_topic = 'tools'

    else:
        last_topic = 'chat'

    save_turn(context['user_input'], context['final_answer'], context['last_tool_call'], last_topic)

    context['messages'].append({
        "role": "assistant",
        "type": "final_answer",
        "content": context['final_answer']
    })

    return {
        'messages': context['messages'],
        'user_input': context['user_input'],
        'final_answer': context['final_answer'],
        'status': context['status'],
        'step': context['step'],
        'stop_reason': context['stop_reason'],
        'completion_result': context['completion_result']
    }

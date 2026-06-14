from run_tool import list_tools


def create_context(user_input, model_name):
    return {
        'user_input': user_input,
        'model_name': model_name,

        # 总路由层
        'router_result': None,
        'route': None,

        # 通用运行状态
        'max_steps': 3,
        'step': 0,
        'status': 'running',
        'stop_reason': None,
        'final_answer': None,

        # tool_agent 链路
        'tools': list_tools(),
        'last_tool_call': None,
        'completion_result': None,

        # llm_workflow 链路
        'workflow_steps': [],
        'workflow_next_step': None,
        'workflow_completion_result': None,
        'previous_result': None,
        'current_step_name': None,

        # direct_llm / memory_query 链路
        'memory': None,
        'use_memory': False,

        # 通用消息轨迹
        'messages': [
            {
                "role": "user",
                "content": user_input
            }
        ]
    }

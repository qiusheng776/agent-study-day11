from model import check_llm_workflow_completion_from_model,get_llm_workflow_next_step_from_model,get_llm_workflow_step_from_model
from create_context import create_context

def llm_workflow(user_input, model_name='deepseek-chat'):
    context = create_context(user_input, model_name)

    while context['step'] < context['max_steps']:
        context['step'] += 1
        # 获取下一步执行的步骤
        llm_response = get_llm_workflow_next_step_from_model(user_input,workflow_steps=context['workflow_steps'],model_name=model_name)
        context['current_step_name'] = llm_response['step_name']
        context['workflow_next_step'] = llm_response['step_name']

        # 执行当前步骤
        step_input = context['previous_result']
        llm_action = get_llm_workflow_step_from_model(llm_response['step_name'],user_input,step_input,model_name)

        # 记录步骤执行结果
        context["workflow_steps"].append({
            "step": context['step'],
            "step_name": context["current_step_name"],
            "input": step_input,
            "result": llm_action,
            "success": True
        })
        context['previous_result'] = llm_action

        # 检查工作流是否完成
        check_result = check_llm_workflow_completion_from_model(user_input, context['workflow_steps'], model_name)
        context['workflow_completion_result'] = check_result['is_complete']

        # 如果工作流完成，停止执行
        if check_result['is_complete']:
            context['status'] = 'finished'
            context['stop_reason'] = 'workflow_completed'
            break

        # 如果达到最大步骤数，停止执行
        if context['step'] >= context['max_steps']:
            context['status'] = 'stopped'
            context['stop_reason'] = 'workflow_max_steps_reached'
            break

    return {
        "workflow_completion_result": context['workflow_completion_result'],
        "step": context['step'],
        "current_step_name": context['current_step_name'],
        "workflow_steps": context['workflow_steps'],
        "workflow_next_step": context['workflow_next_step'],
        "status": context['status'],
        "max_steps": context['max_steps'],
        "stop_reason": context['stop_reason'],
        "final_answer": context['previous_result']
    }



            
    
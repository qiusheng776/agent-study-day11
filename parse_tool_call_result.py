import json

def parse_tool_call_result(model_text):
    try:
        model_text = json.loads(model_text)
        # 解析不了直接报错
    except json.JSONDecodeError:
        return{
            "success": False,
             "need_tool": False,
             "tool_name": None,
             "arguments": {},
             "message": "",
             "error": "模型输出不是合法 JSON",
             "raw_output": model_text
        }
    # 如果不是字典，报错
    if not isinstance(model_text,dict):
        return {
             "success": False,
             "need_tool": False,
             "tool_name": None,
             "arguments": {},
             "message": "",
             "error": "模型输出不是字典",
             "raw_output": model_text
        }
    
    errors = []
    need_tool = model_text.get('need_tool')
    tool_name = model_text.get('tool_name')
    arguments = model_text.get('arguments')
    message = model_text.get('message')
    success = model_text.get('success')
    
    if not isinstance(need_tool,bool):
        errors.append('need_tool 必须是布尔值')
        
    if not isinstance(success,bool):
        errors.append('success 必须是布尔值')
        
    if not isinstance(message,str):
        errors.append('message 必须是字符串')

    if need_tool == True:
        if not isinstance(arguments,dict):
            errors.append('argument 必须是字典')
        
        allowed_tools = ['get_github_user', 'get_windows_disk_status', 'scan_windows_temp_files','web_search','scan_windows_downloads']
        if tool_name not in allowed_tools:
            errors.append('tool_name必须是已注册的工具')

        if tool_name == 'get_github_user' and isinstance(arguments, dict):
            username = arguments.get('username')
            if not isinstance(username, str):
                errors.append('username 必须是字符串')

        if tool_name == 'get_windows_disk_status' and isinstance(arguments, dict):
            if arguments != {}:
                errors.append('get_windows_disk_status 不需要参数')
        
        if tool_name == 'scan_windows_temp_files' and isinstance(arguments, dict):
            min_size_mb = arguments.get('min_size_mb')
            max_items = arguments.get('max_items')
            if not isinstance(min_size_mb, int):
                errors.append('min_size_mb 必须是整数')
            if not isinstance(max_items, int):
                errors.append('max_items 必须是整数')
        
        if tool_name == 'web_search' and isinstance(arguments, dict):
            query = arguments.get('query')
            max_result = arguments.get('max_result')
            if not isinstance(query, str):
                errors.append('query 必须是字符串')
            if not isinstance(max_result, int):
                errors.append('max_result 必须是整数')
        
        if tool_name == 'scan_windows_downloads' and isinstance(arguments, dict):
            min_size_mb = arguments.get('min_size_mb')
            max_items = arguments.get('max_items')
            if not isinstance(min_size_mb, int):
                errors.append('min_size_mb 必须是整数')
            if not isinstance(max_items, int):
                errors.append('max_items 必须是整数')
        
    if need_tool == False:
        if tool_name not in ('',None):
            errors.append('tool_name 必须是非空字符串')
        
        if arguments not in ({},None):
            errors.append('arguments 必须为空')

    if errors:
        return {
            "success": False,
             "need_tool": False,
             "tool_name": None,
             "arguments": {},
             "message": message,
             "error": errors,
             "raw_output": model_text
        }
    return {
        "success": True,
        "need_tool": need_tool,
        "tool_name": tool_name,
        "arguments": arguments,
        "message": message,
        "error": [],
        "raw_output": model_text
    }
            
            

        
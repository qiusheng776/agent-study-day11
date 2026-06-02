from tool_registry import TOOLS


def run_tool(tool_name, arguments):
    if tool_name not in TOOLS:
        return {
            'success': False,
            'message': '工具不存在',
            'data': None
        }

    function = TOOLS[tool_name]['function']

    if arguments is None:
        arguments = {}

    if tool_name == 'get_github_user':
        return function(arguments['username'])

    if tool_name == 'scan_windows_temp_files':
        return function(arguments.get('min_size_mb', 100), arguments.get('max_items', 50))
    
    if tool_name == 'web_search':
        return function(arguments['query'], arguments.get('max_result', 5))

    if tool_name == 'scan_windows_downloads':
        return function(arguments.get('min_size_mb', 50), arguments.get('max_items', 30))
    
    return function()


def list_tools(tool_name=None):
    if tool_name is None:
        tool_data = {}
        for name, info in TOOLS.items():
            tool_data[name] = {
                'description': info['description'],
                'arguments': info['arguments']
            }

        return {
            'success': True,
            'message': '工具列表',
            'data': tool_data
        }

    if tool_name in TOOLS:
        info = TOOLS[tool_name]
        return {
            'success': True,
            'message': '工具详情',
            'data': {
                'description': info['description'],
                'arguments': info['arguments']
            }
        }

    return {
        'success': False,
        'message': '工具不存在',
        'data': None
    }



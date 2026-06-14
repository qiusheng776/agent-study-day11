from function_to_json import function_to_json

TOOLS = {}

def tool(func):
    schema = function_to_json(func)
    function_info = schema['function']
    
    TOOLS[function_info['name']] = {
        'function': func,
        'description': function_info['description'],
        'arguments': function_info['parameters']['properties'],
        'required': function_info['parameters'].get('required', [])
    }
    return func

import tools.web_search
import tools.github_tools
import tools.get_windows_disk_status
import tools.scan_windows_temp_files
import tools.scan_windows_downloads
import tools.scan_large_files

from tools.github_tools import get_github_user
from tools.get_windows_disk_status import get_windows_disk_status
from tools.scan_windows_temp_files import scan_windows_temp_files
from tools.scan_windows_downloads import scan_windows_downloads
from tools.web_search import web_search
from function_to_json import function_to_json

REGISTERED_FUNCTIONS ={
    get_github_user,
    get_windows_disk_status,
    scan_windows_temp_files,
    scan_windows_downloads,
    web_search
}
TOOLS = {}

for func in REGISTERED_FUNCTIONS:
    schema = function_to_json(func)
    function_info = schema['function']

    TOOLS[function_info['name']] = {
        'function': func,
        'description': function_info['description'],
        'arguments': function_info['parameters']['properties'],
        'required': function_info['parameters'].get('required', [])
    }



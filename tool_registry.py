from tools.github_tools import get_github_user
from tools.get_windows_disk_status import get_windows_disk_status
from tools.scan_windows_temp_files import scan_windows_temp_files
from tools.scan_windows_downloads import scan_windows_downloads
from tools.web_search import web_search

TOOLS = {
    'get_github_user': {
        'function': get_github_user,
        'description': '查询GitHub用户信息',
        'arguments': {
            'username': {
                'type': 'string',
                'description': 'GitHub用户名'
            }
        }
    },
    'get_windows_disk_status': {
        'function': get_windows_disk_status,
        'description': '查询Windows硬盘状态',
        'arguments': {}
    },
    'scan_windows_temp_files': {
        'function': scan_windows_temp_files,
        'description': '扫描Windows临时文件',
        'arguments': {
            'min_size_mb': {
                'type': 'integer',
                'description': '最小文件大小（MB）(默认参数10)'
            },
            'max_items': {
                'type': 'integer',
                'description': '最大返回数量(默认参数30)'
            }
        }
    },
    'scan_windows_downloads': {
        'function': scan_windows_downloads,
        'description': '扫描Windows下载文件',
        'arguments': {
            'min_size_mb': {
                'type': 'integer',
                'description': '最小文件大小（MB）(默认参数50)'
            },
            'max_items': {
                'type': 'integer',
                'description': '最大返回数量(默认参数30)'
            }
        }
    },
    'web_search': {
        'function': web_search,
        'description': '联网搜索',
        'arguments': {
            'query': {
                'type': 'string',
                'description': '搜索关键词'
            },
            'max_result': {
                'type': 'integer',
                'description': '最大返回数量(默认参数5)'
            }
        }
    }
}

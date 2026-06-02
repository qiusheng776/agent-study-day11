import json 
from pathlib import Path

# 保存JSON文件
def save_json(data, file_name):
    folder = Path(file_name).parent
    
    if folder:
        folder.mkdir(parents=True, exist_ok=True)
    
    with open(file_name, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return {
        'success': True,
        'message': '文件保存成功',
        'data':str(file_name)
    }

# 加载JSON文件
def load_json(file_name):
    with open(file_name, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data

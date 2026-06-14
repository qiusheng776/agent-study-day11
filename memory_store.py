from json_tools import load_json, save_json
from pathlib import Path
import os
from model import compress_memory_from_model

MEMORY_FILE = Path(__file__).parent / "outputs" / "memory.json"

MEMORY_MAX_MESSAGES = 5
MEMORY_KEEP_MESSAGES = 3

# 读取内存
def read_memory():
    # 如果文件不存在，返回空列表
    if not os.path.exists(MEMORY_FILE):
        return {
            'recent_messages': [],
            'last_tool_call':None,
            'last_topic':None,
            'summary': ''
        }
    # 读取文件内容
    data = load_json(MEMORY_FILE)
    return {
        'recent_messages': data.get("recent_messages", []),
        'last_tool_call': data.get("last_tool_call"),
        'last_topic': data.get("last_topic"),
        'summary': data.get("summary", "")
    }

# 保存内存
def save_memory(messages):
    # 如果传进来[]就是清空
    if messages == []:
        messages = {
            'summary': '',
            'recent_messages': [],
            'last_tool_call':None,
            'last_topic':None
        }   
    # 保存消息到文件
    data = {
        "recent_messages": messages['recent_messages'],
        "last_tool_call": messages['last_tool_call'],
        "last_topic": messages['last_topic'],
        "summary": messages['summary']
    }
    save_json(data, MEMORY_FILE)

# 添加消息到内存
def append_message(messages,role,content):
    # 添加消息到列表
    message = {
        "role": role,
        "content": content
    }
    messages.append(message)

def save_turn(user_input,file_answer,last_tool_call=None,last_topic=None):
    memory = read_memory()
    
    recent_messages = memory['recent_messages']

    if len(recent_messages) > MEMORY_MAX_MESSAGES:
        # 提取后面的keep_messages条消息
        old_messages = recent_messages[:-MEMORY_KEEP_MESSAGES]
        # 保留前面的messages
        keep_messages = recent_messages[-MEMORY_KEEP_MESSAGES:]
        
        memory['summary'] = compress_memory_from_model(
            old_summary = memory['summary'],
            old_messages = old_messages
        )
        memory['recent_messages'] = keep_messages

    else:
        memory['recent_messages'] = recent_messages
    
    # 添加用户输入
    recent_messages.append({
        "role": "user",
        "content": user_input
    })
    
    # 添加助手回复
    recent_messages.append({
        "role": "assistant",
        "content": file_answer
    })

    memory['recent_messages'] = recent_messages[-8:]
    
    if last_tool_call is not None:
        memory['last_tool_call'] = last_tool_call

    if last_topic is not None:
        memory['last_topic'] = last_topic
    
    save_memory(memory)
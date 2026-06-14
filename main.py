from json_tools import save_json
from pathlib import Path
from agent import run_agent
from handle_command import handle_command
from router import router_user_input
from create_context import create_context

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / 'outputs'
# 记录一次对话的所有信息
session_file = OUTPUT_DIR / 'session.json'

while True:
    user_input = input("请用户输入: ")
    if user_input == '/exit':
        break

    if user_input.startswith('/'):
        handle_command(user_input)
    else:
        router_result = router_user_input(user_input)
        result = run_agent(user_input, router_result = router_result)
        print(result['final_answer'])
        save_json(result, session_file)
            

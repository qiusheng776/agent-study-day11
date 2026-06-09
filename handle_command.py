from memory_store import read_memory, save_memory
from run_tool import list_tools

def handle_command(user_input):
    if user_input == '/tools':
        print(list_tools())

    elif user_input == '/memory':
        print(read_memory())

    elif user_input == '/clear':
        # 清空内存
        save_memory([])
        print('记忆清除成功')

    else:
        print('未知指令')

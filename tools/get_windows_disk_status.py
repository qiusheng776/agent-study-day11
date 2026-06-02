import subprocess
import json


def get_windows_disk_status():
    # 1. 准备 PowerShell 命令
    # Get-CimInstance Win32_LogicalDisk：获取 Windows 逻辑磁盘信息
    # DriveType=3：只选择本地硬盘，不要光驱、网络盘等
    # Select-Object DeviceID, Size, FreeSpace：只保留盘符、总容量、剩余空间
    # ConvertTo-Json：把 PowerShell 输出转成 JSON，方便 Python 解析
    ps_command = (
        "Get-CimInstance Win32_LogicalDisk -Filter \"DriveType=3\" | "
        "Select-Object DeviceID, Size, FreeSpace | "
        "ConvertTo-Json"
    )

    # 2. 准备要执行的命令
    # powershell.exe：启动 Windows PowerShell
    # -NoProfile：不加载 PowerShell 配置，减少干扰
    # -Command：后面跟着真正要执行的 PowerShell 命令
    command = [
        "powershell.exe",
        "-NoProfile",
        "-Command",
        ps_command
    ]

    # 3. 执行 PowerShell 命令
    # capture_output=True：捕获命令输出
    # text=True：让输出结果变成字符串，而不是 bytes
    result = subprocess.run(
        command,
        capture_output=True,
        text=True
    )

    # 4. 判断 PowerShell 命令有没有执行失败
    # returncode 等于 0 表示成功
    # returncode 不等于 0 表示失败
    if result.returncode != 0:
        return {
            "success": False,
            "message": "查询 Windows 硬盘状态失败",
            "data": {
                "error": result.stderr
            }
        }

    # 5. 把 PowerShell 输出的 JSON 字符串转成 Python 数据
    # 如果有多个磁盘，json.loads 后通常是 list
    # 如果只有一个磁盘，可能是 dict
    disk_info = json.loads(result.stdout)

    # 6. 统一处理成 list，方便后面 for 循环
    if isinstance(disk_info, dict):
        disk_info = [disk_info]
    # 7. 准备一个列表，用来保存每个磁盘的整理结果
    disks = []

    # 8. 遍历每一个磁盘
    for disk in disk_info:
        # DeviceID 是盘符，比如 C:、D:、E:
        drive = disk["DeviceID"]
        # Size 是总容量，单位是 Byte
        # FreeSpace 是剩余空间，单位也是 Byte
        total_bytes = disk["Size"]
        free_bytes = disk["FreeSpace"]

        # 已用空间 = 总容量 - 剩余空间
        used_bytes = total_bytes - free_bytes

        # Byte 转 GB
        # 1024 Byte = 1 KB
        # 1024 KB = 1 MB
        # 1024 MB = 1 GB
        total_gb = total_bytes / 1024 / 1024 / 1024
        free_gb = free_bytes / 1024 / 1024 / 1024
        used_gb = used_bytes / 1024 / 1024 / 1024

        # 使用率 = 已用空间 / 总容量 * 100
        used_percent = used_bytes / total_bytes * 100

        # 把当前磁盘的信息放进 disks 列表
        disks.append({
            "drive": drive,
            "total_gb": round(total_gb, 2).__str__() + "GB",
            "free_gb": round(free_gb, 2).__str__() + "GB",
            "used_gb": round(used_gb, 2).__str__() + "GB",
            "used_percent": round(used_percent, 2).__str__() + "%"
        })

    # 9. 返回 Agent 工具统一结构
    # success：工具是否执行成功
    # message：给人看的说明
    # data：真正的数据
    return {
        "success": True,
        "message": "查询 Windows 硬盘状态成功",
        "data": {
            "disks": disks
        }
    }


# 这段代码只在直接运行本文件时执行
# 如果别的文件 import 这个函数，这段不会自动执行
if __name__ == "__main__":
    result = get_windows_disk_status()

    # 把返回的 dict 格式化打印出来
    # ensure_ascii=False：中文不要变成 unicode 编码
    # indent=2：缩进 2 个空格，方便阅读
    print(json.dumps(result, ensure_ascii=False, indent=2))
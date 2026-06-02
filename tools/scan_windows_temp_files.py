import subprocess
import json


def scan_windows_temp_files(min_size_mb:int = 10, max_items:int = 30):
    # 1. 准备 PowerShell 命令
    # $env:TEMP：当前用户的临时文件夹
    # C:\Windows\Temp：系统临时文件夹
    # Get-ChildItem：扫描文件
    # -Recurse：递归扫描子文件夹
    # -File：只要文件，不要文件夹
    # Where-Object：筛选大于指定大小的文件
    # Sort-Object Length -Descending：按文件大小从大到小排序
    # Select-Object -First：只取前 max_items 个，避免结果太多
    # ConvertTo-Json：把结果转成 JSON，方便 Python 解析

    min_size_bytes = min_size_mb * 1024 * 1024

    ps_command = f"""
$paths = @($env:TEMP, "C:\\Windows\\Temp")
$results = @()

foreach ($path in $paths) {{
    if (Test-Path $path) {{
        $files = Get-ChildItem -Path $path -Recurse -File -ErrorAction SilentlyContinue |
            Where-Object {{ $_.Length -ge {min_size_bytes} }} |
            Select-Object FullName, Length, LastWriteTime

        $results += $files
    }}
}}

$results |
Sort-Object Length -Descending |
Select-Object -First {max_items} |
ConvertTo-Json
"""

    # 2. 准备执行 PowerShell 的命令
    command = [
        "powershell.exe",
        "-NoProfile",
        "-Command",
        ps_command
    ]

    # 3. 执行命令
    result = subprocess.run(
        command,
        capture_output=True,
        text=True
    )

    # 4. 如果 PowerShell 执行失败，返回失败结果
    if result.returncode != 0:
        return {
            "success": False,
            "message": "扫描 Windows 临时文件失败",
            "data": {
                "error": result.stderr
            }
        }

    # 5. 如果没有扫描到文件，PowerShell 可能输出空内容
    if result.stdout.strip() == "":
        return {
            "success": True,
            "message": "没有发现超过指定大小的临时文件",
            "data": {
                "candidates": []
            }
        }

    # 6. 把 PowerShell 输出的 JSON 字符串转成 Python 数据
    temp_files = json.loads(result.stdout)

    # 7. 如果只有一个文件，PowerShell 可能返回 dict
    # 为了后面统一 for 循环，这里转成 list
    if isinstance(temp_files, dict):
        temp_files = [temp_files]
    # 8. 整理扫描结果
    candidates = []

    for file in temp_files:
        path = file["FullName"]
        size_bytes = file["Length"]
        modified_time = file["LastWriteTime"]

        size_mb = size_bytes / 1024 / 1024

        candidates.append({
            "path": path,
            "size_mb": round(size_mb, 2),
            "modified_time": modified_time,
            "reason": "Windows 临时目录中的大文件，可能可以清理，但需要用户确认"
        })

    # 9. 返回 Agent 工具统一结构
    return {
        "success": True,
        "message": "扫描 Windows 临时文件完成",
        "data": {
            "min_size_mb": f"{min_size_mb}MB",
            "count": len(candidates),
            "candidates": candidates
        }
    }


# # 这段只在直接运行本文件时执行
# if __name__ == "__main__":
#     result = scan_windows_temp_files()

#     print(json.dumps(result, ensure_ascii=False, indent=2))
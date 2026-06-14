from pathlib import Path
from tool_registry import tool

@tool
def scan_windows_downloads(min_size_mb:int=50, max_items:int=30):
    """
    工具介绍：
    扫描 Windows 下载目录中的大文件，帮助用户发现可能占用空间较大的下载内容。

    工具如何使用：
    传入 min_size_mb 作为最小文件大小阈值，传入 max_items 控制最多返回多少个文件。

    工具使用示例：
    scan_windows_downloads(min_size_mb=50, max_items=30)

    工具边界：
    只扫描下载目录并列出文件，不删除、不移动、不修改文件；是否清理需要用户自己确认。

    返回结构说明：
    返回 dict，包含 success、message、data。成功时 data 包含 downloads_path、min_size_mb、max_items、items；items 是列表，每项包含 name、path、size_mb。失败时 data 包含 downloads_path 和空 items。
    """
    downloads_path = Path(r"C:\Users\q1817\Downloads")

    if not downloads_path.exists():
        return {
            "success": False,
            "message": "没有找到 Windows 下载目录",
            "data": {
                "downloads_path": str(downloads_path),
                "items": [],
            },
        }

    min_size_bytes = min_size_mb * 1024 * 1024
    items = []

    for file_path in downloads_path.rglob("*"):
        if not file_path.is_file():
            continue

        try:
            size_bytes = file_path.stat().st_size
        except OSError:
            continue

        if size_bytes < min_size_bytes:
            continue

        size_mb = round(size_bytes / 1024 / 1024, 2)

        items.append(
            {
                "name": file_path.name,
                "path": str(file_path),
                "size_mb": size_mb,
            }
        )

    items.sort(key=lambda item: item["size_mb"], reverse=True)
    items = items[:max_items]

    return {
        "success": True,
        "message": f"已扫描 Windows 下载目录，找到 {len(items)} 个大于 {min_size_mb}MB 的文件",
        "data": {
            "downloads_path": str(downloads_path),
            "min_size_mb": min_size_mb,
            "max_items": max_items,
            "items": items,
        },
    }


if __name__ == "__main__":
    result = scan_windows_downloads(min_size_mb=50, max_items=30)
    print(result)
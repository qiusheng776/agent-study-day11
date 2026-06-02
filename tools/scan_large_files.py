from pathlib import Path


# 根据文件路径，大致判断这个文件属于哪一类。
# 注意：这里只是给 LLM 做参考，不代表一定能删除。
def classify_path(file_path):
    # 把 Path 对象转成字符串，并统一转成小写，方便后面判断路径里包含什么关键词。
    path_text = str(file_path).lower()

    # Windows 系统目录里的文件，一般不建议手动删除。
    if "\\windows\\" in path_text:
        return "system_file"

    # Program Files 里通常是软件安装目录，也不建议直接删除里面的文件。
    if "\\program files\\" in path_text or "\\program files (x86)\\" in path_text:
        return "program_file"

    # 用户临时目录，后面可以作为清理候选，但也要先确认。
    if "\\users\\q1817\\appdata\\local\\temp\\" in path_text:
        return "temp_file"

    # 用户目录下的文件，比如桌面、下载、文档、视频等。
    # 这类文件是否删除，应该由用户自己判断。
    if "\\users\\q1817\\" in path_text:
        return "user_file"

    # 其他无法明确分类的路径，先标记为 unknown。
    return "unknown"


# 扫描大文件的工具函数。
# root_path：从哪个目录开始扫描，默认是整个 C 盘。
# min_size_mb：只保留大于多少 MB 的文件，默认 500MB。
# max_items：最多返回多少个文件，默认返回前 50 个。
def scan_large_files(root_path="C:/", min_size_mb=500, max_items=50):
    # 把字符串路径变成 Path 对象，后面才能用 exists、rglob、stat 这些方法。
    root = Path(root_path)

    # 如果扫描目录不存在，直接返回失败结果。
    if not root.exists():
        return {
            "success": False,
            "message": "扫描目录不存在",
            "data": {
                "root_path": str(root),
                "items": [],
            },
        }

    # Python 读到的文件大小单位是字节。
    # 这里把 MB 转成字节，后面才能和 file_path.stat().st_size 比较。
    min_size_bytes = min_size_mb * 1024 * 1024

    # items 用来保存符合条件的大文件。
    items = []

    # skipped_count 用来记录因为权限或系统限制，无法读取大小的文件数量。
    skipped_count = 0

    # rglob("*") 表示递归扫描 root 下面的所有文件和文件夹。
    for file_path in root.rglob("*"):
        # 如果不是文件，比如是文件夹，就跳过。
        if not file_path.is_file():
            continue

        try:
            # stat().st_size 可以拿到文件大小，单位是字节。
            size_bytes = file_path.stat().st_size
        except OSError:
            # 有些系统文件可能没有权限读取，不能让整个扫描中断，所以跳过并计数。
            skipped_count += 1
            continue

        # 如果文件小于设定阈值，就跳过。
        if size_bytes < min_size_bytes:
            continue

        # 把字节转换成 MB，保留两位小数，方便人看。
        size_mb = round(size_bytes / 1024 / 1024, 2)

        # 把这个大文件的信息保存进 items。
        items.append(
            {
                "name": file_path.name,
                "path": str(file_path),
                "size_mb": size_mb,
                "category": classify_path(file_path),
            }
        )

    # 按 size_mb 从大到小排序，让最大的文件排在前面。
    items.sort(key=lambda item: item["size_mb"], reverse=True)

    # 只保留前 max_items 个，避免返回太多内容给 LLM。
    items = items[:max_items]

    # 按 Agent 工具统一格式返回结果。
    return {
        "success": True,
        "message": f"已扫描 {root}，找到 {len(items)} 个大于 {min_size_mb}MB 的文件",
        "data": {
            "root_path": str(root),
            "min_size_mb": min_size_mb,
            "max_items": max_items,
            "skipped_count": skipped_count,
            "items": items,
        },
    }


# 直接运行这个文件时，会执行下面的测试代码。
# 如果以后这个函数被 Agent 调用，下面这段不会自动执行。
if __name__ == "__main__":
    result = scan_large_files(root_path="C:/", min_size_mb=500, max_items=50)
    print(result)

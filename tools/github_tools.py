import requests

from tool_registry import tool

@tool
def get_github_user(username:str):
    """
    工具介绍：
    查询指定 GitHub 用户的公开资料，用于回答“某个 GitHub 用户是谁、主页是什么、仓库数量、粉丝数量”等问题。

    工具如何使用：
    传入 GitHub 用户名 username，函数会请求 GitHub 用户公开 API。

    工具使用示例：
    get_github_user(username="qiusheng776")

    工具边界：
    只查询公开用户资料，不读取私有仓库、不修改 GitHub 数据；未认证请求可能触发 GitHub rate limit。

    返回结构说明：
    返回 dict，包含 success、message、data。成功时 data 包含 login、name、email、avatar_url、public_repos、html_url、followers；失败时 data 包含 status_code、error、rate_limit_remaining、rate_limit_reset。
    """
    url = f"https://api.github.com/users/{username}"
    response = requests.get(url)
    if response.status_code != 200:
        try:
            error_data = response.json()
        except Exception:
            error_data = {
                "raw_text": response.text
            }
        
        return {
            "success": False,
            "message": "查询用户失败",
            "data": {
                "status_code": response.status_code,
                "error": error_data,
                "rate_limit_remaining": response.headers.get("X-RateLimit-Remaining"),
                "rate_limit_reset": response.headers.get("X-RateLimit-Reset")
            }
        }

    data = response.json()
    return {
        'success': True,
        'message':'查询成功',
        'data':{
            'login': data['login'],
            'name': data['name'],
            'email': data['email'],
            'avatar_url': data['avatar_url'],
            'public_repos': data['public_repos'],
            'html_url': data['html_url'],
            'followers': data['followers'],
        }
    }
    
import requests

def get_github_user(username:str):
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
    
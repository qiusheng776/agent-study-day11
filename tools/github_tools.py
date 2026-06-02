import requests

def get_github_user(username):
    url = f"https://api.github.com/users/{username}"
    response = requests.get(url)
    if response.status_code != 200:
        return {
            'success': False,
            'message': "查询用户失败",
            'data': None
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
    
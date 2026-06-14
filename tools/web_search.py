import requests
from bs4 import BeautifulSoup

from tool_registry import tool

@tool
def web_search(query:str, max_result:int=5):
    """
    工具介绍：
    使用 DuckDuckGo 搜索网页，返回搜索结果标题、摘要和链接。

    工具如何使用：
    传入搜索关键词 query，并用 max_result 控制最多返回多少条结果。

    工具使用示例：
    web_search(query="Python Agent 教程", max_result=5)

    工具边界：
    只做网页搜索和结果摘要提取，不保证搜索结果一定完整或实时；不打开网页深度阅读，不执行网页里的任何内容。

    返回结构说明：
    返回 dict，包含 success、message、data。成功时 data 包含 query 和 results；results 是列表，每项包含 title、snippet、link。失败时 data 为 None。
    """
    usl = 'https://duckduckgo.com/html/'

    params = {
        'q': query
    }

    headers = {
        'User-Agent': 'Mozilla/5.0'
    }

    try:
        response = requests.get(
            usl,
            params=params,
            headers=headers
        )
    except requests.RequestException as e:
        return {
            'success': False,
            'message':f'联网搜索失败{e}',
            'data':None
        }

    if response.status_code != 200:
        return {
            'success': False,
            'message':f'联网搜索失败,状态码:{response.status_code}',
            'data':None
        }
    # 提取完整版的网页内容,然后变成方便处理的格式
    soup = BeautifulSoup(response.text, 'html.parser')

    # .select()是css选择器选择class为result的元素
    result_items = soup.select('.result')

    results = []

    for item in result_items[:max_result]:
        title_tag = item.select_one('.result__title a')

        snippet_tag = item.select_one('.result__snippet')

        if title_tag is None:
            continue

        title = title_tag.get_text(strip=True)

        snippet = snippet_tag.get_text(strip=True)

        link = title_tag.get('href')
        
        results.append({
            'title': title,
            'snippet': snippet,
            'link': link
        })
    
    return {
        'success': True,
        'message': '联网搜索成功',
        'data': {
            'query': query,
            'results': results
        }
    }

if __name__ == '__main__':
    result = web_search('Python编程')
    print(result)
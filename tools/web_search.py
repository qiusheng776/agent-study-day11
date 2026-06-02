import requests
from bs4 import BeautifulSoup

def web_search(query, max_result=5):
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
    except response.RequestException as e:
        return {
            'success': False,
            'messsage':f'联网搜索失败{e}',
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

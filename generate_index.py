import os, json, requests
from collections import defaultdict

token = os.environ['GITHUB_TOKEN']
repo = os.environ['GITHUB_REPOSITORY']
headers = {'Authorization': f'token {token}', 'Accept': 'application/vnd.github+json'}
api_url = f'https://api.github.com/repos/{repo}/releases?per_page=100'

# 获取所有 Release（处理分页）
releases = []
page = 1
while True:
    resp = requests.get(f'{api_url}&page={page}', headers=headers)
    if resp.status_code != 200:
        break
    data = resp.json()
    if not data:
        break
    releases.extend(data)
    page += 1

# 收集文件信息
files = []
for rel in releases:
    for asset in rel.get('assets', []):
        files.append({
            'path': asset['name'],          # 文件名，可包含 / 模拟目录
            'size': asset['size'],
            'download': asset['browser_download_url'],
            'tag': rel['tag_name']
        })

# 构建文件夹树
def add_to_tree(tree, parts, info):
    node = tree
    for part in parts[:-1]:   # 中间部分为文件夹
        if part not in node:
            node[part] = {}
        node = node[part]
    node[parts[-1]] = info    # 叶子节点为文件

tree = {}
for f in files:
    parts = f['path'].split('/')
    add_to_tree(tree, parts, f)

# 递归生成 HTML
def render_tree(node, indent=0):
    if not node:
        return ''
    html = '<ul>\n'
    # 分离文件夹与文件
    dirs = {k: v for k, v in node.items() if isinstance(v, dict)}
    files = {k: v for k, v in node.items() if not isinstance(v, dict)}
    for name in sorted(dirs.keys(), key=str.lower):
        html += f'<li>📁 <strong>{name}</strong>\n'
        html += render_tree(dirs[name], indent+1)
        html += '</li>\n'
    for name in sorted(files.keys(), key=str.lower):
        info = files[name]
        size_mb = info['size'] / (1024*1024)
        html += f'<li>📄 <a href="{info["download"]}">{name}</a>  ({size_mb:.2f} MB)</li>\n'
    html += '</ul>\n'
    return html

body = render_tree(tree)
html_content = f'''<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>云盘文件列表</title>
<style>
  body {{ font-family: system-ui, sans-serif; max-width: 900px; margin: 2rem auto; }}
  ul {{ list-style: none; padding-left: 1.5rem; }}
  li {{ margin: 0.3rem 0; }}
  a {{ text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
</style>
</head>
<body>
<h1>📦 我的云盘</h1>
{body}
</body>
</html>'''

os.makedirs('public', exist_ok=True)
with open('public/index.html', 'w', encoding='utf-8') as f:
    f.write(html_content)
print('索引页面已生成 → public/index.html')

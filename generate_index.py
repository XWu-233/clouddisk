import os, json, requests
from collections import defaultdict

token = os.environ['GITHUB_TOKEN']
repo = os.environ['GITHUB_REPOSITORY']
headers = {'Authorization': f'token {token}', 'Accept': 'application/vnd.github+json'}
api_url = f'https://api.github.com/repos/{repo}/releases?per_page=100'

# 获取所有 Release（分页）
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

# 收集所有附件
files = []
for rel in releases:
    for asset in rel.get('assets', []):
        files.append({
            'path': asset['name'],
            'size': asset['size'],
            'download': asset['browser_download_url'],
            'tag': rel['tag_name']
        })

# 构建树：节点可以是 dict（文件夹）或文件信息 dict
def add_to_tree(tree, parts, info):
    node = tree
    for part in parts[:-1]:
        # 如果中间节点是文件信息（冲突），跳过
        if part in node and isinstance(node[part], dict) and 'download' in node[part]:
            # 这里简单地保留原文件节点，不再继续添加子路径
            return
        if part not in node:
            node[part] = {}
        node = node[part]
    # 最后一部分：直接覆盖（可能是文件信息）
    node[parts[-1]] = info

tree = {}
for f in files:
    parts = f['path'].split('/')
    add_to_tree(tree, parts, f)

def is_file_info(node):
    return isinstance(node, dict) and 'download' in node

def render_tree(node, indent=0):
    if not node:
        return ''
    html = '<ul>\n'
    # 分离：文件夹（不含 download 键）与文件（含 download 键）
    dirs = {}
    file_infos = {}
    for k, v in node.items():
        if is_file_info(v):
            file_infos[k] = v
        elif isinstance(v, dict):
            dirs[k] = v
        # 其他非 dict 类型视作文件（一般不会出现）
        else:
            file_infos[k] = v

    for name in sorted(dirs.keys(), key=str.lower):
        html += f'<li>📁 <strong>{name}</strong>\n'
        html += render_tree(dirs[name], indent+1)
        html += '</li>\n'
    for name in sorted(file_infos.keys(), key=str.lower):
        info = file_infos[name]
        if isinstance(info, dict) and 'download' in info:
            size_mb = info['size'] / (1024*1024)
            html += f'<li>📄 <a href="{info["download"]}">{name}</a>  ({size_mb:.2f} MB)</li>\n'
        else:
            # 异常情况：展示字符串
            html += f'<li>📄 {name}: {info}</li>\n'
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
<h1>📦 云盘文件列表</h1>
{body}
</body>
</html>'''

os.makedirs('public', exist_ok=True)
with open('public/index.html', 'w', encoding='utf-8') as f:
    f.write(html_content)
print('索引页面已生成 → public/index.html')

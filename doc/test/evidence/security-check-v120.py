# -*- coding: utf-8 -*-
"""TT-12-051 安全专项测试：输入校验/SQL注入/越权/敏感信息/响应头."""
import json
import urllib.request
import urllib.error


def req(method, url, data=None, token=None):
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    r = urllib.request.Request(url, method=method,
                               data=json.dumps(data).encode() if data else None,
                               headers=headers)
    try:
        with urllib.request.urlopen(r, timeout=8) as resp:
            return resp.status, json.loads(resp.read().decode()), dict(resp.headers)
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode()), dict(e.headers)


BASE = 'http://127.0.0.1:8000'
results = []

# 登录拿 token
s, b, _ = req('POST', BASE + '/api/v1/auth/login', {'username': 'admin', 'password': 'admin123'})
token = b['access_token']
results.append(('登录(前置)', s, 200))

print('== 输入校验 ==')
# 超长 name (>100)
s, b, _ = req('POST', BASE + '/api/v1/ai-apps',
              {'name': 'x' * 101, 'llm_config': {'provider': 'p', 'model': 'm'}}, token=token)
results.append(('超长name(>100)->422', s, 422))
print('超长name:', s, b.get('code'))
# 空 name
s, b, _ = req('POST', BASE + '/api/v1/ai-apps',
              {'name': '', 'llm_config': {'provider': 'p', 'model': 'm'}}, token=token)
results.append(('空name->422', s, 422))
print('空name:', s, b.get('code'))
# 缺 llm_config
s, b, _ = req('POST', BASE + '/api/v1/ai-apps', {'name': 'ok'}, token=token)
results.append(('缺llm_config->422', s, 422))
print('缺llm_config:', s, b.get('code'))

print('== SQL注入 ==')
s, b, _ = req('POST', BASE + '/api/v1/ai-apps',
              {'name': "x' OR '1'='1", 'llm_config': {'provider': 'p', 'model': 'm'}}, token=token)
results.append(('SQL注入name->200参数化', s, 200))
print('SQL注入name:', s, b.get('code'), '创建成功(参数化):', 'id' in b.get('data', {}))

print('== 越权/鉴权 ==')
s, b, _ = req('GET', BASE + '/api/v1/modules')
results.append(('无token->401', s, 401))
print('无token:', s, b.get('code'))
s, b, _ = req('GET', BASE + '/api/v1/modules', token='invalid.token.here')
results.append(('伪token->401', s, 401))
print('伪token:', s, b.get('code'))

print('== 敏感信息 ==')
s, b, _ = req('POST', BASE + '/api/v1/auth/login', {'username': 'admin', 'password': 'wrong'})
results.append(('错误密码->401', s, 401))
print('错误密码:', s, b.get('code'), '| 响应含password字段:', 'password' in json.dumps(b))
s, b, _ = req('POST', BASE + '/api/v1/auth/login', {'username': 'admin', 'password': 'admin123'})
print('登录响应字段:', list(b.keys()))

print('== 响应头 ==')
s, b, h = req('GET', BASE + '/health')
print('health:', s, {k: v for k, v in h.items() if k.lower() in ('server', 'x-content-type-options', 'content-type')})

print()
print('== 汇总 ==')
fails = [r for r in results if r[1] != r[2]]
for r in results:
    print(('PASS' if r[1] == r[2] else 'FAIL'), r[0], '->', r[1], '(期望', r[2], ')')
print('结论:', '通过' if not fails else '失败: ' + str(fails))

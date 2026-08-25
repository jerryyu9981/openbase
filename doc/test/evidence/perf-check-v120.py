# -*- coding: utf-8 -*-
"""TT-12-052 性能测试：关键接口响应时间（P50/P99/吞吐）."""
import json
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor

BASE = 'http://127.0.0.1:8000'


def http(method, url, data=None, token=None):
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    r = urllib.request.Request(url, method=method,
                               data=json.dumps(data).encode() if data else None,
                               headers=headers)
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(r, timeout=10) as resp:
            resp.read()
            return (time.perf_counter() - t0) * 1000
    except urllib.error.HTTPError:
        return (time.perf_counter() - t0) * 1000


def bench(name, fn, n=30, concurrency=10):
    latencies = []
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        for _ in range(n):
            latencies.append(pool.submit(fn).result())
    latencies.sort()
    p50 = latencies[int(n * 0.5)]
    p99 = latencies[min(int(n * 0.99), n - 1)]
    avg = sum(latencies) / n
    print(f'{name}: n={n} P50={p50:.0f}ms P99={p99:.0f}ms avg={avg:.0f}ms')
    return p50, p99


# 登录拿 token
r = urllib.request.Request(BASE + '/api/v1/auth/login', method='POST',
                           data=json.dumps({'username': 'admin', 'password': 'admin123'}).encode(),
                           headers={'Content-Type': 'application/json'})
with urllib.request.urlopen(r, timeout=8) as resp:
    token = json.loads(resp.read().decode())['access_token']

print('== 基准 ==')
bench('GET /health', lambda: http('GET', BASE + '/health'), n=30, concurrency=10)
bench('POST /auth/login', lambda: http('POST', BASE + '/api/v1/auth/login',
                                       {'username': 'admin', 'password': 'admin123'}), n=20, concurrency=5)
bench('GET /modules', lambda: http('GET', BASE + '/api/v1/modules', token=token), n=30, concurrency=10)
bench('POST /ai-apps', lambda: http('POST', BASE + '/api/v1/ai-apps',
                                    {'name': 'perf', 'llm_config': {'provider': 'p', 'model': 'm'}},
                                    token=token), n=20, concurrency=5)
print('== 结论 ==')
print('目标: P50 < 200ms / P99 < 500ms')

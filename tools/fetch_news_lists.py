"""Докачивает постраничные списки новостей по годам — в них даты публикаций."""
import os, re, sys, time, json, hashlib
import requests
sys.path.insert(0, os.path.dirname(__file__))
from mirror import local_path
s = requests.Session(); s.headers['User-Agent'] = 'Mozilla/5.0 DAPI-mirror/1.0'
for year in range(2009, 2027):
    page = 1
    while page < 40:
        u = f'https://deloros-perm.ru/news/?year={year}' + (f'&PAGEN_1={page}' if page > 1 else '')
        lp = local_path(u)
        if os.path.exists(lp):
            t = open(lp, encoding='utf-8', errors='ignore').read()
        else:
            r = s.get(u, timeout=40); t = r.text
            os.makedirs(os.path.dirname(lp), exist_ok=True)
            open(lp, 'w').write(t)
            json.dump({'url': u, 'status': r.status_code, 'final': r.url, 'ctype': r.headers.get('content-type', '')}, open(lp + '.meta.json', 'w'))
            time.sleep(0.2)
        nxt = f'PAGEN_1={page + 1}' in t
        print(year, page, len(re.findall(r'class="date font_xs"', t)), flush=True)
        if not nxt: break
        page += 1

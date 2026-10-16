"""Полная копия deloros-perm.ru: все страницы из sitemap + найденные внутренние ссылки + ассеты.
Запуск: python3 tools/mirror.py  (вывод в _сырьё/mirror, журнал _сырьё/mirror.log)"""
import os, re, sys, json, time, hashlib, threading, queue
from urllib.parse import urljoin, urlparse, unquote
import requests
from bs4 import BeautifulSoup

BASE = 'https://deloros-perm.ru'
HOST = 'deloros-perm.ru'
ROOT = os.path.join(os.path.dirname(__file__), '..', '_сырьё', 'mirror')
SKIP = re.compile(r'(/bitrix/(admin|tools|services)|/auth/|/personal/|[?&](PAGEN_\d+=\d{3,}|print=|action=|login=|logout=|register=|forgot_password|bxajaxid|clear_cache|backurl|back_url|sort|order)|/search/\?)', re.I)
ASSET_EXT = re.compile(r'\.(css|js|png|jpe?g|gif|webp|svg|ico|woff2?|ttf|eot|pdf|docx?|xlsx?|pptx?|zip|rar|mp4|webm)(\?|$)', re.I)
WORKERS = 12

s = requests.Session()
s.headers['User-Agent'] = 'Mozilla/5.0 (Macintosh) DAPI-mirror/1.0'
lock = threading.Lock()
seen, q = set(), queue.Queue()
stats = {'pages': 0, 'assets': 0, 'err': 0, 'bytes': 0}
log = open(os.path.join(ROOT, '..', 'mirror.log'), 'a')

def local_path(u):
    p = urlparse(u)
    path = unquote(p.path)
    if path.endswith('/') or not os.path.splitext(path)[1]:
        path = path.rstrip('/') + '/index.html'
    if p.query:
        h = hashlib.md5(p.query.encode()).hexdigest()[:8]
        b, e = os.path.splitext(path)
        path = f'{b}__{h}{e}'
    return os.path.join(ROOT, path.lstrip('/'))

def norm(u, base):
    u = urljoin(base, u.strip()).split('#')[0]
    p = urlparse(u)
    if p.scheme not in ('http', 'https'): return None
    host = p.netloc.lower().removeprefix('www.')
    if host != HOST: return None
    return f'https://{HOST}{p.path or "/"}' + (f'?{p.query}' if p.query else '')

def add(u):
    if not u or SKIP.search(u): return
    with lock:
        if u in seen: return
        seen.add(u)
    q.put(u)

ATTR = re.compile(r'\b(href|src|data-src|srcset|data-srcset|data-bg)\s*=\s*["\']([^"\']+)["\']', re.I)

def scan_html(text, base):
    for m in ATTR.finditer(text):
        a, v = m.group(1).lower(), m.group(2)
        if v.startswith('data:') or 'fonts.googleapis' in v: continue
        if 'srcset' in a:
            for part in re.split(r',\s+', v):
                add(norm(part.strip().rsplit(' ', 1)[0] if re.search(r'\s\d+[wx]$', part.strip()) else part.strip(), base))
        else:
            add(norm(v, base))
    for m in re.finditer(r'url\((["\']?)([^)"\']+)\1\)', text):
        if not m.group(2).startswith('data:'): add(norm(m.group(2), base))
    for m in re.finditer(r'["\'](/upload/[^"\'\n]+?)["\']', text):
        add(norm(m.group(1), base))

def handle(u):
    lp = local_path(u)
    if os.path.exists(lp) and os.path.getsize(lp) > 0:
        if os.path.exists(lp + '.meta.json'):
            scan_html(open(lp, encoding='utf-8', errors='ignore').read(), u)
        return
    try:
        r = s.get(u, timeout=40)
    except Exception as e:
        stats['err'] += 1; log.write(f'ERR {u} {e}\n'); return
    meta = {'url': u, 'status': r.status_code, 'final': r.url, 'ctype': r.headers.get('content-type', '')}
    if r.status_code != 200:
        stats['err'] += 1; log.write(f'{r.status_code} {u}\n')
    os.makedirs(os.path.dirname(lp), exist_ok=True)
    with open(lp, 'wb') as f: f.write(r.content)
    stats['bytes'] += len(r.content)
    ct = meta['ctype']
    if 'text/html' in ct:
        stats['pages'] += 1
        with open(lp + '.meta.json', 'w') as f: json.dump(meta, f, ensure_ascii=False)
        scan_html(r.text, r.url)
    elif 'css' in ct:
        stats['assets'] += 1
        for m in re.finditer(r'url\((["\']?)([^)"\']+)\1\)', r.text):
            if not m.group(2).startswith('data:'): add(norm(m.group(2), r.url))
    else:
        stats['assets'] += 1

def worker():
    while True:
        u = q.get()
        try: handle(u)
        finally: q.task_done()
        time.sleep(0.05)

if __name__ == '__main__':
    os.makedirs(ROOT, exist_ok=True)
    sm = os.path.join(ROOT, '..', 'sitemap_urls.txt')
    urls = [BASE + '/']
    for name in ['files', 'iblock-7', 'iblock-13', 'iblock-14', 'iblock-33', 'iblock-37']:
        x = s.get(f'{BASE}/sitemap-{name}.xml', timeout=30).text
        urls += re.findall(r'<loc>([^<]+)</loc>', x)
    open(sm, 'w').write('\n'.join(urls))
    for u in urls: add(norm(u, BASE))
    for _ in range(WORKERS): threading.Thread(target=worker, daemon=True).start()
    t0 = time.time()
    while q.unfinished_tasks:
        time.sleep(15)
        print(f'{int(time.time()-t0)}s seen={len(seen)} left={q.qsize()} {stats} {stats["bytes"]//1048576}MB', flush=True)
        log.flush()
    q.join()
    print('DONE', stats, len(seen), flush=True)

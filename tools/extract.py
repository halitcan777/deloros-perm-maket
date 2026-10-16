"""Достаёт контент из копии сайта (_сырьё/mirror) в data/*.json.
Запуск: python3 tools/extract.py"""
import os, re, json, glob, html
from urllib.parse import urljoin, unquote, urlparse
from bs4 import BeautifulSoup, Comment, NavigableString

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
MIR = os.path.join(PROJ, '_сырьё', 'mirror')
OUT = os.path.join(PROJ, 'data')
BASE = 'https://deloros-perm.ru'
MONTHS = {m: i + 1 for i, m in enumerate(['январ', 'феврал', 'март', 'апрел', 'ма', 'июн', 'июл', 'август', 'сентябр', 'октябр', 'ноябр', 'декабр'])}


def month_num(w):
    w = w.lower()
    for k in sorted(MONTHS, key=len, reverse=True):
        if w.startswith(k):
            return MONTHS[k]


def ru_date(s):
    """«9 октября 2026» → 2026-10-09"""
    m = re.search(r'(\d{1,2})\s+([а-яё]+)\s+(\d{4})', s or '', re.I)
    if not m:
        return None
    mn = month_num(m.group(2))
    return f'{m.group(3)}-{mn:02d}-{int(m.group(1)):02d}' if mn else None


def path_of(url):
    p = unquote(urlparse(url).path)
    return os.path.join(MIR, p.lstrip('/'), 'index.html') if p.endswith('/') else os.path.join(MIR, p.lstrip('/'))


def soup_of(url_or_file):
    f = url_or_file if url_or_file.startswith('/') and os.path.exists(url_or_file) else path_of(url_or_file)
    if not os.path.exists(f):
        return None
    return BeautifulSoup(open(f, encoding='utf-8', errors='ignore').read(), 'html.parser')


def absu(u, base=BASE + '/'):
    if not u:
        return None
    u = u.strip().strip('"\'')
    if u.startswith('data:'):
        return None
    return urljoin(base, u)


def text(el):
    return ' '.join(el.get_text(' ').split()) if el else ''


def h1(s):
    e = s.find('h1')
    return text(e)


def meta_desc(s):
    m = s.find('meta', attrs={'name': 'description'})
    return (m.get('content') or '').strip() if m else ''


KEEP = {'p', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'a', 'strong', 'b', 'em', 'i', 'br', 'table', 'thead', 'tbody', 'tr', 'td', 'th', 'blockquote', 'img', 'iframe'}
DROP_SEL = ['script', 'style', 'svg', 'noscript', 'form', 'section.page-top', 'aside', '.left-menu-md', '.share', '.social-block',
            '.block-buttons', '.subscribe-block', '.bx-pagination', '.module-pagination', '.galery', '.flexslider', '#slider', '#carousel',
            '.breadcrumb', '.back-url', '.mega_fixed_menu', 'header', 'footer', '.sidebar', '.bottom-links-block', '.item_gallery',
            '.ask_a_question_wrapper', '.btntop', '.buttons-block', '.top-wrapper', '.period']


def clean_html(root, base):
    """Оставляет смысловую разметку, выкидывает классы, стили и обёртки шаблона."""
    for c in root.find_all(string=lambda x: isinstance(x, Comment)):
        c.extract()
    for sel in DROP_SEL:
        for e in root.select(sel):
            e.decompose()
    for e in list(root.find_all(True)):
        if e.decomposed if hasattr(e, 'decomposed') else False:
            continue
        name = e.name
        if name in ('h1',):
            e.decompose(); continue
        if name == 'img':
            src = e.get('data-src') or e.get('src')
            src = absu(src, base)
            if not src:
                e.decompose(); continue
            e.attrs = {'src': src, 'alt': e.get('alt', '')}
            continue
        if name == 'a':
            href = e.get('href')
            if not href or href.startswith('javascript') or href == '#':
                e.unwrap(); continue
            e.attrs = {'href': absu(href, base)}
            continue
        if name == 'iframe':
            src = e.get('src') or e.get('data-src')
            e.attrs = {'src': absu(src, base)} if src else {}
            continue
        if name == 'h1':
            e.name = 'h2'
        if name in ('h6',):
            e.name = 'h4'
        if name not in KEEP:
            e.unwrap(); continue
        e.attrs = {k: v for k, v in e.attrs.items() if k in ('colspan', 'rowspan')}
    h = str(root)
    h = re.sub(r'\s+', ' ', h)
    h = re.sub(r'(<br/?>\s*){3,}', '<br/><br/>', h)
    h = re.sub(r'<p>\s*(&nbsp;|\xa0|\s)*\s*</p>', '', h)
    h = re.sub(r'<(strong|b|em|i|li|h\d)>\s*</\1>', '', h)
    h = re.sub(r'<(ul|ol)>\s*</\1>', '', h)
    return h.strip()


def wrap_loose(h):
    """Голый текст между блоками → в абзацы."""
    s = BeautifulSoup(f'<div>{h}</div>', 'html.parser').div
    out, buf = [], []
    block = {'p', 'h2', 'h3', 'h4', 'h5', 'ul', 'ol', 'table', 'blockquote', 'iframe'}

    def flush():
        t = ''.join(str(x) for x in buf).strip()
        t = re.sub(r'^(<br/?>\s*)+|(<br/?>\s*)+$', '', t)
        if BeautifulSoup(t, 'html.parser').get_text().strip() or '<img' in t:
            out.append(f'<p>{t}</p>')
        buf.clear()
    for ch in list(s.children):
        if getattr(ch, 'name', None) in block:
            flush(); out.append(str(ch))
        else:
            buf.append(ch)
    flush()
    return '\n'.join(out)


def content(s, base):
    main = s.select_one('div.main') or s.body
    main = BeautifulSoup(str(main), 'html.parser')
    return wrap_loose(clean_html(main, base))


def gallery(s, base):
    seen, out = set(), []
    for a in s.select('a.fancybox[href], a[data-fancybox-group][href]'):
        u = absu(a['href'], base)
        if u and re.search(r'\.(jpe?g|png|webp|gif)$', u, re.I) and u not in seen:
            seen.add(u); out.append(u)
    return out


def bg_url(el):
    st = (el.get('style') or '') + ' ' + (el.get('data-bg') or '')
    m = re.search(r"url\(['\"]?([^'\")]+)", st) or re.search(r'(/upload/\S+)', st)
    return absu(m.group(1)) if m else None


_META = None


def mirrored(pattern):
    """Все скачанные html-страницы, у которых адрес подходит под pattern."""
    global _META
    if _META is None:
        _META = []
        for mf in glob.glob(os.path.join(MIR, '**', '*.meta.json'), recursive=True):
            try:
                m = json.load(open(mf))
            except Exception:
                continue
            if m.get('status') == 200:
                _META.append((m['url'], mf[:-len('.meta.json')]))
    return [(u, f) for u, f in _META if re.search(pattern, u)]


def sitemap_lastmod():
    import requests
    lm = {}
    for name in ['iblock-7', 'iblock-13', 'iblock-14', 'iblock-33', 'iblock-37', 'files']:
        try:
            x = requests.get(f'{BASE}/sitemap-{name}.xml', timeout=30).text
        except Exception:
            continue
        for loc, mod in re.findall(r'<loc>([^<]+)</loc>\s*<lastmod>([^<]+)</lastmod>', x):
            lm[loc] = mod[:10]
    return lm


# ---------- новости ----------
def news():
    items = {}
    for url, f in mirrored(r'/news/'):
        s = soup_of(f)
        for it in s.select('div.item'):
            a = it.select_one('.title a[href^="/news/"]') or it.select_one('a[href^="/news/"]')
            d = it.select_one('.period .date, .date')
            if not a or not d:
                continue
            u = absu(a['href'])
            if u.count('/') < 6:
                continue
            img = it.select_one('img')
            items.setdefault(u, {})
            items[u].update({k: v for k, v in {
                'url': u, 'title': text(a), 'date': ru_date(text(d)),
                'section': text(it.select_one('.section_name')),
                'thumb': absu(img.get('data-src') or img.get('src')) if img else None}.items() if v})
    # детальные страницы
    for url, f in mirrored(r'/news/[^/]+/[^/?]+/$'):
        s = soup_of(f)
        it = items.setdefault(url, {'url': url})
        it['title'] = it.get('title') or h1(s)
        intro = s.select_one('.introtext')
        it['intro'] = text(intro)
        if intro:
            intro.decompose()
        it['body'] = content(s, url)
        it['gallery'] = gallery(s, url)
        it['desc'] = meta_desc(s)
        crumbs = [text(a) for a in s.select('.breadcrumb a')]
        if not it.get('section') and len(crumbs) > 2:
            it['section'] = crumbs[2]
        it['cat'] = urlparse(url).path.split('/')[2]
    out = sorted(items.values(), key=lambda x: x.get('date') or '0000', reverse=True)
    return out


# ---------- мероприятия ----------
def events(lastmod):
    upcoming = []
    s = soup_of(BASE + '/events/')
    if s:
        for a in s.select('a[href^="/events/"]'):
            u = absu(a['href'])
            if u.rstrip('/') != BASE + '/events' and u not in upcoming and '?' not in u:
                upcoming.append(u)
    out = []
    for url, f in mirrored(r'/events/[^/?]+/$'):
        s = soup_of(f)
        de = s.select_one('.date_events p')
        dtxt = text(de)
        slug = url.rstrip('/').split('/')[-1]
        iso = None
        m = re.search(r'(\d{2})(\d{2})?(\d{2})(\d{2})$', slug)
        dm = re.match(r'(\d{1,2})\s+([а-я]+)', dtxt or '')
        mod = lastmod.get(url, '')
        if dm and month_num(dm.group(2)):
            mn, dd = month_num(dm.group(2)), int(dm.group(1))
            yr = None
            m2 = re.search(r'(\d{2})(\d{2})$', slug)
            if m2 and int(m2.group(1)) == mn:
                yr = 2000 + int(m2.group(2))
            if not yr and mod:
                yr = int(mod[:4])
                if mn > int(mod[5:7]) + 2:
                    yr -= 1
            iso = f'{yr}-{mn:02d}-{dd:02d}' if yr else None
        cont = BeautifulSoup(str(s), 'html.parser')
        for e in cont.select('.date_events'):
            e.decompose()
        body = content(cont, url)
        body = re.sub(r'<p>\s*Подписаться на\s*(<br/>)?\s*рассылку\s*</p>|<p>\s*Будьте в курсе последних новостей отрасли\s*</p>|<p>\s*(Подписаться|Назад к списку)\s*</p>', '', body)
        closed = bool(re.search(r'только для (участников|членов)|закрыт', text(s.select_one('div.main')), re.I))
        g = gallery(s, url)
        out.append({'url': url, 'title': h1(s), 'date_text': dtxt, 'date': iso, 'body': body, 'gallery': g,
                    'upcoming': url in upcoming, 'closed': closed, 'desc': meta_desc(s)})
    out.sort(key=lambda x: x.get('date') or '0000', reverse=True)
    return out, upcoming


# ---------- лица РО ----------
def team():
    people = {}
    order = 0
    lists = sorted(mirrored(r'/organization/team/(\?.*)?$'), key=lambda x: (len(x[0]), x[0]))
    for url, f in lists:
        s = soup_of(f)
        for it in s.select('.item'):
            name_a = it.select_one('a[href*="/organization/team/members/"]')
            title = it.select_one('.title') or name_a
            if not title:
                continue
            nm = text(title)
            if not nm or len(nm) > 60:
                continue
            u = absu(name_a['href']) if name_a else None
            img = it.select_one('img')
            pos = text(it.select_one('.post, .position, .section_name, .props'))
            key = u or nm
            if key in people:
                continue
            order += 1
            people[key] = {'name': nm, 'url': u, 'role': pos, 'order': order,
                           'photo': absu(img.get('data-src') or img.get('src')) if img else None}
    for url, f in mirrored(r'/organization/team/members/[^/?]+/$'):
        s = soup_of(f)
        p = people.setdefault(url, {'name': h1(s), 'url': url, 'order': 999})
        txt = s.select_one('.text_modify, .text')
        p['lead'] = text(txt.find(string=True, recursive=False) and txt) if False else ''
        p['bio'] = content(s, url)
        p['tags'] = [t.lstrip('#') for t in re.findall(r'#[^\s#<]+', text(s.select_one('section.page-top')))]
        img = s.select_one('.detailimage img, .detail img, .image img')
        if img and not p.get('photo_big'):
            p['photo_big'] = absu(img.get('data-src') or img.get('src'), url)
        p['desc'] = meta_desc(s)
    return sorted(people.values(), key=lambda x: x.get('order', 999))


def simple_list(section):
    """Карточки раздела-списка: проекты, комитеты, клубы, советы, партнеры."""
    s = soup_of(f'{BASE}/{section}/')
    out = []
    if not s:
        return out
    for it in s.select('.items .item'):
        a = it.select_one('a[href]')
        if not a:
            continue
        u = absu(a['href'])
        im = it.select_one('[data-bg], [style*="url("]')
        img = it.select_one('img')
        out.append({'url': u, 'title': text(it.select_one('.title')) or text(a),
                    'img': (bg_url(im) if im else None) or (absu(img.get('data-src') or img.get('src')) if img else None)})
    return out


def detail(url):
    if not url or urlparse(url).path in ('', '/'):
        return None
    s = soup_of(url)
    if not s:
        return None
    pt = s.select_one('section.page-top')
    return {'url': url, 'title': h1(s), 'body': content(s, url), 'gallery': gallery(s, url), 'desc': meta_desc(s),
            'tags': [t.lstrip('#') for t in re.findall(r'#[^\s#<]+', text(pt))] if pt else [],
            'crumbs': [text(a) for a in s.select('.breadcrumb a')]}


def menu_tree():
    s = soup_of(BASE + '/organization/team/')
    side = s.select_one('aside.sidebar ul.side-menu') if s else None

    def walk(ul):
        out = []
        for li in ul.find_all('li', recursive=False):
            a = li.find('a')
            node = {'title': text(a), 'url': absu(a['href'])}
            sub = li.select_one('ul.submenu')
            if sub:
                node['children'] = walk(sub)
            out.append(node)
        return out
    return walk(side) if side else []


def main():
    os.makedirs(OUT, exist_ok=True)
    lm = sitemap_lastmod()
    json.dump(lm, open(f'{OUT}/lastmod.json', 'w'), ensure_ascii=False, indent=0)

    n = news()
    json.dump(n, open(f'{OUT}/news.json', 'w'), ensure_ascii=False, indent=1)
    print('news', len(n), 'с датой', sum(1 for x in n if x.get('date')), 'с текстом', sum(1 for x in n if x.get('body')))

    ev, up = events(lm)
    json.dump(ev, open(f'{OUT}/events.json', 'w'), ensure_ascii=False, indent=1)
    print('events', len(ev), 'ближайшие', up, 'с датой', sum(1 for x in ev if x['date']))

    t = team()
    json.dump(t, open(f'{OUT}/team.json', 'w'), ensure_ascii=False, indent=1)
    print('team', len(t), 'с должностью', sum(1 for x in t if x.get('role')))

    sections = {}
    for sec in ['projects', 'commissions', 'clubs', 'boards', 'organization/partners']:
        lst = simple_list(sec)
        for it in lst:
            d = detail(it['url'])
            if d:
                it.update({k: v for k, v in d.items() if k != 'url'})
        sections[sec] = lst
        print(sec, len(lst))
    json.dump(sections, open(f'{OUT}/sections.json', 'w'), ensure_ascii=False, indent=1)

    pages = {}
    for u, f in mirrored(r'deloros-perm\.ru/(organization/(about|perm-region|experts|docs|requisites|how-to-join|kak-vstupit)|contacts|services(/.*)?|include/licenses_detail\.php)/?$'):
        d = detail(u)
        if d:
            pages[u.replace(BASE, '')] = d
    json.dump(pages, open(f'{OUT}/pages.json', 'w'), ensure_ascii=False, indent=1)
    print('pages', len(pages), sorted(pages)[:60])

    json.dump(menu_tree(), open(f'{OUT}/menu.json', 'w'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()

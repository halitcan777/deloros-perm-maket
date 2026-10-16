"""Сборка макета сайта Пермского отделения «Деловой России» из data/*.json → site/.
Запуск:  python3 src/build.py            (ссылки от корня, для локального просмотра через http.server)
         BASE=/deloros-perm python3 src/build.py   (для GitHub Pages)"""
import os, re, json, html, shutil, hashlib, datetime, sys
from urllib.parse import urlparse, unquote
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
DATA = os.path.join(PROJ, 'data')
OUT = os.path.join(PROJ, 'site')
MIR = os.path.join(PROJ, '_сырьё', 'mirror')
IMGCACHE = os.path.join(PROJ, '_сырьё', 'imgcache')
ORIG = 'https://deloros-perm.ru'
P = os.environ.get('BASE', '').rstrip('/')
TODAY = os.environ.get('TODAY', datetime.date.today().isoformat())
VER = datetime.datetime.now().strftime('%m%d%H%M')

PHONE, PHONE_HREF = '+7 (342) 256-35-05', 'tel:+73422563505'
EMAIL = 'welcome@deloros59.ru'
ADDR = '614007, Пермь, ул. Революции, 20, офис 406, БЦ «Бонус»'
ADDR_SHORT = 'Пермь, ул. Революции, 20, офис 406'
HOURS = 'Пн–пт 9:00–18:00'
VK, TG, RUTUBE = 'https://vk.com/deloros59', 'https://t.me/deloros59', 'https://rutube.ru/channel/56421523/'
PAY_CKASSA = 'https://ckassa.ru/payment/#!search_provider/pt_search/111-15131-1/pay'
PAY_SBER = 'https://securepayments.sberbank.ru/shortlink/2KYMlQZt'
BOOK = 'https://book.deloros59.ru/'
CUTOFF_NEWS = os.environ.get('NEWS_FROM', '2025-10-01')   # с какой даты новости получают свою страницу в макете
CUTOFF_EVENTS = os.environ.get('EVENTS_FROM', '2025-09-01')
PRIORITY_PROJECTS = ['139', '156', '155', '162', '158', '154']

J = lambda n: json.load(open(os.path.join(DATA, n), encoding='utf-8'))
esc = lambda s: html.escape(s or '', quote=True)
L = lambda path: P + path

MONTHS_G = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']
MONTHS_N = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']


def dfmt(iso, year=True):
    if not iso:
        return ''
    y, m, d = iso.split('-')
    return f'{int(d)} {MONTHS_G[int(m) - 1]}' + (f' {y}' if year else '')


# ---------------- картинки ----------------
JOBS = {}


def mirror_file(url):
    p = unquote(urlparse(url).path)
    return os.path.join(MIR, p.lstrip('/'))


def img(url, w=800):
    """Регистрирует перевод картинки в WebP нужной ширины, возвращает адрес на сайте."""
    if not url:
        return ''
    if url.startswith('/'):
        url = ORIG + url
    key = hashlib.md5(f'{url}|{w}'.encode()).hexdigest()[:16]
    name = f'{key}.webp'
    JOBS[name] = (url, w)
    return L(f'/img/{name}')


def _convert(args):
    name, url, w = args
    from PIL import Image, ImageOps
    import requests
    dst_cache = os.path.join(IMGCACHE, name)
    dst = os.path.join(OUT, 'img', name)
    if not os.path.exists(dst_cache):
        src = mirror_file(url)
        if not os.path.exists(src) or os.path.getsize(src) == 0:
            try:
                r = requests.get(url, timeout=40, headers={'User-Agent': 'Mozilla/5.0 DAPI-mirror/1.0'})
                if r.status_code != 200 or not r.content:
                    return name, 'http %s' % r.status_code
                os.makedirs(os.path.dirname(src), exist_ok=True)
                open(src, 'wb').write(r.content)
            except Exception as e:
                return name, str(e)[:80]
        try:
            im = Image.open(src)
            im = ImageOps.exif_transpose(im)
            if im.mode not in ('RGB', 'RGBA'):
                im = im.convert('RGBA' if 'transparency' in im.info or im.mode in ('LA', 'P') else 'RGB')
            if im.width > w:
                im = im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)
            im.save(dst_cache, 'WEBP', quality=76, method=4)
        except Exception as e:
            return name, 'img ' + str(e)[:80]
    shutil.copyfile(dst_cache, dst)
    return name, None


def run_images():
    os.makedirs(IMGCACHE, exist_ok=True)
    os.makedirs(os.path.join(OUT, 'img'), exist_ok=True)
    jobs = [(n, u, w) for n, (u, w) in JOBS.items()]
    bad = []
    with ProcessPoolExecutor(max_workers=8) as ex:
        for i, (n, err) in enumerate(ex.map(_convert, jobs, chunksize=16)):
            if err:
                bad.append((n, err))
    print(f'картинки: {len(jobs)}, не вышло {len(bad)}')
    return {n for n, _ in bad}


# ---------------- иконки (Lucide) ----------------
ICONS = {
    'users': '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    'landmark': '<line x1="3" x2="21" y1="22" y2="22"/><line x1="6" x2="6" y1="18" y2="11"/><line x1="10" x2="10" y1="18" y2="11"/><line x1="14" x2="14" y1="18" y2="11"/><line x1="18" x2="18" y1="18" y2="11"/><polygon points="12 2 20 7 4 7"/>',
    'handshake': '<path d="m11 17 2 2a1 1 0 1 0 3-3"/><path d="m14 14 2.5 2.5a1 1 0 1 0 3-3l-3.88-3.88a3 3 0 0 0-4.24 0l-.88.88a1 1 0 1 1-3-3l2.81-2.81a5.79 5.79 0 0 1 7.06-.87l.47.28a2 2 0 0 0 1.42.25L21 4"/><path d="m21 3 1 11h-2"/><path d="M3 3 2 14l6.5 6.5a1 1 0 1 0 3-3"/><path d="M3 4h8"/>',
    'banknote': '<rect width="20" height="12" x="2" y="6" rx="2"/><circle cx="12" cy="12" r="2"/><path d="M6 12h.01M18 12h.01"/>',
    'megaphone': '<path d="m3 11 18-5v12L3 14v-3z"/><path d="M11.6 16.8a3 3 0 1 1-5.8-1.6"/>',
    'globe': '<circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/><path d="M2 12h20"/>',
    'shield': '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/>',
    'calendar': '<rect width="18" height="18" x="3" y="4" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/>',
    'file': '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/>',
    'briefcase': '<path d="M16 20V4a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/><rect width="20" height="14" x="2" y="6" rx="2"/>',
    'graduation': '<path d="M21.42 10.92a1 1 0 0 0-.02-1.84L12.83 5.18a2 2 0 0 0-1.66 0L2.6 9.08a1 1 0 0 0 0 1.83l8.57 3.91a2 2 0 0 0 1.66 0z"/><path d="M22 10v6"/><path d="M6 12.5V16a6 3 0 0 0 12 0v-3.5"/>',
    'plane': '<path d="M17.8 19.2 16 11l3.5-3.5C21 6 21.5 4 21 3c-1-.5-3 0-4.5 1.5L13 8 4.8 6.2c-.5-.1-.9.1-1.1.5l-.3.5c-.2.5-.1 1 .3 1.3L9 12l-2 3H4l-1 1 3 2 2 3 1-1v-3l3-2 3.5 5.3c.3.4.8.5 1.3.3l.5-.2c.4-.3.6-.7.5-1.2z"/>',
    'menu': '<line x1="4" x2="20" y1="6" y2="6"/><line x1="4" x2="20" y1="12" y2="12"/><line x1="4" x2="20" y1="18" y2="18"/>',
    'phone': '<path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/>',
    'factory': '<path d="M2 20a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V8l-7 5V8l-7 5V4a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2Z"/>',
    'cpu': '<rect width="16" height="16" x="4" y="4" rx="2"/><rect width="6" height="6" x="9" y="9" rx="1"/><path d="M15 2v2M15 20v2M2 15h2M2 9h2M20 15h2M20 9h2M9 2v2M9 20v2"/>',
    'building': '<rect width="16" height="20" x="4" y="2" rx="2"/><path d="M9 22v-4h6v4M8 6h.01M16 6h.01M12 6h.01M12 10h.01M12 14h.01M16 10h.01M16 14h.01M8 10h.01M8 14h.01"/>',
    'trending': '<polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/>',
}


def icon(n, size=24):
    return f'<svg viewBox="0 0 24 24" width="{size}" height="{size}" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{ICONS[n]}</svg>'


# ---------------- ссылки внутри старого контента ----------------
GENERATED = set()
LINK_MAP = {  # исправление битых и старых адресов
    '/services/obshchie-uslugi/finansovyy-ekonomicheskiy-audit/': '/services/common-services/finansovyy-ekonomicheskiy-audit/',
    '/organization/kak-vstupit/': '/organization/how-to-join/',
    '/meropriyatiya/': '/events/',
    '/organization/': '/organization/about/',
}


def fix_links(h):
    def rep_a(m):
        u = m.group(1)
        pu = urlparse(u)
        host = pu.netloc.lower().removeprefix('www.')
        if host in ('deloros-perm.ru', 'deloros59.ru'):
            path = unquote(pu.path) or '/'
            path = LINK_MAP.get(path, path)
            if path in GENERATED or (path + '/') in GENERATED:
                return f'href="{esc(L(path))}"'
            return f'href="{esc(ORIG + pu.path)}" target="_blank" rel="noopener"'
        return f'href="{esc(u)}" target="_blank" rel="noopener"'
    h = re.sub(r'href="([^"]+)"', rep_a, h)

    def rep_img(m):
        u = html.unescape(m.group(1))
        return f'src="{img(u, 1200)}" loading="lazy"'
    h = re.sub(r'src="(https?://(?:www\.)?deloros-perm\.ru/upload/[^"]+)"', rep_img, h)
    h = re.sub(r'<iframe src="([^"]+)"', r'<iframe loading="lazy" src="\1" allowfullscreen', h)
    return h


def clean_body(h):
    """Мусор шаблона, теги, пустые ссылки и личные почты из старого контента."""
    h = re.sub(r'<p>\s*(Подписаться на\s*(<br/>)?\s*рассылку|Будьте в курсе последних новостей отрасли|Подписаться|Назад к списку|Поделиться)\s*</p>', '', h)
    h = re.sub(r'<ul>(\s*<li>\s*<a href="[^"]*search_tags[^"]*">[^<]*</a>\s*</li>)+\s*</ul>', '', h)
    h = re.sub(r'<a href="[^"]*">\s*</a>', '', h)
    h = re.sub(r'E-mail\s+[\w.+-]+@[\w-]+\.[\w.]+', '', h)
    h = re.sub(r'<a href="mailto:[^"]+"[^>]*>.*?</a>', '', h)
    h = re.sub(r'<p>\s*(<br/?>\s*)*</p>', '', h)
    return h


def split_team(h):
    """Хвост страницы с карточками участников → список ссылок на участников."""
    m = re.search(r'<p>\s*<a href="[^"]*/organization/team/members/[^"]+">\s*<img', h)
    if not m:
        return h, []
    tail = h[m.start():]
    slugs = list(dict.fromkeys(re.findall(r'/organization/team/members/([^/"]+)/', tail)))
    return h[:m.start()], slugs


def tidy(h):
    """Типографика и опечатки исходника."""
    fixes = {'орбщественной': 'общественной', 'програма': 'программа', 'Финансовый-экономический': 'Финансово-экономический',
             'о изменении': 'об изменении', 'Пермском краю': 'Пермскому краю'}
    for a, b in fixes.items():
        h = h.replace(a, b)
    return h


# ---------------- каркас страницы ----------------
NAV = None


def build_nav(projects):
    pr = {p['id']: p for p in projects}
    return [
        ('Сообщество', '/organization/about/', [
            ('О «Деловой России»', '/organization/about/'),
            ('Отделение в Пермском крае', '/organization/perm-region/'),
            ('Комитеты', '/commissions/'),
            ('Клубы', '/clubs/'),
            ('Советы и рабочие группы', '/boards/'),
            ('Эксперты', '/organization/experts/'),
            ('Партнеры', '/organization/partners/'),
            ('Документы', '/organization/docs/'),
        ]),
        ('Участники', '/organization/team/', None),
        ('Возможности', '/services/', [
            ('Пакеты участия', '/services/package-of-documents/'),
            ('Финансы и инвестиции', '/services/investments-and-loans/'),
            ('PR-пакеты', '/services/pr-package-of-documents/'),
            ('Общие услуги', '/services/common-services/'),
            ('Безопасность бизнеса', '/services/business-security/'),
            ('Управление командировками', '/services/upravlenie-komandirovkami/'),
            ('Обучение', '/services/obrazovatelnye-programmy-korporativnogo-universiteta-sberbanka/'),
        ]),
        ('Проекты', '/projects/', [(pr[i]['title'], f'/projects/{i}/') for i in PRIORITY_PROJECTS if i in pr] + [('Все проекты', '/projects/')]),
        ('Мероприятия', '/events/', None),
        ('Новости', '/news/', None),
        ('Контакты', '/contacts/', None),
    ]


def header(active):
    items = []
    for title, href, sub in NAV:
        on = ' class="on"' if active == href else ''
        dd = ''
        if sub:
            lis = ''.join(f'<li><a href="{L(h)}"{" class=all" if t == "Все проекты" else ""}>{esc(t)}</a></li>' for t, h in sub)
            dd = f'<ul class="dd">{lis}</ul>'
        items.append(f'<li{on}><a href="{L(href)}">{esc(title)}</a>{dd}</li>')
    mob = []
    for title, href, sub in NAV:
        mob.append(f'<a href="{L(href)}">{esc(title)}</a>')
        if sub:
            mob.append('<div class="sub">' + ''.join(f'<a href="{L(h)}">{esc(t)}</a>' for t, h in sub if t != 'Все проекты') + '</div>')
    return f'''<div class="proto">Макет нового сайта · DAPI · содержание взято с deloros-perm.ru на {dfmt(TODAY)}</div>
<div class="top"><div class="wrap">
  <span>{ADDR_SHORT}</span><span>{HOURS}</span><a href="mailto:{EMAIL}">{EMAIL}</a>
  <div class="soc"><a href="#pay" data-pay>Оплатить взнос</a><a href="{TG}" target="_blank" rel="noopener">Telegram</a><a href="{VK}" target="_blank" rel="noopener">ВКонтакте</a></div>
</div></div>
<header class="hdr"><div class="wrap">
  <a class="logo" href="{L('/')}" aria-label="Деловая Россия, Пермский край, на главную"><img src="{L('/assets/logo.png')}" alt="Деловая Россия. Пермский край" width="163" height="48"></a>
  <nav aria-label="Основное меню"><ul class="nav">{''.join(items)}</ul></nav>
  <div class="act"><a class="phone" href="{PHONE_HREF}">{PHONE}</a><a class="btn btn-primary btn-sm" href="{L('/organization/how-to-join/')}#zayavka">Вступить</a>
  <button class="burger" aria-label="Меню" aria-expanded="false" data-burger>{icon('menu')}</button></div>
</div></header>
<div class="mnav" data-mnav>{''.join(mob)}<a class="btn btn-primary" href="{L('/organization/how-to-join/')}#zayavka">Обсудить вступление</a><a href="{PHONE_HREF}">{PHONE}</a><a href="#pay" data-pay>Оплатить взнос</a></div>'''


def footer():
    col = lambda t, links: f'<div><div class="h">{t}</div><ul>' + ''.join(f'<li><a href="{L(h) if h.startswith("/") else h}">{esc(x)}</a></li>' for x, h in links) + '</ul></div>'
    return f'''<footer class="ftr"><div class="wrap">
<div class="cols">
  <div><a class="logo" href="{L('/')}"><img src="{L('/assets/logo.png')}" alt="Деловая Россия. Пермский край" width="163" height="48"></a>
    <div class="ct"><a href="{PHONE_HREF}"><b>{PHONE}</b></a><a href="mailto:{EMAIL}">{EMAIL}</a><span>{ADDR}</span><span>{HOURS}</span></div></div>
  {col('Об отделении', [('О «Деловой России»', '/organization/about/'), ('Отделение в Пермском крае', '/organization/perm-region/'), ('Участники', '/organization/team/'), ('Комитеты', '/commissions/'), ('Клубы', '/clubs/'), ('Советы и рабочие группы', '/boards/'), ('Партнеры', '/organization/partners/')])}
  {col('Участие', [('Вступить', '/organization/how-to-join/'), ('Пакеты участия', '/services/package-of-documents/'), ('Возможности', '/services/'), ('Проекты', '/projects/'), ('Мероприятия', '/events/')])}
  {col('Информация', [('Новости', '/news/'), ('Документы', '/organization/docs/'), ('Реквизиты', '/organization/requisites/'), ('Контакты', '/contacts/'), ('Политика конфиденциальности', '/privacy/')])}
  {col('Мы в сети', [('Telegram', TG), ('ВКонтакте', VK), ('Rutube', RUTUBE), ('Книга «Предприниматели и меценаты Прикамья»', BOOK)])}
</div>
<div class="bottom"><span>© 2004–{TODAY[:4]} Пермское краевое региональное отделение «Деловая Россия»</span><span>ИНН 5902990323 · ОГРН 1135900001742</span><a href="#pay" data-pay>Оплатить членский взнос</a></div>
</div></footer>
<div class="modal" id="pay" role="dialog" aria-modal="true" aria-labelledby="pay-h"><div class="box">
  <button class="x" data-close aria-label="Закрыть">×</button>
  <h3 id="pay-h">Оплата членского взноса</h3>
  <p class="note" style="margin-top:8px">Взнос за год по вашему пакету участия. Пакет «Базовый» 100 000 ₽, «Премиум» 190 000 ₽. Если не уверены в сумме, позвоните в дирекцию {PHONE}.</p>
  <div class="pay-opt">
    <a href="{PAY_SBER}" target="_blank" rel="noopener"><span><b>Картой или через СБП</b><small>Платежная страница Сбербанка, сумму укажете на ней</small></span><span>Перейти</span></a>
    <a href="{PAY_CKASSA}" target="_blank" rel="noopener"><span><b>Через «Центральную кассу»</b><small>Терминалы и онлайн-оплата, поставщик «Деловая Россия»</small></span><span>Перейти</span></a>
  </div>
  <p class="note">Для оплаты по счету от организации напишите на <a href="mailto:{EMAIL}">{EMAIL}</a>, реквизиты на странице <a href="{L('/organization/requisites/')}">Реквизиты</a>.</p>
</div></div>'''


def layout(path, title, body, desc='', active=None, og_img=None):
    full = f'{title} · Деловая Россия, Пермский край' if path != '/' else 'Деловая Россия, Пермский край · сообщество предпринимателей Прикамья'
    d = esc((desc or '')[:200])
    doc = f'''<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(full)}</title><meta name="description" content="{d}"><meta name="robots" content="noindex,nofollow">
<link rel="canonical" href="{ORIG}{esc(path)}"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{d}">{f'<meta property="og:image" content="{og_img}">' if og_img else ''}
<link rel="icon" href="{L('/assets/favicon.png')}"><link rel="preload" href="{L('/assets/fonts/onest-cyrillic-400.woff2')}" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="{L('/assets/site.css')}?v={VER}"></head><body>
{header(active)}
<main id="main">{body}</main>
{footer()}
<script src="{L('/assets/app.js')}?v={VER}" defer></script></body></html>'''
    f = os.path.join(OUT, path.lstrip('/'), 'index.html') if path.endswith('/') else os.path.join(OUT, path.lstrip('/'))
    os.makedirs(os.path.dirname(f), exist_ok=True)
    open(f, 'w', encoding='utf-8').write(doc)


def crumbs(*pairs):
    out = [f'<a href="{L("/")}">Главная</a>']
    for t, h in pairs:
        out.append(f'<span><a href="{L(h)}">{esc(t)}</a></span>' if h else f'<span>{esc(t)}</span>')
    return f'<div class="wrap crumbs">{"".join(out)}</div>'


def page_head(title, sub='', meta=''):
    return f'<div class="wrap page-h"><h1>{esc(title)}</h1>{f"<p class=sub>{sub}</p>" if sub else ""}{f"<div class=meta>{meta}</div>" if meta else ""}</div>'


def side(items, cur):
    return '<nav class="side" aria-label="Раздел">' + ''.join(
        f'<div class="h">{esc(t)}</div>' if h is None else f'<a href="{L(h)}"{" class=on" if h == cur else ""}>{esc(t)}</a>' for t, h in items) + '</nav>'


SIDE_COMMUNITY = [('Сообщество', None), ('О «Деловой России»', '/organization/about/'), ('Отделение в Пермском крае', '/organization/perm-region/'),
                  ('Участники', '/organization/team/'), ('Комитеты', '/commissions/'), ('Клубы', '/clubs/'), ('Советы и рабочие группы', '/boards/'),
                  ('Эксперты', '/organization/experts/'), ('Партнеры', '/organization/partners/'), ('Документы', '/organization/docs/'), ('Реквизиты', '/organization/requisites/')]


def cta_join(title='Хотите участвовать?', text='Оставьте короткую заявку, исполнительный директор свяжется с вами и расскажет, как устроено участие.', interest=''):
    q = f'?interest={esc(interest)}' if interest else ''
    return f'<div class="aside-cta"><div><b>{esc(title)}</b><span>{esc(text)}</span></div><a class="btn btn-primary" href="{L("/organization/how-to-join/")}{q}#zayavka">Обсудить участие</a></div>'


INTERESTS = ['Вступление в «Деловую Россию»', 'Участие в проекте', 'Участие в мероприятии', 'Работа в комитете', 'Партнерство', 'Сотрудничество с участником', 'Другое']


def lead_form(title='Обсудить вступление', text='Короткая заявка ни к чему не обязывает. Исполнительный директор позвонит в течение двух рабочих дней, расскажет об условиях и пригласит на знакомство.', interest=''):
    opts = ''.join(f'<option{" selected" if i == interest else ""}>{esc(i)}</option>' for i in INTERESTS)
    return f'''<section class="sec" id="zayavka"><div class="wrap"><div class="lead-box" data-lead>
<div><h2>{esc(title)}</h2><p style="margin-top:16px">{esc(text)}</p>
<div class="contact">Удобнее позвонить? <a href="{PHONE_HREF}">{PHONE}</a><br>{HOURS}</div></div>
<div>
<form class="form" data-form novalidate>
  <label>Имя и фамилия<input name="name" required autocomplete="name"></label>
  <label>Телефон<input name="phone" type="tel" required autocomplete="tel" placeholder="+7"></label>
  <label>Компания<input name="company" required autocomplete="organization"></label>
  <label>Должность<input name="position" autocomplete="organization-title"></label>
  <label class="full">Что вас интересует<select name="interest">{opts}</select></label>
  <label class="full agree"><input type="checkbox" name="agree" required> <span>Согласен на обработку персональных данных по <a href="{L('/privacy/')}">политике конфиденциальности</a>. Данные хранятся в России.</span></label>
  <input type="hidden" name="source" value="">
  <button class="btn btn-white" type="submit">Отправить заявку</button>
</form>
<div class="done" role="status"><h3>Заявка принята</h3><p>Что будет дальше</p><ol>
  <li>В течение двух рабочих дней позвонит исполнительный директор отделения.</li>
  <li>Договоримся о встрече в офисе на Революции, 20 или на ближайшем открытом мероприятии.</li>
  <li>Если решите вступать, пришлем пакет документов и расскажем о сроках.</li></ol></div>
</div></div></div></section>'''


# ---------------- данные ----------------
def load():
    news = [n for n in J('news.json') if n.get('title') and n.get('url', '').count('/') >= 6]
    for n in news:
        n['cat'] = n.get('cat') or urlparse(n['url']).path.split('/')[2]
    events = J('events.json')
    team = [p for p in J('team.json') if p.get('url') and '/members/' in p['url']]
    sections = J('sections.json')
    pages = J('pages.json')
    projects = []
    for p in sections['projects']:
        pid = p['url'].rstrip('/').split('/')[-1]
        if not pid.isdigit():
            continue
        p['id'] = pid
        projects.append(p)
    return news, events, team, sections, pages, projects


def project_status(p):
    years = [int(y) for y in re.findall(r'\b(20[12]\d)\b', p.get('body', '') + ' ' + p['title'])]
    if int(p['id']) >= 149:
        return 'active'
    if years and max(years) >= 2025:
        return 'active'
    return 'archive'


def path_of(url):
    return urlparse(url).path


def is_own(url):
    return urlparse(url).netloc.lower().removeprefix('www.') in ('deloros-perm.ru', 'deloros59.ru', '')


# ---------------- страницы ----------------
def card_news(n, local=True):
    href = L(path_of(n['url'])) if local else n['url']
    ext = '' if local else ' target="_blank" rel="noopener"'
    ph = f'<div class="ph"><img src="{img(n.get("thumb") or (n.get("gallery") or [None])[0], 640)}" alt="" loading="lazy"></div>' if (n.get('thumb') or n.get('gallery')) else ''
    return f'<a class="card" href="{esc(href)}"{ext}>{ph}<div class="in"><div class="date">{dfmt(n.get("date"))}</div><h3>{esc(n["title"])}</h3></div></a>'


def ev_card(e):
    tag = '<span class="tag closed">Для участников</span>' if e.get('closed') else '<span class="tag ok">Открытое</span>'
    return f'<a class="ev" href="{L(path_of(e["url"]))}"><span class="d">{esc(e.get("date_text") or dfmt(e.get("date"), False))}</span><span class="t">{esc(e["title"])}</span>{tag}</a>'


def build_home(news, events, team, projects, stats):
    up = [e for e in events if e['upcoming']]
    up.sort(key=lambda e: e.get('date') or '9999')
    first_open = next((e for e in up if not e['closed']), up[0] if up else None)
    hero_ev = ''
    if first_open:
        g = first_open.get('gallery') or []
        ph = f'<img src="{img(g[0], 960)}" alt="">' if g else ''
        hero_ev = f'''<aside class="hero-ev">{ph}<div class="in"><div class="lbl">Ближайшее событие</div><h3>{esc(first_open['title'])}</h3>
<div class="meta">{esc(first_open.get('date_text') or '')} · {'только для участников' if first_open['closed'] else 'открытое мероприятие'}</div>
{f'<a class="btn btn-line btn-sm" href="{L("/organization/how-to-join/")}">Как попасть на закрытые встречи</a>' if first_open['closed'] else f'<a class="btn btn-primary btn-sm" href="{L(path_of(first_open["url"]))}#zayavka">Зарегистрироваться</a>'}</div></aside>'''
    leaders = [p for p in team if p.get('order', 999) <= 13][:8]
    pr = {p['id']: p for p in projects}
    prio = [pr[i] for i in PRIORITY_PROJECTS if i in pr]
    up_html = ''.join(ev_card(e) for e in up[:4]) if up else ''
    if not up:
        up_html = f'<div class="empty"><div><b>Скоро появится новое мероприятие</b><span>Анонсы выходят за 2–3 недели. Подпишитесь на Telegram-канал, чтобы не пропустить.</span></div><a class="btn btn-line" href="{TG}">Telegram-канал</a></div>'
    else:
        up_html = f'<div class="ev-list">{up_html}</div>'
    benefits = [
        ('handshake', 'Деловые контакты', 'Собственники и первые лица компаний Прикамья в закрытых чатах, клубах и на встречах отделения.'),
        ('landmark', 'Диалог с властью', 'Участие в советах и рабочих группах при краевых министерствах, прокуратуре, мэрии и уполномоченном по защите прав предпринимателей.'),
        ('banknote', 'Финансирование', 'Консультации по льготным кредитам, грантам, субсидиям и структурированию инвестпроектов.'),
        ('globe', 'Новые рынки', 'Бизнес-миссии, клуб экспортеров и выход на партнеров через федеральную сеть «Деловой России».'),
        ('megaphone', 'Продвижение', 'Публикации о компании и интервью на ресурсах отделения, рекомендация участникам и партнерам.'),
        ('shield', 'Защита бизнеса', 'Помощь при проверках, разбор налоговых рисков, защита от недобросовестных действий.'),
    ]
    who = [('Собственникам и директорам', 'среднего и крупного бизнеса, которым нужны связи, поддержка и голос в регионе'),
           ('Промышленникам и строителям', 'комитеты по промышленности и строительству, «Альянс проверенных подрядчиков»'),
           ('Экспортерам', 'клуб экспортеров, бизнес-миссии, контакты в других странах через сеть организации'),
           ('Технологическим компаниям', 'клуб инноваторов, трансфер технологий, центр компетенций по НМА'),
           ('Инвесторам', 'клуб частного инвестора, гид инвестора, реестр проектов и идей'),
           ('Экспертам и консультантам', 'экспертные советы, выступления на бизнес-завтраках, участие в комитетах')]
    news_html = ''.join(card_news(n) for n in news[:8])
    facts = ''.join(f'<div class="fact"><b>{b}</b><span>{s}</span><small>{sm}</small></div>' for b, s, sm in stats['hero'])
    body = f'''
<section class="hero"><div class="wrap">
 <div><h1>Сообщество предпринимателей Прикамья с 2004 года</h1>
 <p class="lead">Пермское отделение «Деловой России» объединяет собственников и руководителей компаний края. Помогаем находить партнеров, получать финансирование, выходить на новые рынки и доносить позицию бизнеса до власти.</p>
 <div class="ctas"><a class="btn btn-primary" href="{L('/organization/how-to-join/')}#zayavka">Обсудить вступление</a><a class="btn btn-line" href="{L('/organization/team/')}">Посмотреть участников</a></div>
 <div class="facts">{facts}</div></div>
 {hero_ev}
</div></section>

<section class="sec tight"><div class="wrap">
 <div class="sec-h"><h2>Ближайшие мероприятия</h2><a class="link-more" href="{L('/events/')}">Все мероприятия</a></div>
 {up_html}
</div></section>

<section class="sec soft"><div class="wrap">
 <div class="sec-h"><h2>Что получает участник</h2><p>Возможности пакетов «Базовый» и «Премиум». Полный состав и сравнение на странице вступления.</p></div>
 <div class="grid g3">{''.join(f'<div class="benefit"><div class="ic">{icon(i)}</div><h3>{t}</h3><p>{d}</p></div>' for i, t, d in benefits)}</div>
 <div style="margin-top:32px"><a class="btn btn-primary" href="{L('/organization/how-to-join/')}">Условия участия</a></div>
</div></section>

<section class="sec"><div class="wrap">
 <div class="sec-h"><h2>Кому подходит сообщество</h2></div>
 <ul class="who">{''.join(f'<li><b>{t}</b><span>{d}</span></li>' for t, d in who)}</ul>
</div></section>

<section class="sec soft"><div class="wrap">
 <div class="sec-h"><h2>Отделение в цифрах</h2><p>Посчитано по материалам сайта, период указан у каждой цифры. Перед запуском дирекция сверяет данные.</p></div>
 <div class="grid g4">{''.join(f'<div class="benefit"><b style="font-size:36px;font-weight:600;line-height:1">{b}</b><h3>{t}</h3><p>{d}</p></div>' for b, t, d in stats['scale'])}</div>
</div></section>

<section class="sec"><div class="wrap">
 <div class="sec-h"><h2>Проекты отделения</h2><a class="link-more" href="{L('/projects/')}">Все проекты</a></div>
 <div class="grid g3">{''.join(card_project(p) for p in prio)}</div>
</div></section>

<section class="sec soft"><div class="wrap">
 <div class="sec-h"><h2>Новости</h2><a class="link-more" href="{L('/news/')}">Все новости</a></div>
 <div class="grid g4">{news_html}</div>
</div></section>

<section class="sec"><div class="wrap">
 <div class="sec-h"><h2>Руководство отделения</h2><a class="link-more" href="{L('/organization/team/')}">Все участники</a></div>
 <div class="people">{''.join(person_card(p) for p in leaders)}</div>
</div></section>

<section class="sec soft"><div class="wrap">
 <div class="sec-h"><h2>Как вступить</h2><a class="link-more" href="{L('/organization/how-to-join/')}">Подробно о вступлении</a></div>
 {steps_html()}
</div></section>
{lead_form()}'''
    layout('/', 'Главная', body, desc='Пермское отделение «Деловой России» с 2004 года объединяет собственников и руководителей компаний Прикамья. Вступление, мероприятия, проекты, участники.', active='/')


def steps_html():
    st = [('Короткая заявка', 'Имя, компания и телефон на сайте или по звонку'),
          ('Разговор', 'Исполнительный директор расскажет об условиях и ответит на вопросы'),
          ('Знакомство', 'Встреча в офисе или на открытом мероприятии отделения'),
          ('Документы', 'Заявление, анкета, согласие и оплата вступительного взноса'),
          ('Решение совета', 'Региональный совет утверждает прием, вы получаете сертификат и значок')]
    return '<ol class="steps">' + ''.join(f'<li><b>{a}</b><span>{b}</span></li>' for a, b in st) + '</ol>'


def card_project(p):
    st = p.get('status') == 'active'
    tag = '<span class="tag ok">Действует</span>' if st else '<span class="tag arch">Архив</span>'
    ph = f'<div class="ph"><img src="{img(p.get("img"), 640)}" alt="" loading="lazy"></div>' if p.get('img') else ''
    lead = p.get('lead', '')
    return f'<a class="card" href="{L("/projects/" + p["id"] + "/")}">{ph}<div class="in"><h3>{esc(p["title"].strip())}</h3>{f"<p>{esc(lead)}</p>" if lead else ""}<div class="foot">{tag}</div></div></a>'


def person_card(p, data=False):
    attrs = ''
    if data:
        grp = 'lead' if p.get('order', 999) <= 7 else ('council' if 'совет' in (p.get('role') or '').lower() else 'member')
        attrs = f' data-grp="{grp}" data-q="{esc((p["name"] + " " + (p.get("role") or "") + " " + " ".join(p.get("tags") or [])).lower())}"'
    ph = p.get('photo') or p.get('photo_big')
    pic = f'<img src="{img(ph, 480)}" alt="{esc(p["name"])}" loading="lazy">' if ph else ''
    return f'<a class="person" href="{L(path_of(p["url"]))}"{attrs}><div class="ph">{pic}</div><div class="in"><b>{esc(p["name"])}</b><span>{esc(p.get("role") or "Член «Деловой России»")}</span></div></a>'


def strip_tags(h):
    return ' '.join(re.sub(r'<[^>]+>', ' ', h or '').split())


def first_sentence(h, n=180):
    t = strip_tags(h)
    t = re.sub(r'^(Описание)\s+', '', t)
    if len(t) <= n:
        return t
    cut = t[:n]
    i = max(cut.rfind('. '), cut.rfind('! '))
    return (cut[:i + 1] if i > 60 else cut.rsplit(' ', 1)[0] + '…')


def gallery_html(urls, limit=16):
    if not urls:
        return ''
    return '<div class="gallery">' + ''.join(f'<a href="{img(u, 1600)}" data-lb><img src="{img(u, 400)}" alt="" loading="lazy"></a>' for u in urls[:limit]) + '</div>'


def build_news(news):
    cats = {'regional-office': 'Новости отделения', 'partners': 'Новости партнеров', 'events': 'Анонсы и итоги'}
    local = [n for n in news if (n.get('date') or '') >= CUTOFF_NEWS]
    loc_set = {n['url'] for n in local}
    for n in local:
        GENERATED.add(path_of(n['url']))
    per = 24

    def list_pages(items, base, title, cur):
        pages = max(1, (len(items) + per - 1) // per)
        tabs = '<div class="filters">' + f'<a class="chip{" on" if cur == "all" else ""}" href="{L("/news/")}" style="display:inline-flex;align-items:center">Все</a>' + ''.join(
            f'<a class="chip{" on" if cur == k else ""}" href="{L(f"/news/{k}/")}" style="display:inline-flex;align-items:center">{v}</a>' for k, v in cats.items()) + '</div>'
        for i in range(pages):
            chunk = items[i * per:(i + 1) * per]
            path = base if i == 0 else f'{base}page-{i + 1}/'
            pager = ''
            if pages > 1:
                nums = sorted({1, 2, pages - 1, pages, i, i + 1, i + 2} & set(range(1, pages + 1)))
                parts, prev = [], 0
                for k in nums:
                    if k - prev > 1:
                        parts.append('<span class="gap">…</span>')
                    href = L(base if k == 1 else f'{base}page-{k}/')
                    parts.append(f'<span class="on">{k}</span>' if k == i + 1 else f'<a href="{href}">{k}</a>')
                    prev = k
                pager = f'<nav class="pager" aria-label="Страницы">{"".join(parts)}</nav>'
            cards = ''.join(card_news(n, n['url'] in loc_set) for n in chunk)
            body = crumbs(('Новости', '/news/' if cur != 'all' else None), *((title, None),) if cur != 'all' else ()) + page_head(title) + f'<div class="wrap" style="padding-bottom:80px">{tabs}<div class="grid g4">{cards}</div>{pager}</div>'
            GENERATED.add(path)
            layout(path, title + (f', страница {i + 1}' if i else ''), body, desc='Новости Пермского отделения «Деловой России» и партнеров.', active='/news/')

    list_pages(news, '/news/', 'Новости', 'all')
    for k, v in cats.items():
        list_pages([n for n in news if n.get('cat') == k], f'/news/{k}/', v, k)
    return local


def render_news_details(local, news):
    cats = {'regional-office': 'Новости отделения', 'partners': 'Новости партнеров', 'events': 'Анонсы и итоги'}
    for n in local:
        g = n.get('gallery') or []
        cover = n.get('thumb') or (g[0] if g else None)
        rest = [u for u in g if u != cover]
        intro = f'<p class="intro">{esc(n["intro"])}</p>' if n.get('intro') else ''
        same = [x for x in news if x.get('cat') == n.get('cat') and x['url'] != n['url'] and (x.get('date') or '') >= CUTOFF_NEWS][:4]
        body = crumbs(('Новости', '/news/'), *(((cats[n['cat']], f'/news/{n["cat"]}/'),) if n.get('cat') in cats else ()), (n['title'][:60] + ('…' if len(n['title']) > 60 else ''), None)) + \
            page_head(n['title'], meta=f'<span>{dfmt(n.get("date"))}</span><span class="tag">{esc(cats.get(n.get("cat"), ""))}</span>') + \
            f'''<div class="wrap" style="padding-bottom:64px">{f'<div class="cover"><img src="{img(cover, 1200)}" alt=""></div>' if cover else ''}
<article class="prose">{intro}{tidy(fix_links(clean_body(n.get('body') or '')))}</article>{gallery_html(rest)}{cta_join()}</div>
<section class="sec soft"><div class="wrap"><div class="sec-h"><h2>Еще новости</h2><a class="link-more" href="{L('/news/')}">Все новости</a></div><div class="grid g4">{''.join(card_news(x) for x in same)}</div></div></section>'''
        layout(path_of(n['url']), n['title'], body, desc=n.get('desc') or n.get('intro') or first_sentence(n.get('body', '')), active='/news/', og_img=None)


def build_events(events):
    local = [e for e in events if e['upcoming'] or (e.get('date') or '') >= CUTOFF_EVENTS]
    for e in local:
        GENERATED.add(path_of(e['url']))
    GENERATED.add('/events/')
    return local


def render_events(local, events):
    up = sorted([e for e in events if e['upcoming']], key=lambda e: e.get('date') or '9999')
    past = [e for e in local if not e['upcoming'] and (e.get('date') or '') <= TODAY]
    groups = {}
    for e in past:
        k = e['date'][:7]
        groups.setdefault(k, []).append(e)
    up_html = f'<div class="ev-list">{"".join(ev_card(e) for e in up)}</div>' if up else f'<div class="empty"><div><b>Скоро появится новое мероприятие</b><span>Анонсы выходят за 2–3 недели. Подпишитесь на Telegram-канал отделения.</span></div><a class="btn btn-line" href="{TG}">Telegram-канал</a></div>'
    arch = ''
    for k in sorted(groups, reverse=True):
        y, m = k.split('-')
        rows = ''.join(f'<a class="doc" href="{L(path_of(e["url"]))}"><div style="min-width:110px;color:var(--muted)">{dfmt(e["date"], False)}</div><div style="flex:1">{esc(e["title"])}</div>{"<span class=\"tag closed\">Для участников</span>" if e["closed"] else ""}</a>' for e in sorted(groups[k], key=lambda x: x['date'], reverse=True))
        arch += f'<h3 style="margin:40px 0 16px">{MONTHS_N[int(m) - 1]} {y}</h3><div class="docs">{rows}</div>'
    body = crumbs(('Мероприятия', None)) + page_head('Мероприятия', 'Открытые встречи можно посетить до вступления, чтобы познакомиться с сообществом. Закрытые проходят только для участников отделения.') + f'''
<div class="wrap" style="padding-bottom:80px">
<div class="sec-h"><h2>Ближайшие</h2><a class="link-more" href="#zayavka">Предложить мероприятие</a></div>{up_html}
<div class="sec-h" style="margin-top:64px"><h2>Прошедшие</h2><p>С итогами и фотографиями. Архив за прошлые годы на <a href="{ORIG}/events/?archive=y" target="_blank" rel="noopener">текущем сайте</a>, при переезде переносится полностью.</p></div>
{arch}</div>{lead_form('Предложить мероприятие или выступить спикером', 'Расскажите об идее. Дирекция поможет с площадкой, участниками и анонсом.', 'Участие в мероприятии')}'''
    layout('/events/', 'Мероприятия', body, desc='Ближайшие и прошедшие мероприятия Пермского отделения «Деловой России».', active='/events/')
    for e in local:
        g = e.get('gallery') or []
        is_past = (e.get('date') or '9999') < TODAY and not e['upcoming']
        status = 'Прошло' if is_past else ('Только для участников' if e['closed'] else 'Открытое мероприятие')
        if is_past:
            act = cta_join('Хотите на следующую встречу?', 'Открытые мероприятия можно посетить до вступления. Оставьте контакты, пришлем приглашение.', 'Участие в мероприятии')
        elif e['closed']:
            act = cta_join('Мероприятие для участников сообщества', 'Чтобы попасть на такие встречи, обсудите вступление с дирекцией.', 'Вступление в «Деловую Россию»')
        else:
            act = cta_join('Регистрация на мероприятие', 'Оставьте контакты, дирекция подтвердит участие и пришлет детали.', 'Участие в мероприятии')
        body = crumbs(('Мероприятия', '/events/'), (e['title'][:60], None)) + page_head(e['title'], meta=f'<span>{esc(e.get("date_text") or "")}{(" " + e["date"][:4]) if e.get("date") else ""}</span><span class="tag{" closed" if e["closed"] and not is_past else " arch" if is_past else " ok"}">{status}</span>') + \
            f'<div class="wrap" style="padding-bottom:80px">{f"<div class=cover><img src={chr(34)}{img(g[0], 1200)}{chr(34)} alt=></div>" if g else ""}<article class="prose">{tidy(fix_links(clean_body(e.get("body") or "")))}</article>{gallery_html(g[1:])}{act}</div>'
        layout(path_of(e['url']), e['title'], body, desc=e.get('desc') or first_sentence(e.get('body', '')), active='/events/')


def build_team(team):
    GENERATED.add('/organization/team/')
    for p in team:
        GENERATED.add(path_of(p['url']))


def render_team(team):
    chips = [('all', 'Все'), ('lead', 'Руководство'), ('council', 'Региональный совет'), ('member', 'Члены отделения')]
    body = crumbs(('Сообщество', '/organization/about/'), ('Участники', None)) + page_head('Участники', 'Руководство, региональный совет и члены отделения. Найдите нужную компетенцию и предложите сотрудничество через дирекцию.') + f'''
<div class="wrap" style="padding-bottom:80px">
<div class="filters">{''.join(f'<button class="chip{" on" if k == "all" else ""}" data-f="{k}">{t}</button>' for k, t in chips)}<input class="search-in" type="search" placeholder="Поиск по имени, должности, проекту" data-q aria-label="Поиск участников"></div>
<div class="people" data-people>{''.join(person_card(p, True) for p in team)}</div>
<p class="note" style="margin-top:32px">Карточки показывают только тех, кто согласился на публикацию. Данные подтверждаются раз в год.</p>
</div>{lead_form('Предложить сотрудничество участнику', 'Напишите, с кем и о чем хотите поговорить. Дирекция передаст запрос и договорится о знакомстве. Личные почты участников на сайте не публикуем.', 'Сотрудничество с участником')}'''
    layout('/organization/team/', 'Участники', body, desc='Руководство, региональный совет и члены Пермского отделения «Деловой России».', active='/organization/team/')
    for p in team:
        ph = p.get('photo_big') or p.get('photo')
        tags = ''.join(f'<span class="tag">#{esc(t)}</span> ' for t in (p.get('tags') or []) if not t.lower().startswith(p['name'].split()[0].lower()[:4]))
        bio = tidy(fix_links(clean_body(p.get('bio') or '')))
        bio = re.sub(r'<a href="mailto:[^"]+"[^>]*>.*?</a>|[\w.+-]+@[\w-]+\.[\w.]+', '', bio)
        body = crumbs(('Участники', '/organization/team/'), (p['name'], None)) + f'''<div class="wrap" style="padding:24px var(--gut) 80px"><div class="prof">
<div class="ph">{f'<img src="{img(ph, 640)}" alt="{esc(p["name"])}">' if ph else ''}</div>
<div><h1>{esc(p['name'])}</h1><div class="role">{esc(p.get('role') or 'Член «Деловой России»')}</div><div style="margin-bottom:24px">{tags}</div>
<a class="btn btn-primary" href="{L('/organization/team/')}?interest=Сотрудничество с участником#zayavka">Предложить сотрудничество</a>
<article class="prose" style="margin-top:40px">{bio}</article></div></div></div>'''
        layout(path_of(p['url']), p['name'], body, desc=p.get('desc') or f'{p["name"]}, {p.get("role", "")}', active='/organization/team/')


def build_projects(projects):
    GENERATED.add('/projects/')
    for p in projects:
        p['status'] = project_status(p)
        p['lead'] = first_sentence(p.get('body', ''), 140)
        GENERATED.add(f'/projects/{p["id"]}/')


TEAM_BY_SLUG = {}


def render_projects(projects):
    act = [p for p in projects if p['status'] == 'active']
    arc = [p for p in projects if p['status'] != 'active']
    body = crumbs(('Проекты', None)) + page_head('Проекты', 'Инициативы участников отделения. К действующим проектам можно присоединиться, архивные остаются для истории.') + f'''
<div class="wrap" style="padding-bottom:80px">
<div class="sec-h"><h2>Действующие</h2><span class="tag ok">{len(act)}</span></div><div class="grid g3">{''.join(card_project(p) for p in act)}</div>
<div class="sec-h" style="margin-top:64px"><h2>Архив</h2><span class="tag arch">{len(arc)}</span></div><div class="grid g4">{''.join(card_project(p) for p in arc)}</div>
</div>{lead_form('Предложить свой проект', 'Расскажите о проекте или инвестиционной идее. Подскажем комитет, команду и формат поддержки.', 'Участие в проекте')}'''
    layout('/projects/', 'Проекты', body, desc='Действующие и архивные проекты Пермского отделения «Деловой России».', active='/projects/')
    for p in projects:
        st = p['status'] == 'active'
        kv = f'''<dl class="kv"><dt>Статус</dt><dd>{'<span class="tag ok">Действует</span>' if st else '<span class="tag arch">Архив</span>'}</dd>
<dt>Как присоединиться</dt><dd>{'Оставить заявку ниже, дирекция свяжет с руководителем проекта' if st else 'Проект завершен, похожие инициативы в разделе действующих проектов'}</dd></dl>'''
        g = p.get('gallery') or []
        pbody, slugs = split_team(p.get('body') or '')
        members = [TEAM_BY_SLUG[s] for s in slugs if s in TEAM_BY_SLUG]
        team_html = f'<h2 style="margin:48px 0 24px">Команда проекта</h2><div class="people">{"".join(person_card(m) for m in members)}</div>' if members else ''
        body = crumbs(('Проекты', '/projects/'), (p['title'].strip()[:60], None)) + page_head(p['title'].strip()) + \
            f'<div class="wrap" style="padding-bottom:64px">{kv}<article class="prose">{tidy(fix_links(clean_body(pbody)))}</article>{gallery_html(g)}{team_html}</div>' + \
            (lead_form('Присоединиться к проекту', f'Оставьте контакты, дирекция передаст запрос руководителю проекта «{p["title"].strip()}».', 'Участие в проекте') if st else '')
        layout(f'/projects/{p["id"]}/', p['title'].strip(), body, desc=p.get('desc') or p['lead'], active='/projects/', og_img=None)


def build_lists(sections):
    for sec in ('commissions', 'clubs', 'boards', 'organization/partners'):
        GENERATED.add(f'/{sec}/')
        for it in sections[sec]:
            if is_own(it['url']) and urlparse(it['url']).path.startswith(f'/{sec}/'):
                GENERATED.add(path_of(it['url']))


def render_lists(sections):
    meta = {'commissions': ('Комитеты', 'Отраслевые комитеты отделения готовят позицию бизнеса и экспертные предложения. Вступить в комитет может любой участник.', 'Работа в комитете'),
            'clubs': ('Клубы', 'Неформальные сообщества по интересам. Участник может присоединиться к клубу или открыть свой.', 'Другое'),
            'boards': ('Советы и рабочие группы', 'Экспертные и общественные советы при органах власти, где представители отделения отстаивают интересы бизнеса.', 'Другое'),
            'organization/partners': ('Партнеры', 'Органы власти, институты развития и компании, с которыми работает отделение.', 'Партнерство')}
    for sec, (title, sub, interest) in meta.items():
        items = sections[sec]
        cards = ''
        for it in items:
            own = is_own(it['url']) and path_of(it['url']).startswith(f'/{sec}/')
            href = L(path_of(it['url'])) if own and path_of(it['url']) in GENERATED else it['url']
            ph = f'<div class="ph"><img src="{img(it["img"], 640)}" alt="" loading="lazy"{" style=object-fit:contain;padding:24px;background:#fff" if sec == "organization/partners" else ""}></div>' if it.get('img') else ''
            cards += f'<a class="card" href="{esc(href)}">{ph}<div class="in"><h3>{esc(it["title"])}</h3></div></a>'
        body = crumbs(('Сообщество', '/organization/about/'), (title, None)) + page_head(title, sub) + f'<div class="wrap layout">{side(SIDE_COMMUNITY, "/" + sec + "/")}<div><div class="grid g3">{cards}</div>{cta_join(interest=interest)}</div></div>'
        layout(f'/{sec}/', title, body, desc=sub, active='/organization/about/')
        for it in items:
            pth = path_of(it['url'])
            if not is_own(it['url']) or not pth.startswith(f'/{sec}/') or pth == f'/{sec}/':
                continue
            g = it.get('gallery') or []
            body = crumbs((title, f'/{sec}/'), (it['title'][:60], None)) + page_head(it['title']) + \
                f'<div class="wrap layout">{side(SIDE_COMMUNITY, "/" + sec + "/")}<div><article class="prose">{tidy(fix_links(clean_body(it.get("body") or "")))}</article>{gallery_html(g)}{cta_join(interest=interest)}</div></div>'
            layout(path_of(it['url']), it['title'], body, desc=it.get('desc') or first_sentence(it.get('body', '')), active='/organization/about/')


SERVICE_GROUPS = [('/services/package-of-documents/', 'Пакеты участия', 'users'), ('/services/investments-and-loans/', 'Финансы и инвестиции', 'banknote'),
                  ('/services/pr-package-of-documents/', 'PR-пакеты', 'megaphone'), ('/services/common-services/', 'Общие услуги', 'briefcase'),
                  ('/services/business-security/', 'Безопасность бизнеса', 'shield'), ('/services/upravlenie-komandirovkami/', 'Управление командировками', 'plane'),
                  ('/services/obrazovatelnye-programmy-korporativnogo-universiteta-sberbanka/', 'Обучение', 'graduation')]


def build_services(pages):
    for k in pages:
        if k.startswith('/services/') and '?' not in k:
            GENERATED.add(k)


def compare_table():
    rows = [('Деловые контакты, закрытые чаты отделения', True, True), ('Значок и сертификат организации', True, True),
            ('Карточка компании с компетенциями на ресурсах «Деловой России»', True, True), ('Рассылка предложения компании по базе участников', True, True),
            ('Консультации по финансированию, продажам и выходу на новые рынки', True, True), ('Встречи с органами власти, участие в стратегических сессиях', True, True),
            ('Работа в отраслевых комитетах и экспертных советах', True, True), ('Клубы по интересам, бизнес-завтраки, форум-группы', True, True),
            ('Два крупных события отделения в год', True, True), ('Персональный менеджер, календарь полезных встреч', False, True),
            ('Проверка рисков, помощь при проверках, защита от недобросовестных действий', False, True),
            ('Подбор программ поддержки, грантов, льготных кредитов', False, True), ('Помощь в поиске сотрудников и менторов', False, True),
            ('Выход на экспорт и в новые регионы через сеть организации', False, True), ('Интервью о компании, выступления на форумах организации и партнеров', False, True),
            ('Закрытые встречи с первыми лицами бизнеса и власти', False, True)]
    yn = lambda v: '<td class="y">Да</td>' if v else '<td class="n">Нет</td>'
    return f'''<div class="tbl-wrap"><table class="cmp"><thead><tr><th>Что входит</th><th>«Базовый»<small>100 000 ₽ в год</small></th><th>«Премиум»<small>190 000 ₽ в год</small></th></tr></thead>
<tbody>{''.join(f'<tr><th>{esc(r)}</th>{yn(a)}{yn(b)}</tr>' for r, a, b in rows)}</tbody></table></div>
<p class="note" style="margin-top:16px">Цены с сайта отделения на {dfmt(TODAY)}. Вступительный взнос, состав пакетов «Член регионального совета» и «Меценат» дирекция подтверждает отдельно.</p>'''


def render_services(pages):
    # хаб «Возможности»
    cards = ''
    for href, title, ic in SERVICE_GROUPS:
        kids = [(k, v) for k, v in pages.items() if k.startswith(href) and k != href and '?' not in k]
        lst = ''.join(f'<li><a href="{L(k)}">{esc(svc_title(v["title"]))}</a></li>' for k, v in kids[:6])
        cards += f'<div class="benefit"><div class="ic">{icon(ic)}</div><h3><a href="{L(href)}">{title}</a></h3><ul style="margin:0;padding-left:20px;color:var(--ink-2);font-size:15px">{lst}</ul></div>'
    side_items = [('Возможности', None)] + [(t, h) for h, t, _ in SERVICE_GROUPS]
    body = crumbs(('Возможности', None)) + page_head('Возможности участников', 'Что дает членство в отделении и какие сервисы доступны участникам и их компаниям.') + \
        f'<div class="wrap" style="padding-bottom:64px"><h2 style="margin-bottom:24px">Пакеты участия</h2>{compare_table()}<div style="margin-top:24px;display:flex;gap:16px;flex-wrap:wrap"><a class="btn btn-primary" href="{L("/organization/how-to-join/")}#zayavka">Обсудить вступление</a><a class="btn btn-line" href="#pay" data-pay>Оплатить взнос</a></div>' + \
        f'<h2 style="margin:64px 0 24px">Сервисы для участников</h2><div class="grid g3">{cards}</div></div>{lead_form()}'
    layout('/services/', 'Возможности', body, desc='Пакеты участия и сервисы для участников Пермского отделения «Деловой России».', active='/services/')
    for k, v in pages.items():
        if not k.startswith('/services/') or k == '/services/' or '?' in k:
            continue
        grp = next((h for h, _, _ in SERVICE_GROUPS if k.startswith(h)), '/services/')
        kids = [(kk, vv) for kk, vv in pages.items() if kk.startswith(k) and kk != k and '?' not in kk and kk.count('/') == k.count('/') + 1]
        listing = ''
        if kids:
            listing = '<div class="grid g2" style="margin-top:8px">' + ''.join(f'<a class="card" href="{L(kk)}"><div class="in"><h3>{esc(svc_title(vv["title"]))}</h3><p>{esc(first_sentence(vv.get("body", ""), 150))}</p></div></a>' for kk, vv in kids) + '</div>'
        bodyh = tidy(fix_links(clean_body(v.get('body') or '')))
        if kids:
            bodyh = ''  # у разделов в исходнике только список заголовков
        if k == '/services/package-of-documents/':
            bodyh = compare_table()
            listing = ''
        if k.endswith('/chlen-delovoy-rossii-paket-premium/'):
            bodyh = premium_text()
        if k.endswith('/chlen-delovoy-rossii/'):
            bodyh = '<p class="intro">100 000 ₽ в год</p>' + re.sub(r'^<p>\s*Описание\s*', '<p>', bodyh)
        title = svc_title(v['title'])
        body = crumbs(('Возможности', '/services/'), (title[:60], None)) + page_head(title) + \
            f'<div class="wrap layout">{side(side_items, grp)}<div><article class="prose" style="max-width:none">{bodyh}</article>{listing}{cta_join("Нужна эта возможность?", "Оставьте заявку, дирекция расскажет условия для участников и подберет эксперта.", "Вступление в «Деловую Россию»")}</div></div>'
        layout(k, title, body, desc=v.get('desc') or first_sentence(v.get('body', '')), active='/services/')


def svc_title(s):
    return tidy(re.sub(r'Член\s+Деловой России/', '', s)).strip()


def premium_text():
    return '''<p class="intro">190 000 ₽ в год. Все возможности пакета «Базовый» и персональное сопровождение.</p>
<h3>Персональный менеджер</h3><ul><li>Знает специфику вашего бизнеса и знакомит с нужными людьми в отделении и федеральной сети.</li><li>Составляет календарь полезных для вас встреч на месяц и квартал.</li><li>Собирает ключевые новости, изменения законодательства и события по вашей отрасли.</li></ul>
<h3>Сопровождение и развитие бизнеса</h3><ul><li>Проверка рисков в отношении налоговых и контрольно-надзорных органов, помощь при проверках.</li><li>Защита от недобросовестных действий конкурентов.</li><li>Регулярный подбор программ поддержки, грантов, субсидий и льготных кредитов.</li><li>Помощь в поиске сотрудников, узких специалистов и менторов.</li><li>Выход на экспорт и в новые регионы через федеральную сеть «Деловой России».</li></ul>
<h3>Продвижение</h3><ul><li>Публикации на сайте отделения, странице отделения на федеральном сайте и в приложении «Деловая Россия».</li><li>Интервью о вас и компании, рассылка предложения по базе участников.</li><li>Выступления на конференциях и форумах организации и партнеров, бизнес-завтраки с презентацией продукции.</li></ul>
<h3>Закрытые встречи</h3><ul><li>Встречи с первыми лицами бизнеса и власти по конкретному вопросу.</li><li>Клубные форматы для премиум-участников, деловые выезды и бизнес-миссии.</li></ul>'''


def build_static_pages(pages):
    for k in ['/organization/about/', '/organization/perm-region/', '/organization/experts/', '/organization/docs/', '/organization/requisites/', '/contacts/', '/organization/how-to-join/', '/privacy/']:
        GENERATED.add(k)


def render_static(pages, team):
    for k in ['/organization/about/', '/organization/perm-region/', '/organization/experts/', '/organization/requisites/']:
        v = pages[k]
        b = tidy(fix_links(clean_body(v['body'])))
        b = re.sub(r'<p>\s*Контакты\s*</p>\s*$', '', b)
        body = crumbs(('Сообщество', '/organization/about/'), (v['title'], None)) + page_head(v['title']) + \
            f'<div class="wrap layout">{side(SIDE_COMMUNITY, k)}<div><article class="prose">{b}</article>{cta_join()}</div></div>'
        layout(k, v['title'], body, desc=v.get('desc') or first_sentence(v['body']), active='/organization/about/')
    # документы: ссылки на файлы исходного сайта, опечатки исправлены
    v = pages['/organization/docs/']
    b = tidy(fix_links(clean_body(v['body'])))
    body = crumbs(('Сообщество', '/organization/about/'), ('Документы', None)) + page_head('Документы', 'Устав, положение о членстве, презентации и материалы для партнеров. Файлы открываются с текущего сайта отделения.') + \
        f'''<div class="wrap layout">{side(SIDE_COMMUNITY, '/organization/docs/')}<div>
<h2 style="margin-bottom:16px">Для вступления</h2><div class="docs">
<a class="doc" href="{ORIG}/upload/Вступление в ДР Пермский край вер 2.0 от 13.01.2023.docx" target="_blank" rel="noopener"><div class="ic">{icon('file', 20)}</div><div>Пакет документов на вступление<small>DOCX · версия 2.0 от 13.01.2023</small></div></a>
<a class="doc" href="{ORIG}/upload/Положение о членстве в ПК РО ООО Деловая Россия от 27.01.2025 г..pdf" target="_blank" rel="noopener"><div class="ic">{icon('file', 20)}</div><div>Положение о членстве<small>PDF · от 27.01.2025</small></div></a>
<a class="doc" href="{ORIG}/upload/Устав ПК РО Деловая Россия вер. 1.0 от 03.09.2019г..pdf" target="_blank" rel="noopener"><div class="ic">{icon('file', 20)}</div><div>Устав Пермского краевого регионального отделения<small>PDF · от 03.09.2019</small></div></a>
</div>
<h2 style="margin:48px 0 16px">Все материалы</h2><article class="prose">{b}</article>
<p class="note">Документы проверены {dfmt(TODAY)}. Публичный отчет за 2024–2025 годы и презентация на 2026 год готовятся дирекцией.</p></div></div>'''
    layout('/organization/docs/', 'Документы', body, desc='Устав, положение о членстве, пакет документов на вступление и материалы отделения.', active='/organization/about/')
    # контакты
    body = crumbs(('Контакты', None)) + page_head('Контакты', 'Дирекция отделения отвечает на вопросы о вступлении, мероприятиях и проектах.') + f'''
<div class="wrap" style="padding-bottom:80px"><div class="cont">
<dl><div><dt>Телефон</dt><dd><a href="{PHONE_HREF}">{PHONE}</a></dd></div><div><dt>Почта</dt><dd><a href="mailto:{EMAIL}">{EMAIL}</a></dd></div>
<div><dt>Адрес</dt><dd>{ADDR}</dd></div><div><dt>Режим работы</dt><dd>{HOURS}, сб и вс выходные</dd></div>
<div><dt>Исполнительный директор</dt><dd>Ирина Жданова</dd></div>
<div><dt>Мы в сети</dt><dd style="display:flex;gap:16px;flex-wrap:wrap"><a href="{TG}" target="_blank" rel="noopener">Telegram</a><a href="{VK}" target="_blank" rel="noopener">ВКонтакте</a><a href="{RUTUBE}" target="_blank" rel="noopener">Rutube</a></dd></div>
<div><a class="btn btn-line" href="https://yandex.ru/maps/?text={esc('Пермь, улица Революции, 20')}" target="_blank" rel="noopener">Маршрут в Яндекс Картах</a></div></dl>
<div class="map"><iframe title="Карта, Пермь, ул. Революции, 20" loading="lazy" src="https://yandex.ru/map-widget/v1/?text={esc('Пермь, улица Революции, 20')}&amp;z=16"></iframe></div>
</div></div>{lead_form('Написать в дирекцию', 'Оставьте контакты и тему вопроса, перезвоним в рабочее время.', 'Другое')}'''
    layout('/contacts/', 'Контакты', body, desc=f'Пермское отделение «Деловой России», {ADDR}, {PHONE}.', active='/contacts/')
    # политика
    v = pages.get('/include/licenses_detail.php')
    if v:
        body = crumbs(('Политика конфиденциальности', None)) + page_head('Политика конфиденциальности') + f'<div class="wrap" style="padding-bottom:80px"><article class="prose">{tidy(fix_links(clean_body(v["body"])))}</article></div>'
        layout('/privacy/', 'Политика конфиденциальности', body, desc='Политика обработки персональных данных.')
    render_join(team)


def render_join(team):
    faq = [('Кто может вступить?', 'Собственники и руководители среднего и крупного бизнеса, бизнес-консультанты и эксперты в предпринимательстве. Членство индивидуальное, вступает человек, а не компания.'),
           ('Сколько стоит участие?', 'Годовой взнос по пакету «Базовый» 100 000 ₽, по пакету «Премиум» 190 000 ₽. Размер вступительного взноса уточнит дирекция.'),
           ('Можно ли сначала познакомиться с сообществом?', 'Да. Приходите на открытое мероприятие отделения или на встречу в офисе на Революции, 20. После короткой заявки дирекция пригласит вас.'),
           ('Какие документы нужны?', 'Заявление, анкета кандидата, согласие на обработку персональных данных и документ об оплате вступительного взноса. Шаблоны пришлем после разговора.'),
           ('Сколько длится рассмотрение?', 'Решение принимает отделение, затем его утверждает Региональный совет на ближайшем заседании. Точный срок назовет дирекция.'),
           ('Что дальше после вступления?', 'Вы получаете значок и сертификат, доступ в закрытые чаты, карточку на сайте. Дирекция знакомит с комитетами и клубами под ваши задачи.')]
    body = crumbs(('Вступить', None)) + f'''
<section class="hero" style="padding-top:40px"><div class="wrap" style="grid-template-columns:1fr">
<div><h1>Вступить в «Деловую Россию» в Пермском крае</h1>
<p class="lead">Сообщество для собственников и руководителей компаний, которым нужны деловые связи, поддержка и голос бизнеса в регионе. Путь от заявки до решения совета занимает пять шагов.</p>
<div class="ctas"><a class="btn btn-primary" href="#zayavka">Оставить заявку на знакомство</a><a class="btn btn-line" href="{PHONE_HREF}">{PHONE}</a></div></div></div></section>
<section class="sec tight"><div class="wrap"><div class="sec-h"><h2>Как проходит вступление</h2></div>{steps_html()}</div></section>
<section class="sec soft"><div class="wrap"><div class="sec-h"><h2>Кому подходит</h2></div>
<div class="grid g3">
<div class="benefit"><div class="ic">{icon('building')}</div><h3>Собственникам и директорам</h3><p>Среднего и крупного бизнеса Пермского края в любой отрасли.</p></div>
<div class="benefit"><div class="ic">{icon('trending')}</div><h3>Тем, кто растет</h3><p>Выходит на новые рынки, ищет финансирование, партнеров и подрядчиков.</p></div>
<div class="benefit"><div class="ic">{icon('briefcase')}</div><h3>Экспертам и консультантам</h3><p>Кто готов делиться опытом в комитетах, советах и на бизнес-завтраках.</p></div>
</div></div></section>
<section class="sec"><div class="wrap"><div class="sec-h"><h2>Форматы участия и взносы</h2></div>{compare_table()}
<div style="margin-top:24px"><a class="link-more" href="{L('/services/package-of-documents/chlen-delovoy-rossii-paket-premium/')}">Подробнее о пакете «Премиум»</a></div></div></section>
<section class="sec soft"><div class="wrap"><div class="sec-h"><h2>Документы</h2><p>Шаблоны пришлем после разговора. Можно скачать заранее.</p></div>
<div class="docs" style="max-width:820px">
<a class="doc" href="{ORIG}/upload/Вступление в ДР Пермский край вер 2.0 от 13.01.2023.docx" target="_blank" rel="noopener"><div class="ic">{icon('file', 20)}</div><div>Пакет документов на вступление<small>Заявление, анкета, согласие · DOCX</small></div></a>
<a class="doc" href="{ORIG}/upload/Положение о членстве в ПК РО ООО Деловая Россия от 27.01.2025 г..pdf" target="_blank" rel="noopener"><div class="ic">{icon('file', 20)}</div><div>Положение о членстве<small>PDF · от 27.01.2025</small></div></a>
<a class="doc" href="{ORIG}/upload/Устав ПК РО Деловая Россия вер. 1.0 от 03.09.2019г..pdf" target="_blank" rel="noopener"><div class="ic">{icon('file', 20)}</div><div>Устав отделения<small>PDF · от 03.09.2019</small></div></a>
</div></div></section>
<section class="sec"><div class="wrap"><div class="sec-h"><h2>Частые вопросы</h2></div><div class="faq">
{''.join(f'<details><summary>{esc(q)}</summary><div class="a">{esc(a)}</div></details>' for q, a in faq)}</div></div></section>
{lead_form('Заявка на знакомство', 'Это первый шаг, он ни к чему не обязывает. Исполнительный директор позвонит в течение двух рабочих дней.', 'Вступление в «Деловую Россию»')}'''
    layout('/organization/how-to-join/', 'Вступить', body, desc='Как вступить в Пермское отделение «Деловой России»: условия, взносы, этапы, документы, частые вопросы.', active=None)
    redirect('/organization/kak-vstupit/', '/organization/how-to-join/')


def redirect(frm, to):
    f = os.path.join(OUT, frm.lstrip('/'), 'index.html')
    os.makedirs(os.path.dirname(f), exist_ok=True)
    open(f, 'w').write(f'<!doctype html><meta charset="utf-8"><meta name="robots" content="noindex"><meta http-equiv="refresh" content="0;url={L(to)}"><link rel="canonical" href="{L(to)}"><a href="{L(to)}">{L(to)}</a>')
    GENERATED.add(frm)


def plural(n, one, few, many):
    n = abs(int(n)) % 100
    if 11 <= n <= 19:
        return many
    n %= 10
    return one if n == 1 else few if 2 <= n <= 4 else many


def compute_stats(news, events, team, projects, sections):
    y = TODAY[:4]
    last12 = (datetime.date.fromisoformat(TODAY) - datetime.timedelta(days=365)).isoformat()
    ev12 = sum(1 for e in events if last12 <= (e.get('date') or '') <= TODAY)
    news12 = sum(1 for n in news if (n.get('date') or '') >= last12)
    act = sum(1 for p in projects if p['status'] == 'active')
    members = len(team)
    period = f'{dfmt(last12)} – {dfmt(TODAY)}'
    return {
        'hero': [(f'{int(y) - 2004}', plural(int(y) - 2004, 'год', 'года', 'лет') + ' работы', 'отделение с 2004 года'),
                 (f'{ev12}', plural(ev12, 'мероприятие', 'мероприятия', 'мероприятий') + ' за год', 'последние 12 месяцев'),
                 (f'{members}', plural(members, 'участник', 'участника', 'участников') + ' на сайте', f'на {dfmt(TODAY)}')],
        'scale': [(f'{ev12}', plural(ev12, 'мероприятие', 'мероприятия', 'мероприятий'), f'за последние 12 месяцев, {period}'),
                  (f'{act}', plural(act, 'действующий проект', 'действующих проекта', 'действующих проектов'), f'на {dfmt(TODAY)}, статусы предварительные'),
                  (f'{len(sections["boards"])}', plural(len(sections["boards"]), 'совет и рабочая группа', 'совета и рабочих группы', 'советов и рабочих групп'), 'при органах власти, где работают делороссы'),
                  ('1 млрд ₽', 'льготного финансирования', 'получили участники, по данным отделения, период уточняется'),
                  ('20', 'предложений', 'по изменению законодательства, по данным отделения'),
                  (f'{len(sections["commissions"])}', plural(len(sections["commissions"]), 'комитет', 'комитета', 'комитетов'), 'отраслевых и тематических'),
                  (f'{len(sections["clubs"])}', plural(len(sections["clubs"]), 'клуб', 'клуба', 'клубов'), 'по интересам'),
                  (f'{news12}', plural(news12, 'новость', 'новости', 'новостей'), 'за последние 12 месяцев')],
    }


def main():
    global NAV
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    shutil.copytree(os.path.join(HERE, 'assets'), os.path.join(OUT, 'assets'))
    news, events, team, sections, pages, projects = load()
    if '/include/licenses_detail.php' in pages:
        GENERATED.add('/include/licenses_detail.php')
    NAV = build_nav(projects)
    # 1) какие страницы будут — чтобы ссылки внутри старого контента вели на макет
    build_projects(projects)
    local_news = build_news(news)
    local_events = build_events(events)
    build_team(team)
    TEAM_BY_SLUG.update({p['url'].rstrip('/').split('/')[-1]: p for p in team})
    build_lists(sections)
    build_services(pages)
    build_static_pages(pages)
    LINK_MAP['/include/licenses_detail.php'] = '/privacy/'
    GENERATED.update({'/', '/services/'})
    # 2) рендер
    stats = compute_stats(news, events, team, projects, sections)
    build_home(news, events, team, projects, stats)
    render_news_details(local_news, news)
    render_events(local_events, events)
    render_team(team)
    render_projects(projects)
    render_lists(sections)
    render_services(pages)
    render_static(pages, team)
    for frm, to in [('/meropriyatiya/', '/events/'), ('/organization/', '/organization/about/'), ('/include/licenses_detail.php/', '/privacy/'),
                    ('/services/obshchie-uslugi/finansovyy-ekonomicheskiy-audit/', '/services/common-services/finansovyy-ekonomicheskiy-audit/'),
                    ('/services/package-of-documents/predsedatel-regionalnogo-otdeleniya/', '/services/package-of-documents/')]:
        redirect(frm, to)
    layout('/404.html', 'Страница не найдена', page_head('Страница не найдена', 'Возможно, адрес изменился после обновления сайта.') + f'<div class="wrap" style="padding-bottom:80px;display:flex;gap:16px;flex-wrap:wrap"><a class="btn btn-primary" href="{L("/")}">На главную</a><a class="btn btn-line" href="{L("/events/")}">Мероприятия</a><a class="btn btn-line" href="{L("/organization/how-to-join/")}">Вступить</a></div>')
    open(os.path.join(OUT, 'robots.txt'), 'w').write('User-agent: *\nDisallow: /\n')
    open(os.path.join(OUT, '.nojekyll'), 'w').write('')
    bad = run_images()
    if bad:  # убрать битые картинки из разметки
        for root, _, files in os.walk(OUT):
            for fn in files:
                if fn.endswith('.html'):
                    fp = os.path.join(root, fn)
                    t = open(fp, encoding='utf-8').read()
                    alt = '|'.join(re.escape(b) for b in bad)
                    t2 = re.sub(r'<a href="[^"]*/img/(' + alt + r')"[^>]*>.*?</a>', '', t)
                    t2 = re.sub(r'<img src="[^"]*/img/(' + alt + r')"[^>]*>', '', t2)
                    if t2 != t:
                        open(fp, 'w', encoding='utf-8').write(t2)
    n = sum(len([f for f in fs if f.endswith('.html')]) for _, _, fs in os.walk(OUT))
    print(f'страниц: {n}')


if __name__ == '__main__':
    main()

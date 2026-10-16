"""Сборка макета сайта Пермского отделения «Деловой России» из data/*.json → site/.
Схема страниц как на deloros.ru: шапка в две строки, голубая полоса с крошками, контент + правая колонка
с виджетами, партнеры и синий подвал на каждой странице. Тексты только с deloros-perm.ru, код свой.
Запуск:  python3 src/build.py                                   (site/, ссылки от корня)
         OUT=docs BASE=/deloros-perm-maket python3 src/build.py  (GitHub Pages)"""
import os, re, json, html, shutil, hashlib, datetime
from urllib.parse import urlparse, unquote
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
DATA = os.path.join(PROJ, 'data')
OUT = os.environ.get('OUT') or os.path.join(PROJ, 'site')
MIR = os.path.join(PROJ, '_сырьё', 'mirror')
IMGCACHE = os.path.join(PROJ, '_сырьё', 'imgcache')
ORIG = 'https://deloros-perm.ru'
P = os.environ.get('BASE', '').rstrip('/')
TODAY = os.environ.get('TODAY', datetime.date.today().isoformat())
VER = datetime.datetime.now().strftime('%m%d%H%M')

PHONE, PHONE_HREF = '+7 (342) 256-35-05', 'tel:+73422563505'
EMAIL = 'welcome@deloros59.ru'
ADDR = '614007, Пермь, ул. Революции, 20, офис 406, БЦ «Бонус»'
VK, TG, RUTUBE = 'https://vk.com/deloros59', 'https://t.me/deloros59', 'https://rutube.ru/channel/56421523/'
PAY_CKASSA = 'https://ckassa.ru/payment/#!search_provider/pt_search/111-15131-1/pay'
PAY_SBER = 'https://securepayments.sberbank.ru/shortlink/2KYMlQZt'
BOOK = 'https://book.deloros59.ru/'
DOC_JOIN = ORIG + '/upload/Вступление в ДР Пермский край вер 2.0 от 13.01.2023.docx'
DOC_POL = ORIG + '/upload/Положение о членстве в ПК РО ООО Деловая Россия от 27.01.2025 г..pdf'
DOC_USTAV = ORIG + '/upload/Устав ПК РО Деловая Россия вер. 1.0 от 03.09.2019г..pdf'
NEWS_FROM = os.environ.get('NEWS_FROM', '2025-10-01')    # с какой даты у новости своя страница в макете
EVENTS_FROM = os.environ.get('EVENTS_FROM', '2025-09-01')
PRIORITY = ['139', '156', '155', '162', '158', '154']
CATS = {'regional-office': 'Новости отделения', 'partners': 'Новости партнеров', 'events': 'Анонсы и итоги'}

J = lambda n: json.load(open(os.path.join(DATA, n), encoding='utf-8'))
esc = lambda s: html.escape(s or '', quote=True)
L = lambda path: P + path
MG = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']


def dfmt(iso, year=True):
    if not iso:
        return ''
    y, m, d = iso.split('-')
    return f'{int(d)} {MG[int(m) - 1]}' + (f' {y}' if year else '')


def dnum(iso):
    return '.'.join(reversed(iso.split('-'))) if iso else ''


def path_of(url):
    return urlparse(url).path


def is_own(url):
    return urlparse(url).netloc.lower().removeprefix('www.') in ('deloros-perm.ru', 'deloros59.ru', '')


# ---------------- картинки → WebP ----------------
JOBS = {}


def img(url, w=800):
    if not url:
        return ''
    if url.startswith('/'):
        url = ORIG + url
    name = hashlib.md5(f'{url}|{w}'.encode()).hexdigest()[:16] + '.webp'
    JOBS[name] = (url, w)
    return L(f'/img/{name}')


def _convert(args):
    name, url, w = args
    from PIL import Image, ImageOps
    import requests
    cache = os.path.join(IMGCACHE, name)
    if not os.path.exists(cache):
        src = os.path.join(MIR, unquote(urlparse(url).path).lstrip('/'))
        if not os.path.exists(src) or os.path.getsize(src) == 0:
            try:
                r = requests.get(url, timeout=40, headers={'User-Agent': 'Mozilla/5.0 DAPI-mirror/1.0'})
                if r.status_code != 200 or not r.content:
                    return name, f'http {r.status_code}'
                os.makedirs(os.path.dirname(src), exist_ok=True)
                open(src, 'wb').write(r.content)
            except Exception as e:
                return name, str(e)[:80]
        try:
            im = ImageOps.exif_transpose(Image.open(src))
            if im.mode not in ('RGB', 'RGBA'):
                im = im.convert('RGBA' if 'transparency' in im.info or im.mode in ('LA', 'P') else 'RGB')
            if im.width > w:
                im = im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)
            im.save(cache, 'WEBP', quality=76, method=4)
        except Exception as e:
            return name, 'img ' + str(e)[:80]
    shutil.copyfile(cache, os.path.join(OUT, 'img', name))
    return name, None


def run_images():
    os.makedirs(IMGCACHE, exist_ok=True)
    os.makedirs(os.path.join(OUT, 'img'), exist_ok=True)
    bad = []
    with ProcessPoolExecutor(max_workers=8) as ex:
        for n, err in ex.map(_convert, [(n, u, w) for n, (u, w) in JOBS.items()], chunksize=16):
            if err:
                bad.append(n)
    print(f'картинки: {len(JOBS)}, не вышло {len(bad)}')
    return set(bad)


# ---------------- иконки (Lucide) ----------------
ICONS = {
    'userplus': '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><line x1="19" x2="19" y1="8" y2="14"/><line x1="22" x2="16" y1="11" y2="11"/>',
    'card': '<rect width="20" height="14" x="2" y="5" rx="2"/><line x1="2" x2="22" y1="10" y2="10"/>',
    'book': '<path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20"/>',
    'search': '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
    'menu': '<line x1="4" x2="20" y1="6" y2="6"/><line x1="4" x2="20" y1="12" y2="12"/><line x1="4" x2="20" y1="18" y2="18"/>',
    'right': '<path d="M5 12h14"/><path d="m12 5 7 7-7 7"/>',
    'chl': '<path d="m15 18-6-6 6-6"/>', 'chr': '<path d="m9 18 6-6-6-6"/>',
    'send': '<path d="m22 2-7 20-4-9-9-4Z"/><path d="M22 2 11 13"/>',
    'play': '<polygon points="6 3 20 12 6 21 6 3"/>',
    'file': '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M10 9H8M16 13H8M16 17H8"/>',
    'users': '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    'banknote': '<rect width="20" height="12" x="2" y="6" rx="2"/><circle cx="12" cy="12" r="2"/><path d="M6 12h.01M18 12h.01"/>',
    'megaphone': '<path d="m3 11 18-5v12L3 14v-3z"/><path d="M11.6 16.8a3 3 0 1 1-5.8-1.6"/>',
    'shield': '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/>',
    'briefcase': '<path d="M16 20V4a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/><rect width="20" height="14" x="2" y="6" rx="2"/>',
    'graduation': '<path d="M21.42 10.92a1 1 0 0 0-.02-1.84L12.83 5.18a2 2 0 0 0-1.66 0L2.6 9.08a1 1 0 0 0 0 1.83l8.57 3.91a2 2 0 0 0 1.66 0z"/><path d="M22 10v6"/><path d="M6 12.5V16a6 3 0 0 0 12 0v-3.5"/>',
    'plane': '<path d="M17.8 19.2 16 11l3.5-3.5C21 6 21.5 4 21 3c-1-.5-3 0-4.5 1.5L13 8 4.8 6.2c-.5-.1-.9.1-1.1.5l-.3.5c-.2.5-.1 1 .3 1.3L9 12l-2 3H4l-1 1 3 2 2 3 1-1v-3l3-2 3.5 5.3c.3.4.8.5 1.3.3l.5-.2c.4-.3.6-.7.5-1.2z"/>',
    'factory': '<path d="M2 20a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V8l-7 5V8l-7 5V4a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2Z"/>',
    'rocket': '<path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z"/><path d="m12 15-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z"/><path d="M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0"/><path d="M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5"/>',
    'coffee': '<path d="M10 2v2M14 2v2M16 8a1 1 0 0 1 1 1v8a4 4 0 0 1-4 4H7a4 4 0 0 1-4-4V9a1 1 0 0 1 1-1h14a4 4 0 1 1 0 8h-1"/><path d="M6 2v2"/>',
    'scale': '<path d="m16 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"/><path d="m2 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"/><path d="M7 21h10M12 3v18M3 7h2c2 0 5-1 7-2 2 1 5 2 7 2h2"/>',
}


def icon(n):
    return f'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{ICONS[n]}</svg>'


# ---------------- старый контент: ссылки, мусор, опечатки ----------------
GENERATED = set()
LINK_MAP = {'/services/obshchie-uslugi/finansovyy-ekonomicheskiy-audit/': '/services/common-services/finansovyy-ekonomicheskiy-audit/',
            '/organization/kak-vstupit/': '/organization/how-to-join/', '/meropriyatiya/': '/events/',
            '/organization/': '/organization/about/', '/include/licenses_detail.php': '/privacy/'}


def fix_links(h):
    def rep_a(m):
        u = m.group(1)
        pu = urlparse(u)
        if pu.netloc.lower().removeprefix('www.') in ('deloros-perm.ru', 'deloros59.ru'):
            path = LINK_MAP.get(unquote(pu.path) or '/', unquote(pu.path) or '/')
            if path in GENERATED:
                return f'href="{esc(L(path))}"'
            return f'href="{esc(ORIG + pu.path)}" target="_blank" rel="noopener"'
        return f'href="{esc(u)}" target="_blank" rel="noopener"'
    h = re.sub(r'href="([^"]+)"', rep_a, h)
    h = re.sub(r'src="(https?://(?:www\.)?deloros-perm\.ru/upload/[^"]+)"', lambda m: f'src="{img(html.unescape(m.group(1)), 1200)}" loading="lazy"', h)
    return re.sub(r'<iframe src="([^"]+)"', r'<iframe loading="lazy" src="\1" allowfullscreen', h)


def clean_body(h):
    # на живом сайте в комитетах выводится служебный дамп Битрикса «Array ( [0] => …» вместо кнопки
    h = re.sub(r'<p>(?:(?!</p>).)*=&gt; Array(?:(?!</p>).)*</p>|<p>(?:(?!</p>).)*=> Array(?:(?!</p>).)*</p>', '', h, flags=re.S)
    h = re.sub(r'(Вступить в комитет\s*)?Array\s*\([^<]*', '', h)
    h = re.sub(r'<p>\s*(Подписаться на\s*(<br/>)?\s*рассылку|Будьте в курсе последних новостей отрасли|Подписаться|Назад к списку|Поделиться|Описание)\s*</p>', '', h)
    h = re.sub(r'^<p>\s*Описание\s+', '<p>', h)
    h = re.sub(r'<ul>(\s*<li>\s*<a href="[^"]*search_tags[^"]*">[^<]*</a>\s*</li>)+\s*</ul>', '', h)
    h = re.sub(r'<a href="[^"]*">\s*</a>', '', h)
    h = re.sub(r'E-mail\s+[\w.+-]+@[\w-]+\.[\w.]+', '', h)
    h = re.sub(r'<a href="mailto:[^"]+"[^>]*>.*?</a>', '', h)
    return re.sub(r'<p>\s*(<br/?>\s*)*</p>', '', h)


def split_team(h):
    """Хвост страницы с карточками участников → (текст без хвоста, slug'и участников)."""
    m = re.search(r'<p>\s*<a href="[^"]*/organization/team/members/[^"]+">\s*<img', h)
    if not m:
        return h, []
    return h[:m.start()], list(dict.fromkeys(re.findall(r'/organization/team/members/([^/"]+)/', h[m.start():])))


def tidy(h):
    for a, b in {'орбщественной': 'общественной', 'програма': 'программа', 'Финансовый-экономический': 'Финансово-экономический',
                 'о изменении': 'об изменении', 'Пермском краю': 'Пермскому краю', 'Член  Деловой': 'Член Деловой'}.items():
        h = h.replace(a, b)
    return h


def body_html(h):
    return tidy(fix_links(clean_body(h or '')))


def strip_tags(h):
    return ' '.join(re.sub(r'<[^>]+>', ' ', h or '').split())


def plural(n, one, few, many):
    n = abs(int(n)) % 100
    if 11 <= n <= 19:
        return many
    n %= 10
    return one if n == 1 else few if 2 <= n <= 4 else many


# ---------------- данные ----------------
D = {}


def load():
    news = [n for n in J('news.json') if n.get('title') and n.get('url', '').count('/') >= 6]
    for n in news:
        n['cat'] = n.get('cat') or urlparse(n['url']).path.split('/')[2]
        n['local'] = (n.get('date') or '') >= NEWS_FROM
        n['pic'] = n.get('thumb') or (n.get('gallery') or [None])[0]
    events = J('events.json')
    for e in events:
        e['local'] = e['upcoming'] or (e.get('date') or '') >= EVENTS_FROM
    team = [p for p in J('team.json') if p.get('url') and '/members/' in p['url']]
    sections = J('sections.json')
    projects = []
    for p in sections['projects']:
        pid = p['url'].rstrip('/').split('/')[-1]
        if pid.isdigit():
            p['id'] = pid
            years = [int(y) for y in re.findall(r'\b(20[12]\d)\b', p.get('body', '') + ' ' + p['title'])]
            p['active'] = int(pid) >= 149 or bool(years and max(years) >= 2025)
            p['title'] = p['title'].strip()
            projects.append(p)
    D.update(news=news, events=events, team=team, sections=sections, pages=J('pages.json'), projects=projects,
             team_by_slug={p['url'].rstrip('/').split('/')[-1]: p for p in team})


def nhref(n):
    return L(path_of(n['url'])) if n['local'] else n['url']


def ntarget(n):
    return '' if n['local'] else ' target="_blank" rel="noopener"'


def pic_tag(url, w, alt='', extra=''):
    return f'<img src="{img(url, w)}" alt="{esc(alt)}" loading="lazy"{extra}>' if url else ''


# ---------------- каркас ----------------
NAV = None
TEAM_GROUPS = [('Председатель и сопредседатель', '/organization/team/rukovodstvo/', 'rukovodstvo'),
               ('Исполнительная дирекция', '/organization/team/direkciya/', 'direkciya'),
               ('Региональный совет', '/organization/team/sovet/', 'sovet'),
               ('Лидеры комитетов', '/organization/team/lidery/', 'lidery'),
               ('Члены отделения', '/organization/team/chleny/', 'chleny')]
SERVICE_GROUPS = [('/services/package-of-documents/', 'Пакеты участия', 'users'), ('/services/investments-and-loans/', 'Финансы и инвестиции', 'banknote'),
                  ('/services/pr-package-of-documents/', 'PR-пакеты', 'megaphone'), ('/services/common-services/', 'Общие услуги', 'briefcase'),
                  ('/services/business-security/', 'Безопасность бизнеса', 'shield'), ('/services/upravlenie-komandirovkami/', 'Управление командировками', 'plane'),
                  ('/services/obrazovatelnye-programmy-korporativnogo-universiteta-sberbanka/', 'Образовательные программы', 'graduation')]
ABOUT_MENU = [('О «Деловой России»', '/organization/about/'), ('«Деловая Россия» в Пермском крае', '/organization/perm-region/'), ('Вступить', '/organization/how-to-join/'),
              ('Партнеры', '/organization/partners/'), ('Документы', '/organization/docs/'), ('Реквизиты', '/organization/requisites/'), ('Контакты', '/contacts/')]
TEAM_MENU = [(t, h) for t, h, _ in TEAM_GROUPS] + [('Эксперты', '/organization/experts/')]


def build_nav():
    pr = {p['id']: p for p in D['projects']}
    return [
        ('О нас', '/organization/about/', ABOUT_MENU),
        ('Лица', '/organization/team/', TEAM_MENU),
        ('Комитеты', '/commissions/', None),
        ('Советы', '/boards/', None),
        ('Клубы', '/clubs/', None),
        ('Проекты', '/projects/', [(pr[i]['title'], f'/projects/{i}/') for i in PRIORITY if i in pr] + [('Все проекты', '/projects/')]),
        ('Возможности', '/services/', [(t, h) for h, t, _ in SERVICE_GROUPS]),
        ('Мероприятия', '/events/', None),
        ('Пресс-центр', '/news/', [('Все новости', '/news/')] + [(v, f'/news/{k}/') for k, v in CATS.items()]),
        ('Контакты', '/contacts/', None),
    ]


def soc_links():
    return (f'<div class="soc"><a href="{VK}" target="_blank" rel="noopener" aria-label="ВКонтакте">vk</a>'
            f'<a href="{TG}" target="_blank" rel="noopener" aria-label="Telegram">{icon("send")}</a>'
            f'<a href="{RUTUBE}" target="_blank" rel="noopener" aria-label="Rutube">{icon("play")}</a></div>')


def header(active):
    items = ''
    for t, h, sub in NAV:
        dd = '<ul class="dd">' + ''.join(f'<li><a href="{L(sh)}">{esc(st)}</a></li>' for st, sh in sub) + '</ul>' if sub else ''
        items += f'<li{" class=on" if active == h else ""}><a href="{L(h)}">{esc(t)}</a>{dd}</li>'
    mob = ''
    for t, h, sub in NAV:
        mob += f'<a href="{L(h)}">{esc(t)}</a>'
        if sub:
            mob += '<div class="sub">' + ''.join(f'<a href="{L(sh)}">{esc(st)}</a>' for st, sh in sub) + '</div>'
    return f'''<header>
<div class="ht"><div class="c">
 <a class="hb" href="{L('/organization/how-to-join/')}">Вступить в<br>организацию {icon('userplus')}</a>
 {soc_links()}
 <a class="hb blue" href="#pay" data-pay>Оплатить<br>взнос {icon('card')}</a>
 <a class="hb blue hide-l" href="{BOOK}" target="_blank" rel="noopener">Книга «Предприниматели<br>и меценаты Прикамья» {icon('book')}</a>
 <a class="hphone" href="{PHONE_HREF}">{PHONE}</a>
 <form class="hsearch" action="{L('/search/')}" role="search"><input name="q" aria-label="Поиск по сайту"><button aria-label="Найти">{icon('search')}</button></form>
</div></div>
<div class="hn"><div class="c">
 <a class="logo" href="{L('/')}"><img src="{L('/assets/logo.png')}" alt="Деловая Россия. Пермский край" width="150" height="44"></a>
 <ul class="nav">{items}</ul>
 <button class="burger" aria-label="Меню" aria-expanded="false" data-burger>{icon('menu')}</button>
</div></div>
<div class="mnav" data-mnav>{mob}<a href="{PHONE_HREF}">{PHONE}</a><a href="#pay" data-pay>Оплатить взнос</a><a href="{L('/search/')}">Поиск</a><a class="btn" href="{L('/organization/how-to-join/')}">Вступить в организацию</a></div>
</header>'''


def partner_href(p):
    own = is_own(p['url']) and path_of(p['url']).startswith('/organization/partners/')
    return (L(path_of(p['url'])), '') if own else (esc(p['url']), ' target="_blank" rel="noopener"')


def partners_strip():
    cards, seen = '', set()
    for p in D['sections']['organization/partners']:
        f = os.path.join(MIR, unquote(path_of(p.get('img') or '')).lstrip('/'))
        key = hashlib.md5(open(f, 'rb').read()).hexdigest() if p.get('img') and os.path.isfile(f) else os.path.basename(p.get('img') or '')
        if p.get('img') and key not in seen and not seen.add(key):
            h, t = partner_href(p)
            cards += f'<a class="pt" href="{h}"{t} title="{esc(p["title"])}">{pic_tag(p["img"], 320, p["title"])}</a>'
    return f'''<section class="sec soft"><div class="c"><div class="sh"><h2>Наши партнёры</h2></div>
<div class="slider" data-slider><div class="track">{cards}</div><div class="ctl-row"><div class="nav-btns"><button class="nb" data-prev aria-label="Назад">{icon('chl')}</button><button class="nb" data-next aria-label="Вперед">{icon('chr')}</button></div></div></div></div></section>'''


def footer():
    return f'''{partners_strip()}
<footer class="ftr"><div class="c">
 <div class="fa"><span>{ADDR}</span><i></i><a href="{PHONE_HREF}">тел.: {PHONE}</a><i></i><a href="mailto:{EMAIL}">Email: {EMAIL}</a></div>
 <div class="fm2"><img src="{L('/assets/logo.png')}" alt="" width="136" height="40"><p><b>© Пермское краевое региональное отделение «Деловая Россия», 2004–{TODAY[:4]}.</b><br>ИНН 5902990323 · Пн–пт 9:00–18:00</p>{soc_links()}</div>
 <div class="fb"><a href="{L('/privacy/')}">Политика обработки персональных данных</a><a href="{L('/organization/requisites/')}">Реквизиты</a><a href="{L('/organization/docs/')}">Документы</a><a href="#pay" data-pay>Оплатить взнос</a><span class="r">Макет сайта · DAPI</span></div>
</div></footer>
<div class="modal" id="pay" role="dialog" aria-modal="true" aria-labelledby="pay-h"><div class="bx"><button class="x" data-close aria-label="Закрыть">×</button>
 <h3 id="pay-h">Оплатить членский взнос</h3><p class="note">Годовой взнос по пакету «Базовый» 100 000 ₽, по пакету «Премиум» 190 000 ₽. Сумма вводится на странице оплаты.</p>
 <div class="pay"><a href="{PAY_SBER}" target="_blank" rel="noopener"><span>Банковской картой<small>Платежная страница ПАО Сбербанк</small></span>{icon('right')}</a>
 <a href="{PAY_CKASSA}" target="_blank" rel="noopener"><span>Через «Центральную кассу»<small>Поставщик «Деловая Россия», Пермский край</small></span>{icon('right')}</a></div>
 <p class="note" style="margin-top:16px">Оплата по счету: напишите на <a href="mailto:{EMAIL}" style="color:var(--blue)">{EMAIL}</a>.</p></div></div>
<div class="modal" id="thanks" role="dialog" aria-modal="true"><div class="bx"><button class="x" data-close aria-label="Закрыть">×</button><h3>Спасибо за отправленную заявку!</h3><p class="note">Исполнительная дирекция отделения свяжется с вами по указанному телефону.</p></div></div>'''


def layout(path, title, main, desc='', active=None):
    desc = re.sub(r'(Вступить в комитет\s*)?Array\s*\(.*', '', desc or '', flags=re.S).strip() or title
    full = 'Деловая Россия · Пермский край' if path == '/' else f'{title} · Деловая Россия, Пермский край'
    doc = f'''<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(full)}</title><meta name="description" content="{esc((desc or '')[:200])}"><meta name="robots" content="noindex,nofollow">
<link rel="canonical" href="{ORIG}{esc(path)}"><link rel="icon" href="{L('/assets/favicon.png')}">
<link rel="preload" href="{L('/assets/fonts/onest-cyrillic-600.woff2')}" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="{L('/assets/site.css')}?v={VER}"></head><body>
{header(active)}<main>{main}</main>{footer()}
<script>window.BASE={json.dumps(P)};</script><script src="{L('/assets/app.js')}?v={VER}" defer></script></body></html>'''
    f = os.path.join(OUT, path.lstrip('/'), 'index.html') if path.endswith('/') else os.path.join(OUT, path.lstrip('/'))
    os.makedirs(os.path.dirname(f), exist_ok=True)
    open(f, 'w', encoding='utf-8').write(doc)


def inner(path, title, crumbs, content, aside=None, desc='', active=None):
    cb = f'<a href="{L("/")}">Главная</a>' + ''.join(f'<i></i><a href="{L(h)}">{esc(t)}</a>' if h else f'<i></i><span>{esc(t)}</span>' for t, h in crumbs)
    aside = aside if aside is not None else wg_news() + wg_events()
    main = f'<div class="cb"><div class="c">{cb}</div></div><div class="c"><h1 class="ph1">{esc(title)}</h1><div class="pg"><div>{content}</div><aside class="aside">{aside}</aside></div></div>'
    layout(path, title, main, desc, active)


# ---------------- виджеты правой колонки ----------------
def wg_news(title='Новости', items=None, more=('Все новости', '/news/')):
    items = items if items is not None else D['news'][:6]
    if not items:
        return ''
    rows = ''.join(f'<a class="it" href="{nhref(n)}"{ntarget(n)}><small>{dfmt(n.get("date"))}</small>{esc(n["title"])}</a>' for n in items[:6])
    return f'<div class="wg"><h3>{esc(title)}</h3>{rows}<a class="more" href="{L(more[1])}">{more[0]} {icon("right")}</a></div>'


def wg_events():
    up = sorted([e for e in D['events'] if e['upcoming']], key=lambda e: e.get('date') or '9')
    if not up:
        return ''
    rows = ''.join(f'<a class="it" href="{L(path_of(e["url"]))}"><small>{esc(e.get("date_text") or "")}</small>{esc(e["title"])}</a>' for e in up[:5])
    return f'<div class="wg"><h3>Анонсы</h3>{rows}<a class="more" href="{L("/events/")}">Все мероприятия {icon("right")}</a></div>'


def wm(items, cur):
    return '<nav class="wm">' + ''.join(f'<a href="{L(h)}"{" class=on" if h == cur else ""}>{esc(t)}</a>' for t, h in items) + '</nav>'


def news_about(words, n=6):
    rx = re.compile('|'.join(words), re.I)
    return [x for x in D['news'] if rx.search(x['title'])][:n]


# ---------------- общие куски ----------------
def gallery(urls, limit=16):
    if not urls:
        return ''
    return '<div class="gal">' + ''.join(f'<a href="{img(u, 1600)}" data-lb>{pic_tag(u, 400)}</a>' for u in urls[:limit]) + '</div>'


def person(p):
    return f'<a class="person" href="{L(path_of(p["url"]))}"><div class="im">{pic_tag(p.get("photo") or p.get("photo_big"), 480, p["name"])}</div><b>{esc(p["name"])}</b><span>{esc(p.get("role") or "Член «Деловой России»")}</span></a>'


def people_block(slugs, title):
    ms = [D['team_by_slug'][s] for s in slugs if s in D['team_by_slug']]
    return f'<h2 class="h2s">{title}</h2><div class="people">{"".join(person(m) for m in ms)}</div>' if ms else ''


def pager(base, i, pages):
    if pages < 2:
        return ''
    nums = sorted({1, 2, pages - 1, pages, i, i + 1, i + 2} & set(range(1, pages + 1)))
    out, prev = [], 0
    for k in nums:
        if k - prev > 1:
            out.append('<span>…</span>')
        out.append(f'<span class="on">{k}</span>' if k == i + 1 else f'<a href="{L(base if k == 1 else f"{base}page-{k}/")}">{k}</a>')
        prev = k
    return f'<nav class="pager" aria-label="Страницы">{"".join(out)}</nav>'


def search_panel():
    return f'''<form class="srch" action="{L('/search/')}"><input class="q" name="q" placeholder="Поиск" aria-label="Поиск"><button>Найти</button>
<input name="from" type="date" aria-label="Дата от"><input name="to" type="date" aria-label="Дата до"></form>'''


def news_row(n):
    return f'<a class="row" href="{nhref(n)}"{ntarget(n)}><div class="im">{pic_tag(n.get("pic"), 320)}</div><div><small>{dfmt(n.get("date"))}</small><b>{esc(n["title"])}</b></div></a>'


def ev_row(e):
    up = e['upcoming']
    yr = f'<small>{e["date"][:4]}</small>' if e.get('date') and not up else ''
    return f'<a class="row ev" href="{L(path_of(e["url"]))}"><div class="d{" up" if up else ""}">{esc(e.get("date_text") or dfmt(e.get("date"), False))}{yr}</div><b>{esc(e["title"])}</b></a>'


def slider_ctl(cls='ctl-row'):
    btns = f'<button class="nb" data-prev aria-label="Назад">{icon("chl")}</button><button class="nb" data-next aria-label="Вперед">{icon("chr")}</button>'
    return f'<div class="ctl-row"><div class="nav-btns">{btns}</div></div>' if cls == 'ctl-row' else f'<div class="ctl">{btns}</div>'


# ---------------- главная (порядок блоков как на deloros.ru) ----------------
def build_home():
    news, events, team, projects, sections = D['news'], D['events'], D['team'], D['projects'], D['sections']
    pr = {p['id']: p for p in projects}
    up = sorted([e for e in events if e['upcoming']], key=lambda e: e.get('date') or '9')
    # баннер
    slides = [f'''<div class="ban ban-brand"><div class="t"><img class="logo-w" src="{L('/assets/logo.png')}" alt="Деловая Россия. Пермский край"><span>Пермское краевое региональное отделение общероссийской общественной организации «Деловая Россия». С 2004 года объединяет предпринимателей Прикамья.</span><a class="bt" href="{L('/organization/how-to-join/')}">Вступить в организацию</a></div></div>''']
    for e in up[:2]:
        g = e.get('gallery') or []
        if g:
            slides.append(f'<a class="ban shade" href="{L(path_of(e["url"]))}"><img class="bg" src="{img(g[0], 1600)}" alt=""><div class="t"><b>{esc(e["title"])}</b><span>{esc(e.get("date_text") or "")}</span><span class="bt">Подробнее</span></div></a>')
    if pr.get('154', {}).get('img'):
        slides.append(f'<a class="ban shade" href="{L("/projects/154/")}"><img class="bg" src="{img(pr["154"]["img"], 1600)}" alt=""><div class="t"><b>{esc(pr["154"]["title"])}</b><span>Проект отделения</span><span class="bt">Подробнее</span></div></a>')
    intro = f'<section class="intro"><div class="c"><div class="slider" data-slider data-auto="7000"><div class="track">{"".join(slides)}</div>{slider_ctl("ctl")}</div></div></section>'
    # новости
    withpic = [n for n in news if n.get('pic')]
    feat = withpic[:5]
    fi = ''.join(f'<a class="fs{" on" if i == 0 else ""}" data-fi href="{nhref(n)}"{ntarget(n)}><img src="{img(n["pic"], 960)}" alt=""></a>' for i, n in enumerate(feat))
    fs = ''.join(f'<div class="fs{" on" if i == 0 else ""}" data-ft><a href="{nhref(n)}"{ntarget(n)}><small>{dnum(n.get("date"))}</small><h3>{esc(n["title"])}</h3></a></div>' for i, n in enumerate(feat))
    dots = ''.join(f'<i{" class=on" if i == 0 else ""} data-dot="{i}"></i>' for i in range(len(feat)))
    cards = ''.join(f'<a class="nc" href="{nhref(n)}"{ntarget(n)}><h3>{esc(n["title"])}</h3><small>{dnum(n.get("date"))}</small><div class="im">{pic_tag(n["pic"], 640)}</div></a>' for n in withpic[5:11])
    news_sec = f'''<section class="sec"><div class="c"><div class="sh"><h2>Новости</h2></div>
<div class="feat" data-feat><div class="ph">{fi}</div><div class="tx">{fs}<div class="ctl"><div class="nav-btns"><button class="nb" data-fprev aria-label="Назад">{icon("chl")}</button><button class="nb" data-fnext aria-label="Вперед">{icon("chr")}</button></div><div class="dots">{dots}</div></div></div></div>
<div class="ncards">{cards}</div><div style="margin-top:32px"><a class="more" href="{L('/news/')}">Все новости {icon('right')}</a></div></div></section>'''
    # анонсы
    past = [e for e in events if not e['upcoming'] and e['local']]
    an_items = up + past[:max(0, 4 - len(up))]
    an = ''.join(f'<a class="an" href="{L(path_of(e["url"]))}"><div class="d">{esc(e.get("date_text") or "")}</div><div class="t">{esc(e["title"])}</div><div class="lb">{"Только для членов сообщества" if e["closed"] else "Открытое мероприятие"}{"" if e["upcoming"] else " · прошло"}</div></a>' for e in an_items)
    an_sec = f'''<section class="sec soft"><div class="c"><div class="sh"><h2>Анонсы</h2><a class="more" href="{L('/events/')}">Смотреть все мероприятия {icon('right')}</a></div>
<div class="slider" data-slider><div class="track">{an}</div></div></div></section>'''
    # слово председателя
    by = {p['name'].split()[-1]: p for p in team}
    qs = []
    for n in news:
        for sur in ('Теплов', 'Протопопов'):
            if sur in n['title'] and sur in by and len(qs) < 8:
                qs.append((n, by[sur]))
                break
    q_html = ''.join(f'<a class="qt" href="{nhref(n)}"{ntarget(n)}><div class="av">{pic_tag(p.get("photo") or p.get("photo_big"), 400, p["name"])}</div><div><div class="q">“</div><small>{dnum(n.get("date"))}</small><h3>{esc(n["title"])}</h3><div class="who">{esc(p["name"])}, {esc((p.get("role") or "").lower())}</div></div></a>' for n, p in qs)
    q_sec = f'''<section class="sec"><div class="c"><div class="sh"><h2>Слово председателя</h2><a class="more" href="{L('/organization/team/rukovodstvo/')}">Руководство отделения {icon('right')}</a></div>
<div class="slider" data-slider><div class="track">{q_html}</div>{slider_ctl()}</div></div></section>''' if qs else ''
    # пресс-центр
    tabs = [('all', 'Все события', news, '/news/')] + [(k, v, [n for n in news if n['cat'] == k], f'/news/{k}/') for k, v in CATS.items()]
    tb = ''.join(f'<button class="{"on" if i == 0 else ""}" data-tab="{k}">{t}</button>' for i, (k, t, _, _) in enumerate(tabs))
    panes = ''
    for i, (k, t, items, href) in enumerate(tabs):
        rows = ''.join(f'<a class="pr" href="{nhref(n)}"{ntarget(n)}><div class="im">{pic_tag(n.get("pic"), 320)}</div><b><small>{dnum(n.get("date"))}</small>{esc(n["title"])}</b></a>' for n in items[:6])
        panes += f'<div class="tpane{" on" if i == 0 else ""}" data-pane="{k}"><a class="more" href="{L(href)}">К новостям раздела {icon("right")}</a><div class="pl">{rows}</div></div>'
    pc_sec = f'<section class="sec soft"><div class="c"><div class="sh"><h2>Пресс-центр</h2></div><div data-tabs><div class="tabs">{tb}</div>{panes}</div></div></section>'
    # направления
    own = lambda sec: len([it for it in sections[sec] if is_own(it['url']) and path_of(it['url']).startswith(f'/{sec}/') and path_of(it['url']) != f'/{sec}/'])
    nc, nb, nk = own('commissions'), own('boards'), own('clubs')
    act = [p for p in projects if p['active']]
    dcs = [('Комитеты', f'{nc} {plural(nc, "отраслевой комитет", "отраслевых комитета", "отраслевых комитетов")} отделения', '/commissions/'),
           ('Советы и рабочие группы', f'{nb} {plural(nb, "совет", "совета", "советов")} и рабочих групп при органах власти, где работают делороссы', '/boards/'),
           ('Клубы', f'{nk} {plural(nk, "клуб", "клуба", "клубов")} по интересам', '/clubs/'),
           ('Проекты', f'{len(act)} {plural(len(act), "действующий проект", "действующих проекта", "действующих проектов")} отделения', '/projects/')]
    dc = ''.join(f'<div class="dc"><span class="geo"></span><h3>{t}</h3><p>{d}</p><a class="bt" href="{L(h)}">Перейти</a></div>' for t, d, h in dcs)
    sl = ''.join(f'<div class="sl"><img src="{img(pr[i]["img"], 1200)}" alt="" loading="lazy"><h3>{esc(pr[i]["title"])}</h3><a class="bt" href="{L(f"/projects/{i}/")}" style="margin-top:auto">Перейти</a></div>' for i in PRIORITY if i in pr and pr[i].get('img'))
    dir_sec = f'''<section class="sec"><div class="c"><div class="sh"><h2>Направления</h2></div><div class="dir">{dc}
<div class="dc wide"><div class="slider" data-slider style="height:100%"><div class="track">{sl}</div>{slider_ctl("ctl")}</div></div></div></div></section>'''
    # полезное
    use = [(BOOK, pr.get('154', {}).get('img'), 'Книга «Предприниматели и меценаты Прикамья»', ''),
           (L('/projects/155/'), pr.get('155', {}).get('img'), 'Гид инвестора', ''),
           (L('/organization/how-to-join/'), None, 'Как вступить в «Деловую Россию»', ' red'),
           (L('/organization/docs/'), None, 'Устав, положение о членстве, пакет документов', ''),
           (TG, None, 'Telegram-канал отделения', '')]
    us = ''
    for h, im, t, cls in use:
        pic = pic_tag(im, 480) if im else f'<img src="{L("/assets/logo.png")}" alt="" style="object-fit:contain;padding:16px">'
        us += f'<a class="use{cls}" href="{h}"{" target=_blank rel=noopener" if h.startswith("http") else ""}><div class="im">{pic}</div><span>{t}</span></a>'
    use_sec = f'''<section class="sec" style="padding-top:0"><div class="c"><div class="sh"><h2>Полезное</h2></div><p class="sub2">Материалы и сервисы отделения</p>
<div class="slider" data-slider><div class="track">{us}</div>{slider_ctl()}</div></div></section>'''
    layout('/', 'Главная', intro + news_sec + an_sec + q_sec + pc_sec + dir_sec + use_sec,
           desc='Пермское краевое региональное отделение «Деловой России»: новости, мероприятия, комитеты, проекты, вступление в организацию.', active='/')


# ---------------- пресс-центр, мероприятия, поиск ----------------
def build_news():
    news = D['news']
    per = 20
    lists = [('/news/', 'Новости', news)] + [(f'/news/{k}/', v, [n for n in news if n['cat'] == k]) for k, v in CATS.items()]
    menu = [('Все новости', '/news/')] + [(v, f'/news/{k}/') for k, v in CATS.items()]
    for base, title, items in lists:
        pages = max(1, (len(items) + per - 1) // per)
        for i in range(pages):
            path = base if i == 0 else f'{base}page-{i + 1}/'
            content = search_panel() + '<div class="rows">' + ''.join(news_row(n) for n in items[i * per:(i + 1) * per]) + '</div>' + pager(base, i, pages)
            crumbs = [('Пресс-центр', '/news/')] + ([(title, None)] if base != '/news/' else [])
            inner(path, title, crumbs, content, aside=wm(menu, base) + wg_events(), desc='Новости Пермского отделения «Деловой России».', active='/news/')
    for n in news:
        if not n['local']:
            continue
        g = n.get('gallery') or []
        cover = n.get('thumb') or (g[0] if g else None)
        intro = f'<p class="lead">{esc(n["intro"])}</p>' if n.get('intro') else ''
        tag = f'<a class="tg" href="{L("/news/" + n["cat"] + "/")}">{CATS[n["cat"]]}</a>' if n['cat'] in CATS else ''
        content = f'<div class="meta"><span>{dfmt(n.get("date"))}</span>{tag}</div>' + \
            (f'<div class="cover"><img src="{img(cover, 1200)}" alt=""></div>' if cover else '') + f'<div class="txt">{intro}{body_html(n.get("body"))}</div>' + gallery([u for u in g if u != cover])
        crumbs = [('Пресс-центр', '/news/')] + ([(CATS[n['cat']], f'/news/{n["cat"]}/')] if n['cat'] in CATS else [])
        inner(path_of(n['url']), n['title'], crumbs, content, desc=n.get('desc') or n.get('intro') or strip_tags(n.get('body'))[:180], active='/news/')


def build_events():
    events = D['events']
    up = sorted([e for e in events if e['upcoming']], key=lambda e: e.get('date') or '9')
    past = [e for e in events if e['local'] and not e['upcoming'] and (e.get('date') or '') <= TODAY]
    items = up + past
    per = 25
    pages = max(1, (len(items) + per - 1) // per)
    for i in range(pages):
        path = '/events/' if i == 0 else f'/events/page-{i + 1}/'
        content = search_panel() + '<div class="rows">' + ''.join(ev_row(e) for e in items[i * per:(i + 1) * per]) + '</div>' + pager('/events/', i, pages)
        if i == pages - 1:
            content += f'<p class="note" style="margin-top:24px">Мероприятия до {dfmt(EVENTS_FROM)} в <a href="{ORIG}/events/?archive=y" target="_blank" rel="noopener" style="color:var(--blue)">архиве текущего сайта</a>.</p>'
        inner(path, 'Мероприятия', [('Мероприятия', None)], content, aside=wg_news(), desc='Анонсы и прошедшие мероприятия Пермского отделения «Деловой России».', active='/events/')
    for e in events:
        if not e['local']:
            continue
        g = e.get('gallery') or []
        when = esc(e.get('date_text') or '') + (f' {e["date"][:4]}' if e.get('date') else '')
        act = ''
        if e['upcoming']:
            act = f'<div class="btns" style="margin-top:32px"><a class="btn" href="{L("/organization/how-to-join/")}">{"Вступить в организацию" if e["closed"] else "Подать заявку на участие"}</a></div>'
        content = f'<div class="meta"><span>{when}</span></div>' + (f'<div class="cover"><img src="{img(g[0], 1200)}" alt=""></div>' if g else '') + \
            f'<div class="txt">{body_html(e.get("body"))}</div>' + gallery(g[1:]) + act
        inner(path_of(e['url']), e['title'], [('Мероприятия', '/events/')], content, desc=e.get('desc') or strip_tags(e.get('body'))[:180], active='/events/')


def build_search():
    idx = [[n['title'], n.get('date') or '', nhref(n), 0 if n['local'] else 1, CATS.get(n['cat'], '')] for n in D['news']]
    idx += [[e['title'], e.get('date') or '', L(path_of(e['url'])), 0, 'Мероприятия'] for e in D['events'] if e['local']]
    idx += [[p['title'], '', L(f'/projects/{p["id"]}/'), 0, 'Проекты'] for p in D['projects']]
    idx += [[p['name'] + ', ' + (p.get('role') or ''), '', L(path_of(p['url'])), 0, 'Лица'] for p in D['team']]
    for sec, lbl in (('commissions', 'Комитеты'), ('clubs', 'Клубы'), ('boards', 'Советы')):
        idx += [[it['title'], '', L(path_of(it['url'])), 0, lbl] for it in D['sections'][sec] if is_own(it['url'])]
    json.dump(idx, open(os.path.join(OUT, 'assets', 'search.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    inner('/search/', 'Поиск по сайту', [('Поиск', None)], search_panel() + '<p class="note" data-sinfo></p><div class="rows" data-results></div>', desc='Поиск по сайту.')


# ---------------- лица ----------------
def grp_of(p):
    r = (p.get('role') or '').lower()
    if r.startswith('председатель отделения') or r.startswith('сопредседатель'):
        return 'rukovodstvo'
    if 'директор' in r or 'менеджер' in r or 'руководитель проектов' in r:
        return 'direkciya'
    if 'регионального совета' in r or 'почетный' in r:
        return 'sovet'
    if 'лидер комитета' in r:
        return 'lidery'
    return 'chleny'


def build_team():
    team = D['team']
    boxes = ''
    for t, h, k in TEAM_GROUPS:
        n = len([p for p in team if grp_of(p) == k])
        boxes += f'<a class="box" href="{L(h)}">{t}<small>{n} {plural(n, "человек", "человека", "человек")}</small></a>'
    boxes += f'<a class="box" href="{L("/organization/experts/")}">Эксперты</a>'
    inner('/organization/team/', 'Лица Пермского отделения', [('Лица', None)], f'<div class="boxes">{boxes}</div>',
          aside=wg_news('Слово председателя', news_about(['Теплов', 'Протопопов'])) + wg_events(), desc='Руководство, дирекция, региональный совет и члены Пермского отделения «Деловой России».', active='/organization/team/')
    for t, h, k in TEAM_GROUPS:
        ps = [p for p in team if grp_of(p) == k]
        inner(h, t, [('Лица', '/organization/team/'), (t, None)], f'<div class="people">{"".join(person(p) for p in ps)}</div>',
              aside=wm(TEAM_MENU, h) + wg_news(), desc=f'{t} Пермского отделения «Деловой России».', active='/organization/team/')
    for p in team:
        ph = p.get('photo_big') or p.get('photo')
        bio = re.sub(r'[\w.+-]+@[\w-]+\.[\w.]+', '', body_html(p.get('bio')))
        g = [x for x in TEAM_GROUPS if x[2] == grp_of(p)][0]
        content = f'<div class="prof"><div>{pic_tag(ph, 640, p["name"])}</div><div><div class="role">{esc(p.get("role") or "Член «Деловой России»")}</div><div class="txt">{bio}</div></div></div>'
        inner(path_of(p['url']), p['name'], [('Лица', '/organization/team/'), (g[0], g[1])], content,
              aside=wm(TEAM_MENU, g[1]) + wg_news(), desc=p.get('desc') or f'{p["name"]}, {p.get("role", "")}', active='/organization/team/')


# ---------------- комитеты, клубы, советы, партнеры ----------------
SEC_META = {'commissions': ('Комитеты', 'Лидер', 'factory', ['комитет']),
            'clubs': ('Клубы', 'Лидер', 'coffee', ['клуб']),
            'boards': ('Советы и рабочие группы', 'Представитель отделения', 'scale', ['совет', 'рабоч'])}


def build_sections():
    for sec, (title, who, ic, words) in SEC_META.items():
        items = [it for it in D['sections'][sec] if is_own(it['url']) and path_of(it['url']).startswith(f'/{sec}/') and path_of(it['url']) != f'/{sec}/']
        rows = ''
        for it in items:
            it['_body'], it['_slugs'] = split_team(it.get('body') or '')
            lead = next((D['team_by_slug'][s]['name'] for s in it['_slugs'] if s in D['team_by_slug']), '')
            rows += f'<a class="row ic" href="{L(path_of(it["url"]))}"><div class="i">{icon(ic)}</div><div><b>{esc(it["title"])}</b>{f"<small>{who}: {esc(lead)}</small>" if lead else ""}</div></a>'
        aside = wg_news(f'Новости: {title.lower()}', news_about(words)) + wg_events()
        inner(f'/{sec}/', title, [(title, None)], f'<div class="rows">{rows}</div>', aside=aside, desc=f'{title} Пермского отделения «Деловой России».', active=f'/{sec}/')
        for it in items:
            content = f'<div class="txt">{body_html(it["_body"])}</div>' + gallery(it.get('gallery') or []) + people_block(it['_slugs'], 'Представители отделения' if sec == 'boards' else who)
            inner(path_of(it['url']), it['title'], [(title, f'/{sec}/')], content, aside=aside, desc=it.get('desc') or strip_tags(it['_body'])[:180], active=f'/{sec}/')
    rows = ''
    for it in D['sections']['organization/partners']:
        h, t = partner_href(it)
        rows += f'<a class="row" href="{h}"{t}><div class="im" style="display:flex;align-items:center;justify-content:center;background:#fff">{pic_tag(it.get("img"), 320, "", " style=object-fit:contain;max-height:72px")}</div><div><b>{esc(it["title"])}</b></div></a>'
        if not t:
            inner(path_of(it['url']), it['title'], [('О нас', '/organization/about/'), ('Партнеры', '/organization/partners/')], f'<div class="txt">{body_html(it.get("body"))}</div>' + gallery(it.get('gallery') or []),
                  aside=wm(ABOUT_MENU, '/organization/partners/') + wg_news(), desc=it.get('desc') or it['title'], active='/organization/about/')
    inner('/organization/partners/', 'Партнеры', [('О нас', '/organization/about/'), ('Партнеры', None)], f'<div class="rows">{rows}</div>',
          aside=wm(ABOUT_MENU, '/organization/partners/') + wg_news(), desc='Партнеры Пермского отделения «Деловой России».', active='/organization/about/')


# ---------------- проекты ----------------
def build_projects():
    projects = D['projects']

    def tile(p):
        return f'<a class="tile" href="{L("/projects/" + p["id"] + "/")}"><b>{esc(p["title"])}</b><span class="hc">{pic_tag(p.get("img"), 480) or icon("rocket")}</span></a>'
    act, arc = [p for p in projects if p['active']], [p for p in projects if not p['active']]
    content = f'<div class="tiles">{"".join(tile(p) for p in act)}</div><h2 class="h2s">Завершенные проекты</h2><div class="tiles">{"".join(tile(p) for p in arc)}</div>'
    aside = wg_news('Новости проектов', news_about(['проект', 'альянс', 'экспортер', 'инвест'])) + wg_events()
    inner('/projects/', 'Проекты', [('Проекты', None)], content, aside=aside, desc='Проекты Пермского отделения «Деловой России».', active='/projects/')
    for p in projects:
        body, slugs = split_team(p.get('body') or '')
        kv = f'<dl class="kv"><dt>Статус</dt><dd>{"<span class=status>Действующий проект</span>" if p["active"] else "<span class=status arch>Завершен</span>"}</dd></dl>'
        btn = f'<div class="btns" style="margin-top:32px"><a class="btn" href="{L("/organization/how-to-join/")}">Участвовать в проекте</a></div>' if p['active'] else ''
        content = kv + f'<div class="txt">{body_html(body)}</div>' + gallery(p.get('gallery') or []) + people_block(slugs, 'Участники проекта') + btn
        inner(f'/projects/{p["id"]}/', p['title'], [('Проекты', '/projects/')], content, aside=aside, desc=p.get('desc') or strip_tags(body)[:180], active='/projects/')


# ---------------- возможности ----------------
PREMIUM_DROP = r'кальян|саун|частных самол|вертол|элит|миллионер|яхт|квадроцикл|экстрим'


def svc_title(s):
    return tidy(re.sub(r'Член\s+Деловой России/', '', s)).strip()


def price_of(k):
    return {'/services/package-of-documents/chlen-delovoy-rossii/': '100 000 ₽ в год', '/services/package-of-documents/chlen-delovoy-rossii-paket-premium/': '190 000 ₽ в год'}.get(k, '')


def build_services():
    pages = D['pages']
    menu = [(t, h) for h, t, _ in SERVICE_GROUPS]
    tiles = ''.join(f'<a class="tile" href="{L(h)}"><b>{t}</b><span class="hc">{icon(ic)}</span></a>' for h, t, ic in SERVICE_GROUPS)
    inner('/services/', 'Возможности', [('Возможности', None)], f'<div class="tiles">{tiles}</div>', aside=wm(menu, None) + wg_news(), desc='Возможности для членов Пермского отделения «Деловой России».', active='/services/')
    for k, v in pages.items():
        if not k.startswith('/services/') or k == '/services/' or '?' in k:
            continue
        grp = next(((h, t) for h, t, _ in SERVICE_GROUPS if k.startswith(h)), ('/services/', 'Возможности'))
        kids = [(kk, vv) for kk, vv in pages.items() if kk.startswith(k) and kk != k and '?' not in kk and kk.count('/') == k.count('/') + 1]
        if kids:
            content = '<div class="rows">' + ''.join(f'<a class="row ic" href="{L(kk)}"><div class="i">{icon("file")}</div><div><b>{esc(svc_title(vv["title"]))}</b>{f"<small>{price_of(kk)}</small>" if price_of(kk) else ""}</div></a>' for kk, vv in kids) + '</div>'
        else:
            b = body_html(v.get('body'))
            if k.endswith('/chlen-delovoy-rossii-paket-premium/'):
                b = re.sub(r'<li>(?:(?!</li>).)*?(' + PREMIUM_DROP + r')(?:(?!</li>).)*</li>', '', b, flags=re.I | re.S)
            pr = price_of(k)
            content = (f'<p style="font-size:22px;font-weight:700;color:var(--blue)">{pr}</p>' if pr else '') + f'<div class="txt">{b}</div>'
            if '/package-of-documents/' in k:
                content += f'<div class="btns" style="margin-top:32px"><a class="btn" href="{L("/organization/how-to-join/")}">Вступить в организацию</a><a class="btn ghost" href="#pay" data-pay>Оплатить взнос</a></div>'
        crumbs = [('Возможности', '/services/')] + ([(grp[1], grp[0])] if grp[0] != k else [])
        inner(k, svc_title(v['title']), crumbs, content, aside=wm(menu, grp[0]) + wg_news(), desc=v.get('desc') or strip_tags(v.get('body'))[:180], active='/services/')


# ---------------- о нас ----------------
def doc_link(href, title, kind):
    return f'<a class="doc" href="{esc(href)}" target="_blank" rel="noopener"><span class="i">{icon("file")}</span><span>{title}</span><small>{kind}</small></a>'


def build_about():
    pages = D['pages']
    for k in ['/organization/about/', '/organization/perm-region/', '/organization/requisites/']:
        v = pages[k]
        b = re.sub(r'<p>\s*Контакты\s*</p>\s*$', '', body_html(v['body']))
        crumbs = [('О нас', None)] if k == '/organization/about/' else [('О нас', '/organization/about/'), (v['title'], None)]
        inner(k, v['title'], crumbs, f'<div class="txt">{b}</div>', aside=wm(ABOUT_MENU, k) + wg_news(), desc=v.get('desc') or strip_tags(v['body'])[:180], active='/organization/about/')
    v = pages['/organization/experts/']
    inner('/organization/experts/', 'Эксперты', [('Лица', '/organization/team/'), ('Эксперты', None)], f'<div class="txt">{body_html(v["body"])}</div>',
          aside=wm(TEAM_MENU, '/organization/experts/') + wg_news(), desc='Эксперты Пермского отделения «Деловой России».', active='/organization/team/')
    # документы
    b = body_html(pages['/organization/docs/']['body'])
    b = re.sub(r'<p>\s*<a href="([^"]+)"[^>]*>\s*([^<]+?)\s*</a>\s*([\d.,]+\s*[КМ]б)?\s*</p>', lambda m: doc_link(html.unescape(m.group(1)), m.group(2), (m.group(3) or '').strip()), b)
    content = f'''<h2 class="h2s" style="margin-top:0">Вступление</h2><div class="docs">{doc_link(DOC_JOIN, 'Пакет документов на вступление', 'DOCX')}{doc_link(DOC_POL, 'Положение о членстве от 27.01.2025', 'PDF')}{doc_link(DOC_USTAV, 'Устав отделения от 03.09.2019', 'PDF')}</div>
<div class="txt">{b}</div>'''
    inner('/organization/docs/', 'Документы', [('О нас', '/organization/about/'), ('Документы', None)], content, aside=wm(ABOUT_MENU, '/organization/docs/') + wg_news(), desc='Документы Пермского отделения «Деловой России».', active='/organization/about/')
    # контакты
    content = f'''<div class="ct"><div><small>Адрес</small><b>{ADDR}</b></div><div><small>Режим работы</small><b>Пн–пт 9:00–18:00, сб–вс выходной</b></div>
<div><small>Телефон</small><b><a href="{PHONE_HREF}">{PHONE}</a></b></div><div><small>E-mail</small><b><a href="mailto:{EMAIL}">{EMAIL}</a></b></div></div>
<div class="map"><iframe title="Карта" loading="lazy" src="https://yandex.ru/map-widget/v1/?text={esc('Пермь, улица Революции, 20')}&amp;z=16"></iframe></div>
<h2 class="h2s">Написать сообщение</h2>
<form class="fm" data-form><label>Имя<input name="name" required autocomplete="name"></label><label>Телефон<input name="phone" type="tel" required autocomplete="tel"></label>
<label class="full">Сообщение<textarea name="msg" required></textarea></label>
<label class="chk full"><input type="checkbox" required> <span>Согласен на обработку персональных данных по <a href="{L('/privacy/')}" style="color:var(--blue)">политике</a></span></label>
<div class="full"><button class="btn">Отправить</button></div></form>'''
    inner('/contacts/', 'Контакты', [('О нас', '/organization/about/'), ('Контакты', None)], content, aside=wm(ABOUT_MENU, '/contacts/') + wg_news(), desc=f'{ADDR}, {PHONE}, {EMAIL}', active='/contacts/')
    v = pages.get('/include/licenses_detail.php')
    if v:
        inner('/privacy/', 'Политика обработки персональных данных', [('Политика обработки персональных данных', None)], f'<div class="txt">{body_html(v["body"])}</div>', desc='Политика обработки персональных данных.')
    build_join()


def build_join():
    b = body_html(D['pages']['/organization/how-to-join/']['body'])
    b = re.sub(r'<p>(?:(?!</p>).)*(Заполнить анкету|\(скачать\))(?:(?!</p>).)*</p>', '', b, flags=re.S)
    b = re.sub(r'<table>(?:(?!</table>).)*Заполнить анкету(?:(?!</table>).)*</table>', '', b, flags=re.S)
    b = re.split(r'<p>\s*Пакет документов на вступление', b)[0]

    def first(k):
        v = D['pages'].get(k)
        if not v:
            return ''
        t = strip_tags(clean_body(v.get('body', '')))
        return t if len(t) < 220 else t[:220].rsplit(' ', 1)[0] + '…'
    base_u, prem_u = '/services/package-of-documents/chlen-delovoy-rossii/', '/services/package-of-documents/chlen-delovoy-rossii-paket-premium/'
    nxt = icon('right')
    content = f'''<div data-join>
<div class="stp"><div class="on" data-st="1"><span>Информация о членстве</span><i>1</i></div><div data-st="2"><span>Пакеты членства</span><i>2</i></div><div data-st="3"><span>Личная информация</span><i>3</i></div></div>
<div class="step on" data-step="1"><span class="stl">Шаг 1 из 3</span><h2 class="h2s" style="margin-top:0">Информация о членстве</h2><div class="txt">{b}</div>
<div class="docs">{doc_link(DOC_JOIN, 'Пакет документов на вступление', 'DOCX')}{doc_link(DOC_USTAV, 'Устав организации', 'PDF')}{doc_link(DOC_POL, 'Положение о членстве', 'PDF')}</div>
<label class="chk"><input type="checkbox" data-agree> С информацией ознакомлен</label><button class="btn" data-go="2" disabled>К выбору пакета членства {nxt}</button></div>
<div class="step" data-step="2"><span class="stl">Шаг 2 из 3</span><h2 class="h2s" style="margin-top:0">Пакеты членства</h2>
<div class="pk"><label class="pkc"><input type="radio" name="pkg" value="Базовый" checked><b>«Базовый»</b><div class="pr2">100 000 ₽ <small>в год</small></div><p>{esc(first(base_u))}</p><a href="{L(base_u)}" target="_blank">Подробнее о пакете</a></label>
<label class="pkc"><input type="radio" name="pkg" value="Премиум"><b>«Премиум»</b><div class="pr2">190 000 ₽ <small>в год</small></div><p>{esc(first(prem_u))}</p><a href="{L(prem_u)}" target="_blank">Подробнее о пакете</a></label></div>
<div class="btns"><button class="btn ghost" data-go="1">Назад</button><button class="btn" data-go="3">Далее {nxt}</button></div></div>
<div class="step" data-step="3"><span class="stl">Шаг 3 из 3</span><h2 class="h2s" style="margin-top:0">Личная информация</h2>
<form class="fm" data-form><input type="hidden" name="package"><input type="hidden" name="source">
<label>Фамилия и имя<input name="name" required autocomplete="name"></label><label>Телефон<input name="phone" type="tel" required autocomplete="tel"></label>
<label>Компания<input name="company" required autocomplete="organization"></label><label>Должность<input name="position" autocomplete="organization-title"></label>
<label class="full">E-mail<input name="email" type="email" autocomplete="email"></label>
<label class="chk full"><input type="checkbox" required> <span>Согласен на обработку персональных данных по <a href="{L('/privacy/')}" style="color:var(--blue)">политике</a></span></label>
<div class="full btns"><button type="button" class="btn ghost" data-go="2">Назад</button><button class="btn">Отправить заявку</button></div></form></div>
</div>'''
    inner('/organization/how-to-join/', 'Вступить в «Деловую Россию»', [('О нас', '/organization/about/'), ('Вступить в «Деловую Россию»', None)], content,
          desc='Условия членства, пакеты и заявка на вступление в Пермское отделение «Деловой России».', active='/organization/about/')
    redirect('/organization/kak-vstupit/', '/organization/how-to-join/')


def redirect(frm, to):
    f = os.path.join(OUT, frm.lstrip('/'), 'index.html')
    os.makedirs(os.path.dirname(f), exist_ok=True)
    open(f, 'w').write(f'<!doctype html><meta charset="utf-8"><meta name="robots" content="noindex"><meta http-equiv="refresh" content="0;url={L(to)}"><a href="{L(to)}">{L(to)}</a>')


def register():
    """Какие адреса будут в макете, чтобы ссылки в старых текстах вели на него."""
    g = GENERATED
    g.update({'/', '/news/', '/events/', '/search/', '/organization/team/', '/organization/experts/', '/projects/', '/services/', '/contacts/', '/privacy/',
              '/organization/about/', '/organization/perm-region/', '/organization/requisites/', '/organization/docs/', '/organization/partners/', '/organization/how-to-join/',
              '/commissions/', '/clubs/', '/boards/'})
    g.update(f'/news/{k}/' for k in CATS)
    g.update(h for _, h, _ in TEAM_GROUPS)
    g.update(path_of(n['url']) for n in D['news'] if n['local'])
    g.update(path_of(e['url']) for e in D['events'] if e['local'])
    g.update(path_of(p['url']) for p in D['team'])
    g.update(f'/projects/{p["id"]}/' for p in D['projects'])
    for sec in ('commissions', 'clubs', 'boards', 'organization/partners'):
        g.update(path_of(it['url']) for it in D['sections'][sec] if is_own(it['url']) and path_of(it['url']).startswith(f'/{sec}/'))
    g.update(k for k in D['pages'] if k.startswith('/services/') and '?' not in k)


def main():
    global NAV
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    shutil.copytree(os.path.join(HERE, 'assets'), os.path.join(OUT, 'assets'))
    load()
    NAV = build_nav()
    register()
    build_home(); build_news(); build_events(); build_search(); build_team(); build_sections()
    build_projects(); build_services(); build_about()
    for frm, to in [('/meropriyatiya/', '/events/'), ('/organization/', '/organization/about/'), ('/include/licenses_detail.php/', '/privacy/'),
                    ('/services/obshchie-uslugi/finansovyy-ekonomicheskiy-audit/', '/services/common-services/finansovyy-ekonomicheskiy-audit/'),
                    ('/services/package-of-documents/predsedatel-regionalnogo-otdeleniya/', '/services/package-of-documents/')]:
        redirect(frm, to)
    inner('/404.html', 'Страница не найдена', [('Страница не найдена', None)], f'<p>Возможно, адрес изменился. <a href="{L("/")}" style="color:var(--blue)">На главную</a></p>')
    open(os.path.join(OUT, 'robots.txt'), 'w').write('User-agent: *\nDisallow: /\n')
    open(os.path.join(OUT, '.nojekyll'), 'w').write('')
    bad = run_images()
    if bad:
        alt = '|'.join(re.escape(b) for b in bad)
        for root, _, files in os.walk(OUT):
            for fn in files:
                if fn.endswith('.html'):
                    fp = os.path.join(root, fn)
                    t = open(fp, encoding='utf-8').read()
                    t2 = re.sub(r'<a href="[^"]*/img/(' + alt + r')"[^>]*>.*?</a>', '', t)
                    t2 = re.sub(r'<img src="[^"]*/img/(' + alt + r')"[^>]*>', '', t2)
                    if t2 != t:
                        open(fp, 'w', encoding='utf-8').write(t2)
    print('страниц:', sum(len([f for f in fs if f.endswith('.html')]) for _, _, fs in os.walk(OUT)))


if __name__ == '__main__':
    main()

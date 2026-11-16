#!/usr/bin/env python3
"""Đường dẫn phân cấp (breadcrumb): chữ hiện trên trang VÀ schema BreadcrumbList sinh từ CÙNG MỘT danh sách, nên không bao giờ lệch nhau.

Nằm ngay dưới thanh menu, trên H1:  Trang chủ › Đánh giá › Bybit.  Trên điện thoại (<=640px) chỉ hiện một nút quay lại "‹ Đánh giá"
(bản đầy đủ vẫn nằm trong schema). Trang chủ và 404 không có.
  python3 tools/breadcrumb.py            # gắn/cập nhật cho mọi trang trong repo (chạy lại bao nhiêu lần cũng được)
  python3 tools/breadcrumb.py --check    # chỉ kiểm tra, thoát mã 1 nếu có trang thiếu hoặc lệch
Các nơi sinh trang tự gọi apply(): tools/seo_head.py (trang Việt), tools/en_pages.py (trang Anh), tools/news/publish.py (bài, danh sách, phân trang)."""
import html, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SITE = json.load(open(os.path.join(HERE, 'news', 'config.json')))['site'].rstrip('/')
INTRO = json.load(open(os.path.join(HERE, 'seo_intro.json'), encoding='utf-8'))

# khoá -> (nhãn Việt, nhãn Anh, địa chỉ Việt, địa chỉ Anh)
P = {
    'home':    ('Trang chủ', 'Home', '/', '/en'),
    'tools':   ('Công cụ', 'Tools', '/cong-cu', '/en/tools'),
    'chart':   ('Biểu đồ', 'Chart', '/bieu-do', '/en/chart-calculator'),
    'conv':    ('Quy đổi', 'Converter', '/quy-doi', '/en/converter'),
    'rank':    ('Xếp hạng', 'Rankings', '/xep-hang', '/en/rankings'),
    'compare': ('So sánh', 'Compare', '/so-sanh', '/en/compare'),
    'reviews': ('Đánh giá', 'Reviews', '/danh-gia', '/en/reviews'),
    'news':    ('Tin tức', 'News', '/tin-tuc', '/en/news'),
    'learn':   ('Kiến thức', 'Learn', '/kien-thuc', '/en/learn'),
    'about':   ('Về chúng tôi', 'About', '/ve-chung-toi', '/en/about'),
    'risk':    ('Miễn trừ rủi ro', 'Risk disclaimer', '/mien-tru-rui-ro', '/en/risk-disclaimer'),
}
# trang cố định (đường dẫn file không .html) -> (khoá trang, khoá cha)
FIXED = {'cong-cu': ('tools', None), 'bieu-do': ('chart', 'tools'), 'quy-doi': ('conv', 'tools'), 'xep-hang': ('rank', None),
         'so-sanh': ('compare', None), 'danh-gia': ('reviews', None), 'tin-tuc': ('news', None), 'kien-thuc': ('learn', None),
         've-chung-toi': ('about', None), 'mien-tru-rui-ro': ('risk', None)}
EN_FIXED = {P[k][3][1:]: k for k in P if k != 'home'}          # 'en/rankings' -> 'rank'
EN_FIXED['en/news'] = 'news'; EN_FIXED['en/learn'] = 'learn'
VI_FIXED = {P[k][2][1:]: k for k in P if k != 'home'}
TXT = {'vi': ('Đường dẫn', 'Quay lại', 'Trang %d'), 'en': ('Breadcrumb', 'Back', 'Page %d')}
LI = {'vi': 0, 'en': 1}
ART_DIRS = {'tin-tuc': ('news', 'vi'), 'kien-thuc': ('learn', 'vi'), 'en/news': ('news', 'en'), 'en/learn': ('learn', 'en')}

CSS = ('/*bc*/.bc{margin:26px 0 -12px;font-size:12.5px;line-height:1.4;font-family:var(--sans,inherit)}'
       '.bc ol{display:flex;flex-wrap:nowrap;align-items:center;margin:0;padding:0;list-style:none;min-width:0}'
       '.bc li{display:flex;align-items:center;flex:none;white-space:nowrap;color:var(--muted)}'
       '.bc li+li::before{content:"\\203A";margin:0 8px;opacity:.7}'
       '.bc li:last-child{flex:0 1 auto;min-width:0}'
       '.bc li a,.bc li span{display:block;margin:0;padding:0;font:inherit;line-height:1.4}.bc a{color:var(--muted);text-decoration:none;border-radius:4px}'
       '.bc a:hover{color:var(--accent);text-decoration:underline;text-underline-offset:3px}'
       '.bc a:focus-visible{outline:2px solid var(--accent);outline-offset:2px}'
       '.bc [aria-current]{color:var(--text);overflow:hidden;text-overflow:ellipsis}'
       '.bc .bcb{display:none}'
       '@media (max-width:640px){.bc{margin-top:21px;margin-bottom:-13px}.bc ol{display:none}.bc .bcb{display:inline-flex;align-items:center;min-height:32px;padding-right:12px}}/*/bc*/')
CSS_RE = re.compile(r'/\*bc\*/.*?/\*/bc\*/', re.S)
NAV_RE = re.compile(r'\n?<nav class="bc"[^>]*>.*?</nav>', re.S)
LD_RE = re.compile(r'\n?<script type="application/ld\+json" id="bc-ld">.*?</script>', re.S)


def esc(s): return html.escape(s, quote=True)


def _text(h): return html.unescape(re.sub(r'<[^>]+>', '', h)).strip()


def trail_for(rel, text):
    """rel: đường dẫn file so với gốc repo (vd 'danh-gia-bybit.html'). Trả về (ngôn ngữ, [(nhãn, địa chỉ hoặc None)]) hoặc None nếu trang không có breadcrumb."""
    p = rel[:-5] if rel.endswith('.html') else rel
    if p in ('index', 'en/index', '404'): return None
    lg = 'en' if p.startswith('en/') else 'vi'
    i = LI[lg]
    home = (P['home'][i], P['home'][2 + i])

    def pg(k): return (P[k][i], P[k][2 + i])
    if p in (EN_FIXED if lg == 'en' else VI_FIXED):
        k = (EN_FIXED if lg == 'en' else VI_FIXED)[p]
        par = FIXED.get([f for f, v in FIXED.items() if v[0] == k][0], (None, None))[1] if k in [v[0] for v in FIXED.values()] else None
        out = [home] + ([pg(par)] if par else []) + [(P[k][i], None)]
        return lg, out
    m = re.match(r'(?:en/reviews/|danh-gia-)([a-z0-9-]+)$', p)
    if m and m.group(1) in INTRO:
        return lg, [home, pg('reviews'), (INTRO[m.group(1)][0], None)]
    m = re.match(r'(.+)/([^/]+)$', p)
    if m and m.group(1) in ART_DIRS:
        kind, _ = ART_DIRS[m.group(1)]
        n = re.match(r'(?:trang|page)-(\d+)$', m.group(2))
        if n: return lg, [home, pg(kind), (TXT[lg][2] % int(n.group(1)), None)]
        h = re.search(r'<h1[^>]*>(.*?)</h1>', text, re.S)
        if not h: return None
        return lg, [home, pg(kind), (_text(h.group(1)), None)]
    return None


def build(lg, trail, url):
    """(html của nav, json-ld). Mục cuối là trang hiện tại (không link trong chữ nhưng có trong schema)."""
    lis = []
    for k, (lab, href) in enumerate(trail):
        lis.append('<li><a href="%s">%s</a></li>' % (href, esc(lab)) if href else '<li><span aria-current="page">%s</span></li>' % esc(lab))
    par = trail[-2]
    nav = ('<nav class="bc" aria-label="%s"><ol>%s</ol><a class="bcb" href="%s">‹ %s</a></nav>' % (TXT[lg][0], ''.join(lis), par[1], esc(par[0])))
    items = [{"@type": "ListItem", "position": k + 1, "name": lab, "item": SITE + (href if href else url)} for k, (lab, href) in enumerate(trail)]
    items[0]['item'] = SITE + '/' if lg == 'vi' else SITE + '/en'
    ld = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": items}
    return nav, '<script type="application/ld+json" id="bc-ld">%s</script>' % json.dumps(ld, ensure_ascii=False).replace('</', '<\\/')


def apply(t, rel):
    """gắn (hoặc làm mới) breadcrumb cho nội dung t của file rel. Trang không thuộc diện thì trả nguyên."""
    r = trail_for(rel, t)
    t = NAV_RE.sub('', LD_RE.sub('', t))
    if r is None: return t
    lg, trail = r
    p = rel[:-5]
    url = SITE + '/' + p
    nav, ld = build(lg, trail, url)
    w = t.find('<div class="wrap">')          # đầu khung nội dung (header dùng chung nằm ngay trước, xem tools/header.py)
    assert w >= 0, rel + ': không thấy <div class="wrap">'
    e = w + len('<div class="wrap">')
    t = t[:e] + '\n' + nav + t[e:]
    if '<!--/seo-->' in t: t = t.replace('<!--/seo-->', ld + '\n<!--/seo-->', 1)
    else: t = t.replace('</title>', '</title>\n' + ld, 1)    # bài viết: đầu trang không có <!--seo--> và không đóng </head>
    if CSS_RE.search(t): t = CSS_RE.sub(lambda _: CSS, t, count=1)
    else:
        w = t.find('<div class="wrap">'); h = t.find('<!--chh-->')   # CSS vào <style> của trang, trước khối header (khối đó được dựng lại mỗi lần)
        h = h if 0 <= h < w else w
        i = t.rfind('</style>', 0, h)
        assert i >= 0, rel
        t = t[:i] + CSS + t[i:]
    return t


def all_pages():
    for d, dirs, files in os.walk(ROOT):
        dirs[:] = [x for x in dirs if x not in ('node_modules', '.git', '__pycache__', 'tools', 'functions', 'img')]
        for f in files:
            if f.endswith('.html'): yield os.path.relpath(os.path.join(d, f), ROOT).replace(os.sep, '/')


def verify(rel, text):
    """lỗi (list) của một trang: thiếu breadcrumb, hoặc chữ hiện và schema không khớp nhau"""
    if trail_for(rel, text) is None: return [] if not NAV_RE.search(text) else ['có breadcrumb ở trang không cần']
    n = NAV_RE.search(text); l = LD_RE.search(text)
    if not n or not l: return ['thiếu breadcrumb (chạy python3 tools/breadcrumb.py)']
    shown = [_text(x) for x in re.findall(r'<li>(.*?)</li>', n.group(0), re.S)]
    ld = json.loads(re.search(r'>(.*)</script>', l.group(0), re.S).group(1))
    names = [x['name'] for x in ld['itemListElement']]
    if shown != names: return ['breadcrumb: chữ hiện %r lệch schema %r' % (shown, names)]
    return []


if __name__ == '__main__':
    chk = '--check' in sys.argv; bad = []
    for rel in all_pages():
        fp = os.path.join(ROOT, rel); t = open(fp, encoding='utf-8').read()
        if chk:
            for e in verify(rel, t): bad.append('%s: %s' % (rel, e))
            continue
        n = apply(t, rel)
        if n != t: open(fp, 'w', encoding='utf-8').write(n); print('ok', rel)
    if chk:
        print('\n'.join(bad) if bad else 'Breadcrumb khớp ở mọi trang'); sys.exit(1 if bad else 0)

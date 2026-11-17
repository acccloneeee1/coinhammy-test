"""Sitemap, hai trang danh sách tiếng Anh và phân trang danh sách (trang 2 trở đi).
Tách từ publish.py; chạy từ thư mục gốc của kho (xem publish.py)."""

import json
import math
import os
import re
from datetime import datetime

from news_core import KINDS, ROOT, SITE, VN, die, esc, jload
import lang_boot
import breadcrumb
import header
import en_pages
import prerender_i18n


XH = ' xmlns:xhtml="http://www.w3.org/1999/xhtml"'
LISTS = {'tin-tuc.html': 'en/news.html', 'kien-thuc.html': 'en/learn.html'}   # trang danh sách Việt -> bản Anh
LISTS.update(en_pages.sitemap_alts())   # trang chính có bản Anh sinh từ bản Việt (tools/en_pages.py)


def sm_rows(vi, en, lastmod):
    """hai dòng sitemap (Việt + Anh), mỗi dòng khai báo cả hai bản"""
    alt = ('<xhtml:link rel="alternate" hreflang="vi" href="%s"/><xhtml:link rel="alternate" hreflang="en" href="%s"/>'
           '<xhtml:link rel="alternate" hreflang="x-default" href="%s"/>') % (vi, en, vi)
    return ['<url><loc>%s</loc><lastmod>%s</lastmod>%s</url>' % (loc, lastmod, alt) for loc in (vi, en)]


def sitemap(items):
    pages = ['', 'cong-cu.html', 'bieu-do.html', 'quy-doi.html', 'xep-hang.html', 'so-sanh.html', 'danh-gia.html', 'tin-tuc.html', 'kien-thuc.html',
             've-chung-toi.html', 'mien-tru-rui-ro.html'] + sorted(f for f in os.listdir(ROOT) if f.startswith('danh-gia-') and f.endswith('.html'))
    now = datetime.now(VN).strftime('%Y-%m-%d')
    clean = lambda p: p[:-5] if p.endswith('.html') else p   # URL sạch, khớp thẻ canonical
    rows = []
    for p in pages:
        if p in LISTS: rows += sm_rows('%s/%s' % (SITE, clean(p)), '%s/%s' % (SITE, clean(LISTS[p])), now)
        else: rows.append('<url><loc>%s/%s</loc><lastmod>%s</lastmod></url>' % (SITE, clean(p), now))
    rows += pg_sitemap_rows(now)   # trang 2 trở đi của danh sách tin / kiến thức
    lidx = jload(os.path.join(ROOT, 'hoc', 'index.json'), {'items': []})
    for pfx, its in (('tin', items), ('hoc', lidx['items'])):
        for x in its:
            rows += sm_rows(SITE + (x.get('u') or '/%s/%s' % (pfx, x['slug'])), SITE + x['ue'], x['ts'][:10])
    open(os.path.join(ROOT, 'sitemap.xml'), 'w', encoding='utf-8').write(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"%s>\n' % XH + '\n'.join(rows) + '\n</urlset>\n')
    # robots.txt chỉ tạo khi chưa có (đã có sẵn, trỏ Sitemap về tên miền chính)
    if not os.path.exists(os.path.join(ROOT, 'robots.txt')):
        open(os.path.join(ROOT, 'robots.txt'), 'w', encoding='utf-8').write('User-agent: *\nDisallow: /tools/\nAllow: /\nSitemap: %s/sitemap.xml\n' % SITE)


EN_LISTS = {'tin-tuc.html': ('en/news', 'Latest crypto news | CoinHammy', 'The latest crypto news, edited by CoinHammy and updated throughout the day: Bitcoin, ETFs, derivatives markets and the events that move crypto prices.'),
            'kien-thuc.html': ('en/learn', 'Futures trading guides | CoinHammy', 'One new guide a day: market mechanics and trading skills for futures traders, from risk management and position sizing to reading funding and open interest.')}


def en_list_page(vi_file):
    """trang danh sách tiếng Anh = bản sao của trang danh sách Việt (cùng giao diện, cùng mã) với đầu trang tiếng Anh; luôn sinh lại từ trang Việt để hai bản không lệch nhau"""
    path, title, desc = EN_LISTS[vi_file]
    t = open(os.path.join(ROOT, vi_file), encoding='utf-8').read()
    vi_path = '/' + vi_file[:-5]
    url, vurl = '%s/%s' % (SITE, path), SITE + vi_path
    blk = ('<!--seo-->\n<meta name="description" content="%s">\n<link rel="canonical" href="%s">\n%s\n<base href="/">\n'
           '<meta property="og:type" content="website">\n<meta property="og:site_name" content="CoinHammy">\n<meta property="og:locale" content="en_US">\n'
           '<meta property="og:locale:alternate" content="vi_VN">\n<meta property="og:title" content="%s">\n<meta property="og:description" content="%s">\n'
           '<meta property="og:url" content="%s">\n<meta property="og:image" content="%s/tin/og-default.png">\n<meta property="og:image:width" content="1200">\n'
           '<meta property="og:image:height" content="630">\n<meta name="twitter:card" content="summary_large_image">\n%s\n<!--/seo-->') % (
        esc(desc), url, lang_boot.hreflang(vurl, url), esc(title), esc(desc), url, SITE, lang_boot.boot('en', vi_path, '/' + path))
    t, n = re.subn(r'<title>.*?</title>\s*<!--seo-->.*?<!--/seo-->', lambda _: '<title>%s</title>\n%s' % (esc(title), blk), t, count=1, flags=re.S)
    assert n == 1, vi_file
    assert t.count('<html lang="vi">') == 1, vi_file
    t = t.replace('<html lang="vi">', '<html lang="en">')
    t = t.replace('<a href="#" aria-current="page"', '<a href="/%s" aria-current="page"' % path)
    t = pg_set_nav(t, 'news' if vi_file == 'tin-tuc.html' else 'learn', 'en') if '<!--pgn-->' in t else t
    t, _ = prerender_i18n.bake(path + '.html', en_pages.relink(t))   # nội dung điền sẵn (tools/i18n_baked.json) để trang Anh sinh ra vẫn có sẵn
    return path, header.apply(breadcrumb.apply(t, path + '.html'), path + '.html', 'en')


def en_lists(check=False):
    """ghi (hoặc chỉ kiểm tra) 2 trang danh sách tiếng Anh. check=True: trả về danh sách file đang lệch"""
    stale = []
    for vf in EN_LISTS:
        path, t = en_list_page(vf)
        fp = os.path.join(ROOT, path + '.html')
        cur = open(fp, encoding='utf-8').read() if os.path.isfile(fp) else None
        if cur != t:
            stale.append(path + '.html')
            if not check:
                os.makedirs(os.path.dirname(fp), exist_ok=True); open(fp, 'w', encoding='utf-8').write(t)
    return stale


# ---------------------------------------------------------------------------------------------------------------------
# PHÂN TRANG DANH SÁCH (từ 11/11/2026). Trang 1 = trang danh sách như cũ (tin-tuc.html, kien-thuc.html + bản Anh);
# trang 2 trở đi là trang tĩnh /tin-tuc/trang-N, /kien-thuc/trang-N, /en/news/page-N, /en/learn/page-N, mỗi trang PER_PAGE bài.
# Mục đích: bài cũ nào cũng có link <a href> thật từ một trang danh sách (Google không bấm nút "Xem thêm").
# Tự chạy sau mỗi lần đăng bài (after_publish); chạy tay: python3 tools/news/publish.py pages
PER_PAGE = 15   # khớp trang 1: 1 bài nổi bật + 5 tin mới + 9 thẻ
PG = {'news': {'vi': ('tin-tuc.html', 'tin-tuc', 'trang-%d'), 'en': ('en/news.html', 'en/news', 'page-%d')},
      'learn': {'vi': ('kien-thuc.html', 'kien-thuc', 'trang-%d'), 'en': ('en/learn.html', 'en/learn', 'page-%d')}}
# title trang 2+ = title trang 1 giữ nguyên, thêm đuôi số trang (anh Thái chốt 11/11/2026)
PG_TITLE = {('news', 'vi'): 'Tin tức crypto mới nhất - Trang %d | CoinHammy',
            ('news', 'en'): 'Latest crypto news - Page %d | CoinHammy',
            ('learn', 'vi'): 'Kiến thức giao dịch Futures - Trang %d | CoinHammy',
            ('learn', 'en'): 'Futures trading guides - Page %d | CoinHammy'}
PG_DESC = {('news', 'vi'): 'Trang %d/%d mục Tin tức của CoinHammy: các tin crypto đã đăng trước đó về Bitcoin, ETF, thị trường phái sinh và những sự kiện tác động đến giá coin.',
           ('news', 'en'): 'Page %d of %d of CoinHammy crypto news: earlier stories on Bitcoin, ETFs, derivatives markets and the events that move crypto prices for traders.',
           ('learn', 'vi'): 'Trang %d/%d mục Kiến thức của CoinHammy: các bài đã đăng về cơ chế thị trường và kỹ năng giao dịch Futures, từ quản lý vốn đến funding rate.',
           ('learn', 'en'): 'Page %d of %d of CoinHammy trading guides: earlier lessons on market mechanics and futures trading skills, from position sizing to funding rates.'}
PG_PAD = {'vi': (' Xem tiếp.', ' Mời anh em xem tiếp.', ' Xem các bài cũ hơn.'), 'en': (' Read on.', ' Keep reading.', ' See older posts.')}
PG_TXT = {'vi': ('Phân trang', 'Trang trước', 'Trang sau', 'Trang %d', 'Trang %d/%d · các bài đã đăng trước đó.'),
          'en': ('Pagination', 'Previous', 'Next', 'Page %d', 'Page %d of %d · earlier posts.')}
COIN_CC = {'BTC': '#F7931A', 'ETH': '#627EEA', 'SOL': '#9945FF', 'XRP': '#3B4A5A'}


def pg_items(kind):
    return jload(os.path.join(ROOT, *KINDS[kind]['idx']), {'items': []})['items']


def pg_total(kind):
    return max(1, math.ceil(len(pg_items(kind)) / PER_PAGE))


def pg_path(kind, lg, n):
    """đường dẫn (bắt đầu bằng /) của trang n"""
    _, base, pat = PG[kind][lg]
    return '/' + base + ('' if n == 1 else '/' + pat % n)


def pg_fit(cands, lo, hi, what):
    for c in cands:
        if lo <= len(c) <= hi: return c
    die('phân trang: không đặt được %s trong %d-%d ký tự: %s' % (what, lo, hi, ' | '.join('%d' % len(c) for c in cands)))


def pg_meta(kind, lg, n, total):
    title = PG_TITLE[(kind, lg)] % n
    if len(title) > 60: die('title trang %d quá 60 ký tự: %s' % (n, title))
    d = PG_DESC[(kind, lg)] % (n, total)
    desc = pg_fit([d] + [d + x for x in PG_PAD[lg]], 150, 160, 'mô tả')
    return title, desc


def pg_nav(kind, lg, cur, total):
    """hàng nút số trang (link thật). 1 trang thì không in gì. Nhiều trang: đầu, cuối, trang hiện tại ±2, chỗ nhảy cách in dấu …"""
    if total < 2: return ''
    T = PG_TXT[lg]; L = lambda n: pg_path(kind, lg, n)
    show = sorted({1, total} | {n for n in range(cur - 2, cur + 3) if 1 <= n <= total})
    out, last = [], 0
    if cur > 1: out.append('<a href="%s" rel="prev" aria-label="%s"><span aria-hidden="true">←</span><span class="pgl">%s</span></a>' % (L(cur - 1), T[1], T[1]))
    for n in show:
        if n - last > 1: out.append('<i aria-hidden="true">…</i>')
        out.append('<b aria-current="page" aria-label="%s">%d</b>' % (T[3] % n, n) if n == cur else '<a href="%s" aria-label="%s">%d</a>' % (L(n), T[3] % n, n))
        last = n
    if cur < total: out.append('<a href="%s" rel="next" aria-label="%s"><span class="pgl">%s</span><span aria-hidden="true">→</span></a>' % (L(cur + 1), T[2], T[2]))
    return '<nav class="pgn" id="pgn" aria-label="%s">%s</nav>' % (T[0], ''.join(out))


def pg_set_nav(t, kind, lg, cur=1):
    """ghi hàng nút số trang vào khối <!--pgn-->…<!--/pgn--> của trang danh sách"""
    if t.count('<!--pgn-->') != 1 or t.count('<!--/pgn-->') != 1: die('phân trang: trang danh sách %s phải có đúng một khối <!--pgn--><!--/pgn-->' % kind)
    t, n = re.subn(r'<!--pgn-->.*?<!--/pgn-->', lambda _: '<!--pgn-->%s<!--/pgn-->' % pg_nav(kind, lg, cur, pg_total(kind)), t, count=1, flags=re.S)
    if n != 1: die('phân trang: trang danh sách %s thiếu khối <!--pgn--><!--/pgn-->' % kind)
    return t


def pg_card(x, kind, lg, labels):
    """một thẻ bài, cùng khuôn với cardHTML() trong trang danh sách (ngày đăng in cố định thay cho "x giờ trước")"""
    L = x.get(lg) or x.get('vi') or {}
    u = (lg == 'en' and x.get('ue')) or x.get('u') or '/%s/%s' % (KINDS[kind]['pfx'], x['slug'])
    img = (lg == 'en' and x.get('img_en')) or x.get('img') or ''
    cc = COIN_CC.get(x.get('coin')) if kind == 'news' else None
    st = ' style="--cc:%s"' % cc if cc else ''
    inner = ''
    if img:
        m = re.match(r'^(/(?:tin|hoc)/img/.+)\.jpg$', img, re.I)
        ss = ''
        if m and all(os.path.isfile(os.path.join(ROOT, (m.group(1) + sfx).lstrip('/'))) for sfx in ('-480.webp', '-960.webp')):
            ss = ' srcset="%s-480.webp 480w, %s-960.webp 960w" sizes="(max-width:620px) 100vw, 330px"' % (m.group(1), m.group(1))
        inner = '<img src="%s"%s alt="" width="640" height="360" loading="lazy" decoding="async" referrerpolicy="no-referrer" onerror="chImgErr(this)">' % (esc(img), ss)
    d = datetime.fromisoformat(x['ts']).astimezone(VN)
    when = d.strftime('%d/%m/%Y') if lg == 'vi' else '%s %d, %d' % (d.strftime('%b'), d.day, d.year)
    return ('<article class="gc"><a class="gimg%s" href="%s" tabindex="-1" aria-hidden="true"%s>%s</a><div class="mrow"><span class="mcat">%s</span><time datetime="%s">%s</time></div>'
            '<h3><a href="%s">%s</a></h3>%s</article>') % ('' if img else ' ph', esc(u), st, inner, esc(labels.get('c_' + x.get('cat', ''), x.get('cat', ''))), x['ts'][:10], when,
                                                         esc(u), esc(L.get('title', '')), '<p class="gd">%s</p>' % esc(L['desc']) if L.get('desc') else '')


def pg_page(tpl, kind, lg, n, total, items):
    """trang n (n >= 2) dựng từ trang 1 cùng ngôn ngữ: giữ nguyên đầu trang, chân trang, CSS, JS; thay phần đầu SEO và phần danh sách"""
    title, desc = pg_meta(kind, lg, n, total)
    url = SITE + pg_path(kind, lg, n); vi_p, en_p = pg_path(kind, 'vi', n), pg_path(kind, 'en', n)
    first = SITE + pg_path(kind, lg, 1)
    a, b = tpl.index('<title>'), tpl.index('<!--/seo-->')
    head = tpl[a:b]

    def sub(pat, rep, txt, cnt=1):
        txt, k = re.subn(pat, lambda _: rep, txt, flags=re.S)
        if k != cnt: die('phân trang: khuôn trang danh sách %s/%s đổi, không thay được %s (%d chỗ)' % (kind, lg, pat[:50], k))
        return txt
    head = sub(r'<title>.*?</title>', '<title>%s</title>' % esc(title), head)
    head = sub(r'<meta name="description" content="[^"]*">', '<meta name="description" content="%s">' % esc(desc), head)
    head = sub(r'<link rel="canonical" href="[^"]*">', '<link rel="canonical" href="%s">' % url, head)
    head = sub(r'<meta property="og:title" content="[^"]*">', '<meta property="og:title" content="%s">' % esc(title), head)
    head = sub(r'<meta property="og:description" content="[^"]*">', '<meta property="og:description" content="%s">' % esc(desc), head)
    head = sub(r'<meta property="og:url" content="[^"]*">', '<meta property="og:url" content="%s">' % url, head)
    head = sub(r'<link rel="alternate" hreflang="vi"[^>]*>\s*<link rel="alternate" hreflang="en"[^>]*>\s*<link rel="alternate" hreflang="x-default"[^>]*>', lang_boot.hreflang(SITE + vi_p, SITE + en_p), head)
    head = sub(r'window\.CH_PAGE=\{l:"(?:vi|en)",alt:\{[^}]*\}\}', 'window.CH_PAGE={l:"%s",alt:%s}' % (lg, json.dumps({'vi': vi_p, 'en': en_p})), head)
    t = tpl[:a] + head + tpl[b:]
    T = PG_TXT[lg]
    i = t.index('var D='); D, _ = json.JSONDecoder().raw_decode(t[i + 6:]); labels = D.get(lg) or {}
    t = t.replace('<a href="#" aria-current="page"', '<a href="%s" aria-current="page"' % pg_path(kind, lg, 1))   # mục menu đang chọn trỏ về trang 1
    m = re.search(r'<div class="thead"><h1 data-i18n="[^"]*">(.*?)</h1></div>\s*<p class="intro"[^>]*>.*?</p>', t, re.S)
    if not m: die('phân trang: không thấy H1 của trang danh sách %s/%s' % (kind, lg))
    t = t[:m.start()] + '<div class="thead"><h1>%s <span class="pgno">· %s</span></h1></div>\n  <p class="intro">%s</p>' % (m.group(1), T[3] % n, T[4] % (n, total)) + t[m.end():]
    m = re.search(r'(<main class="pg">).*?(<div class="lnks">)', t, re.S)
    if not m: die('phân trang: không thấy khối danh sách của trang %s/%s' % (kind, lg))
    cards = ''.join(pg_card(x, kind, lg, labels) for x in items)
    t = t[:m.start()] + '%s\n    <div class="ngrid pga">%s</div>\n    %s\n    %s' % (m.group(1), cards, pg_nav(kind, lg, n, total), m.group(2)) + t[m.end():]
    # trang lưu trữ là trang tĩnh: tắt phần JS tự dựng/tự tải lại danh sách (đầu trang, đổi ngôn ngữ, sáng/tối vẫn chạy)
    for fn in ('function render(){', 'function loadNews(fresh){' if kind == 'news' else 'function loadArt(fresh){'):
        if t.count(fn) != 1: die('phân trang: không thấy %s trong trang danh sách %s/%s' % (fn, kind, lg))
        t = t.replace(fn, fn + 'return;')
    t = re.sub(r'<!--pre-->.*?<!--/pre-->\n', '', t, flags=re.S)   # không còn ô chữ chờ JS điền: bỏ đoạn che chữ lúc chờ chuyển ngôn ngữ
    rel = pg_path(kind, lg, n).lstrip('/') + '.html'
    return header.apply(breadcrumb.apply(t, rel), rel, lg)


def paginate(check=False):
    """ghi hàng nút số trang vào 4 trang danh sách và sinh/xoá các trang lưu trữ. check=True: chỉ trả về danh sách file đang lệch."""
    stale = []

    def put(rel, txt):
        fp = os.path.join(ROOT, rel)
        cur = open(fp, encoding='utf-8').read() if os.path.isfile(fp) else None
        if cur != txt:
            stale.append(rel)
            if not check:
                os.makedirs(os.path.dirname(fp), exist_ok=True); open(fp, 'w', encoding='utf-8').write(txt)
    for kind in PG:
        items = pg_items(kind); total = pg_total(kind)
        for lg in ('vi', 'en'):
            first, base, pat = PG[kind][lg]
            tpl = pg_set_nav(open(os.path.join(ROOT, first), encoding='utf-8').read(), kind, lg)
            put(first, tpl)
            for n in range(2, total + 1):
                put('%s/%s.html' % (base, pat % n), pg_page(tpl, kind, lg, n, total, items[(n - 1) * PER_PAGE:n * PER_PAGE]))
            rx = re.compile('^' + pat.replace('%d', r'(\d+)') + r'\.html$')   # trang thừa (số bài giảm): xoá
            for f in os.listdir(os.path.join(ROOT, base)):
                m = rx.match(f)
                if m and int(m.group(1)) > total:
                    stale.append('%s/%s' % (base, f))
                    if not check: os.remove(os.path.join(ROOT, base, f))
    return stale


def pg_sitemap_rows(now):
    rows = []
    for kind in PG:
        for n in range(2, pg_total(kind) + 1):
            rows += sm_rows(SITE + pg_path(kind, 'vi', n), SITE + pg_path(kind, 'en', n), now)
    return rows

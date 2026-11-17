"""Dựng trang HTML của bài (Việt + Anh), trang 404 và file _redirects.
Tách từ publish.py; chạy từ thư mục gốc của kho (xem publish.py)."""

import json
import os

from news_core import AUTHOR, KINDS, KIT, ROOT, SITE, epath, esc, fmt_time, vpath
from news_images import fig_html, fill_figs, img_alt, img_url
from news_related import place_related
import lang_boot
import breadcrumb
import header
import en_pages


SHARE_ICO = '<svg viewBox="0 1.5 24 24" fill="currentColor" aria-hidden="true"><path d="M12 3.2l4 4-1.4 1.4L13 7v8h-2V7L9.4 8.6 8 7.2l4-4zM5 11h3v2H7v6h10v-6h-1v-2h3v10H5V11z"/></svg>'


def block(a, lg, kind='news'):
    L = a[lg]; img = a.get('image')
    cat = KINDS[kind]['cats'][a['cat']][0 if lg == 'vi' else 1]
    fig = ''
    if img:
        alt = img_alt(a, img, lg)
        cap = fig_html(img, lg)
        fig = '<figure class="acov%s"><img src="%s" alt="%s" width="1200" height="675" decoding="async"%s referrerpolicy="no-referrer">%s</figure>' % (
            ' chart' if img.get('license') == 'chart' else '', esc(img_url(a, img, 'h', lg, kind)), esc(alt), '' if lg == 'vi' else ' loading="lazy"', cap)
    btn = ('Giao dịch %s' if lg == 'vi' else 'Trade %s') % a['coin']
    note = ('Nội dung chỉ để tham khảo, không phải lời khuyên đầu tư. Giao dịch Futures có thể mất toàn bộ ký quỹ.' if lg == 'vi'
            else 'For information only, not investment advice. Futures trading can lose your entire margin.')
    rel = KINDS[kind]['rel'][0 if lg == 'vi' else 1]
    body_in, rel_tail = place_related(a, lg, L['body_html'])
    keys = ''
    if L.get('bullets'):
        keys = '<aside class="akeys" aria-label="%s"><h2>%s</h2><ul>%s</ul></aside>\n' % (
            'Tóm tắt nhanh' if lg == 'vi' else 'Key points', 'Tóm tắt nhanh' if lg == 'vi' else 'Key points',
            ''.join('<li>%s</li>' % esc(x) for x in L['bullets']))
    return ('<div class="%s" lang="%s">\n<div class="thead"><h1>%s</h1></div>\n<p class="intro">%s</p>\n<main class="pg art">\n'
            '<div class="ameta"><span class="acat">%s</span><a class="aby" href="/ve-chung-toi#bien-tap">%s</a><time datetime="%s">%s</time></div>\n%s\n%s'
            '<article class="prose">\n%s\n%s</article>\n'
            '<div class="acta"><button type="button" class="ago chx-open" data-place="news" data-sym="%sUSDT">%s <span aria-hidden="true">→</span></button>'
            '<div class="ashare"><button type="button" class="ashb" aria-haspopup="dialog" aria-expanded="false" aria-label="%s" title="%s">%s</button></div></div>\n'
            '<section class="arel"><h2>%s</h2><div class="arelg" data-rel="%s"></div></section>\n</main>\n</div>') % (
        'lv' if lg == 'vi' else 'le', lg, esc(L['title']), esc(L['lead']), esc(cat), esc(AUTHOR[0 if lg == 'vi' else 1]), esc(a['ts']), fmt_time(a['ts'], lg), fig, keys,
        fill_figs(a, lg, kind, body_in), rel_tail + ('\n' if rel_tail else ''), a['coin'], esc(btn), 'Chia sẻ bài viết' if lg == 'vi' else 'Share this article', 'Chia sẻ bài viết' if lg == 'vi' else 'Share this article', SHARE_ICO, rel, lg)


def redirects(rows):
    """_redirects của Cloudflare Pages: địa chỉ cũ /tin/<slug>, /hoc/<slug> chuyển vĩnh viễn (301) sang địa chỉ mới"""
    out = ['# Tự sinh bởi publish.py rebuild — đừng sửa tay. Địa chỉ cũ của bài -> địa chỉ mới (301).']
    for a, kind in sorted(rows, key=lambda r: (r[1], r[0]['slug'])):
        pfx = KINDS[kind]['pfx']; new = vpath(a, kind)
        out.append('/%s/%s %s 301' % (pfx, a['slug'], new)); out.append('/%s/%s.html %s 301' % (pfx, a['slug'], new))
    open(os.path.join(ROOT, '_redirects'), 'w', encoding='utf-8').write('\n'.join(out) + '\n')


def render(a, kind='news', lg='vi'):
    K = KINDS[kind]; L = a[lg]; i = 0 if lg == 'vi' else 1
    t = open(os.path.join(KIT, 'template.html'), encoding='utf-8').read()
    vp, ep = vpath(a, kind), epath(a, kind)
    url = SITE + (vp if lg == 'vi' else ep)
    hero = a.get('image') or {}
    img = hero.get('url') or ''
    if img.startswith('/'): img = SITE + img
    img = img or SITE + '/tin/og-default.png'
    lds = [img] + [abs_ for abs_ in [(SITE + x['url'] if str(x.get('url', '')).startswith('/') else x.get('url', '')) for x in (a.get('images') or [])] if abs_]
    ld = {'@context': 'https://schema.org', '@type': K['ld'], 'headline': L['title'][:110],
          'description': L['desc'], 'image': lds, 'datePublished': a['ts'], 'dateModified': a.get('updated') or a['ts'],
          'inLanguage': lg, 'mainEntityOfPage': url, 'articleSection': K['cats'][a['cat']][i],
          'author': {'@type': 'Organization', 'name': AUTHOR[i], 'url': SITE + '/ve-chung-toi#bien-tap'},
          'publisher': {'@type': 'Organization', 'name': 'CoinHammy', 'url': SITE + '/'}}
    if L.get('keywords'): ld['keywords'] = ', '.join(L['keywords'])
    head = ('<meta name="description" content="%s">\n<link rel="canonical" href="%s">\n%s\n<base href="/">\n'
            '<meta property="og:type" content="article">\n<meta property="og:site_name" content="CoinHammy">\n'
            '<meta property="og:locale" content="%s">\n<meta property="og:locale:alternate" content="%s">\n'
            '<meta property="og:title" content="%s">\n<meta property="og:description" content="%s">\n<meta property="og:url" content="%s">\n'
            '<meta property="og:image" content="%s">\n<meta property="article:published_time" content="%s">\n'
            '<meta name="twitter:card" content="summary_large_image">\n%s%s\n'
            '<script type="application/ld+json">%s</script>') % (
        esc(L['desc']), url, lang_boot.hreflang(SITE + vp, SITE + ep), 'vi_VN' if lg == 'vi' else 'en_US', 'en_US' if lg == 'vi' else 'vi_VN',
        esc(L['seo_title']), esc(L['desc']), url, esc(img), esc(a['ts']),
        ('<meta name="keywords" content="%s">\n' % esc(', '.join(L['keywords']))) if L.get('keywords') else '',
        lang_boot.boot(lg, vp, ep), json.dumps(ld, ensure_ascii=False).replace('</', '<\\/'))
    t = t.replace('{{SEO_TITLE}}', esc(L['seo_title']) + ' | CoinHammy').replace('{{HEAD}}', head).replace('{{LANG}}', lg)
    t = t.replace('{{SLUG}}', a['slug']).replace('{{PFX}}', K['pfx']).replace('{{BODY}}', block(a, lg, kind))
    t = en_pages.relink(t) if lg == 'en' else en_pages.clean_links(t)     # trang Anh: link menu trỏ bản Anh của trang đích nếu có
    rel = (vp if lg == 'vi' else ep).lstrip('/') + '.html'
    return header.apply(breadcrumb.apply(t, rel), rel, lg)   # đường dẫn phân cấp (chữ + schema cùng một danh sách) + header dùng chung


def render_404():
    """404.html: trang báo không tìm thấy (header dùng chung từ template). Không có trang này thì Cloudflare Pages trả TRANG CHỦ cho mọi địa chỉ sai."""
    t = open(os.path.join(KIT, 'template.html'), encoding='utf-8').read()
    head = ('<meta name="robots" content="noindex,follow">\n<meta name="description" content="Page not found">\n<base href="/">')
    body = (
        '<style>.a404{padding:56px 0 40px;max-width:640px}.a404 h1{margin:0 0 10px}.a404 p{text-align:left;color:var(--muted);margin:0 0 22px;font-size:16px;line-height:1.6}'
        '.a404 .go{display:flex;flex-wrap:wrap;gap:10px}.a404 .go a{display:inline-flex;align-items:center;min-height:44px;padding:0 18px;border-radius:10px;font-weight:700;text-decoration:none;'
        'border:1px solid var(--line,rgba(127,127,127,.35));color:var(--text)}.a404 .go a.main{background:var(--accent);color:var(--accent-ink);border-color:transparent}'
        'html[lang=vi] .l404-en,html[lang=en] .l404-vi{display:none}</style>\n'
        '<main class="a404">\n'
        '<h1><span class="l404-vi">Không tìm thấy trang này</span><span class="l404-en">This page does not exist</span></h1>\n'
        '<p><span class="l404-vi">Địa chỉ có thể bị gõ sai hoặc trang đã được chuyển đi. Hãy quay lại trang chủ hoặc mở một mục bên dưới.</span>'
        '<span class="l404-en">The address may be mistyped, or the page has moved. Go back to the home page or open one of the sections below.</span></p>\n'
        '<div class="go"><a class="main" href="/"><span class="l404-vi">Về trang chủ</span><span class="l404-en">Home</span></a>'
        '<a href="/tin-tuc"><span class="l404-vi">Tin tức</span><span class="l404-en">News</span></a>'
        '<a href="/cong-cu"><span class="l404-vi">Công cụ</span><span class="l404-en">Tools</span></a>'
        '<a href="/xep-hang"><span class="l404-vi">Xếp hạng sàn</span><span class="l404-en">Rankings</span></a></div>\n'
        '</main>')
    t = t.replace('{{SEO_TITLE}}', '404 | CoinHammy').replace('{{HEAD}}', head).replace('{{LANG}}', 'vi')
    t = t.replace('{{SLUG}}', '-').replace('{{PFX}}', 'tin').replace('{{BODY}}', body)
    open(os.path.join(ROOT, '404.html'), 'w', encoding='utf-8').write(header.apply(t, '404.html', 'vi'))


def write_article(a, kind='news'):
    """ghi trang Việt + trang Anh của một bài"""
    for lg, pth in (('vi', vpath(a, kind)), ('en', epath(a, kind))):
        fp = os.path.join(ROOT, pth.lstrip('/') + '.html')
        os.makedirs(os.path.dirname(fp), exist_ok=True)
        open(fp, 'w', encoding='utf-8').write(render(a, kind, lg))

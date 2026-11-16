#!/usr/bin/env python3
"""Bản tiếng Anh của các trang chính (giai đoạn 2, nhóm 1: xếp hạng, so sánh, đánh giá + 19 trang đánh giá từng sàn).

Mỗi trang chính có HAI địa chỉ như bài viết: bản Việt ở gốc (/xep-hang) và bản Anh ở /en/... (/en/rankings).
Bản Anh KHÔNG viết tay: nó được SINH TỪ bản Việt (cùng giao diện, cùng mã, cùng dữ liệu) với đầu trang tiếng Anh
(title, description, canonical, hreflang) và ngôn ngữ cố định là Anh. Sửa bản Việt xong chạy lại:
  python3 tools/en_pages.py            # ghi lại các trang /en/...
  python3 tools/en_pages.py --check    # chỉ kiểm tra, liệt kê trang đang lệch (thoát mã 1 nếu lệch)
  python3 tools/en_pages.py --patch    # (một lần) vá mã chọn ngôn ngữ vào các trang Việt; chạy lại vô hại
publish.py rebuild cũng gọi build() nên bản Anh luôn khớp bản Việt.

Địa chỉ:  xep-hang -> /en/rankings   so-sanh -> /en/compare   danh-gia -> /en/reviews   danh-gia-<sàn> -> /en/reviews/<sàn>
Nhóm 2 (công cụ, trang chủ...) chưa có bản Anh riêng: các link tới đó vẫn trỏ trang Việt (trang tự đổi ngôn ngữ theo lựa chọn của khách)."""
import html, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lang_boot, faq_ld, breadcrumb, header

ROOT = os.path.dirname(HERE)
SITE = json.load(open(os.path.join(HERE, 'news', 'config.json')))['site'].rstrip('/')
INTRO = json.load(open(os.path.join(HERE, 'seo_intro.json'), encoding='utf-8'))   # id -> [tên sàn, câu giới thiệu tiếng Việt]

# trang -> (đường dẫn bản Anh không có .html, tiêu đề, mô tả)
FIXED = {
    'xep-hang': ('en/rankings', 'Crypto Futures Exchange Rankings | CoinHammy',
                 'Crypto derivatives exchanges ranked on one scale: trading fees, leverage and sign-up perks for new traders. Compiled from the public fee pages of each exchange.'),
    'so-sanh': ('en/compare', 'Compare Crypto Exchanges: Fees, Leverage | CoinHammy',
                'Pick 2 to 5 derivatives exchanges and compare fees, leverage, pros and cons and key facts side by side. Data is compiled from public sources of each exchange.'),
    'danh-gia': ('en/reviews', 'Crypto Futures Exchange Reviews | CoinHammy',
                 'Reviews of crypto derivatives exchanges: fees, leverage, safety and pros and cons of each one. Figures compiled from the public sources of every exchange.'),
    # nhóm 2
    'index': ('en/index', 'CoinHammy – Futures Calculator, Crypto News & Rankings',
              'Free tools for futures traders: order size, margin, liquidation price, take profit and stop loss, plus crypto news, guides and exchange rankings in one place.'),
    'cong-cu': ('en/tools', 'Futures Position Calculator: Margin, Liquidation | CoinHammy',
                'Free futures position calculator: see order size, margin, estimated liquidation price and PnL at your take-profit and stop-loss levels before you trade.'),
    'bieu-do': ('en/chart-calculator', 'Position Calculator with Live Candlestick Chart | CoinHammy',
                'CoinHammy advanced position calculator: live candlestick chart with RSI, order book, liquidation price, take profit and stop loss for futures. Free to use.'),
    'quy-doi': ('en/converter', 'Crypto & Currency Converter: VND, USD, USDT, BTC | CoinHammy',
                'Quickly convert between fiat, stablecoins and popular coins such as VND, USD, USDT, BTC and ETH. Free CoinHammy tool: enter an amount and see the result.'),
    've-chung-toi': ('en/about', 'About Us | CoinHammy', 'CoinHammy is where futures traders find the tools and data they use every day: position sizing, converters, exchange rankings, news and trading guides.'),
    'mien-tru-rui-ro': ('en/risk-disclaimer', 'Risk Disclaimer | CoinHammy',
                        'Read carefully before using the tools or following any content on CoinHammy: derivatives trading carries high risk and nothing here is investment advice.'),
}
# trang đã có bản Anh từ trước (danh sách tin/kiến thức) — chỉ dùng để đổi link
OLD = {'tin-tuc': 'en/news', 'kien-thuc': 'en/learn'}


def esc(s): return html.escape(s, quote=True)


def review_en(sid):
    """tiêu đề + mô tả bản Anh của trang đánh giá một sàn (câu giới thiệu tiếng Anh lấy từ chính dữ liệu trong trang)"""
    t = open(os.path.join(ROOT, 'danh-gia-%s.html' % sid), encoding='utf-8').read()
    X, _ = json.JSONDecoder().raw_decode(t[t.index('var X=') + 6:])
    name, intro = X['name'], X['facts']['intro']['en'].strip()
    heads = ('%s review: fees, leverage, safety, pros and cons. ', '%s review: fees, leverage and safety. ', '%s review: fees and leverage. ', '%s review. ')
    pads = (' Read more.', ' Public data only.', ' Figures from public sources.', ' Figures compiled from public sources.')
    hs = [h % name for h in heads]
    full = None   # luôn giữ trọn câu: thử đầu mô tả dài -> ngắn, rồi thêm câu đệm, rồi bỏ câu cuối; cuối cùng mới cắt
    first = re.match(r'.*?[.!?](?=\s|$)', intro)
    for it in ([intro, first.group(0)] if first and first.group(0) != intro else [intro]):
        for h in hs:
            if 150 <= len(h + it) <= 160: full = h + it; break
        if not full:
            for h in hs:
                for pad in pads:
                    if 150 <= len(h + it + pad) <= 160: full = h + it + pad; break
                if full: break
        if full: break
    if not full:
        head = hs[0]; room = 160 - len(head)
        full = head + intro[:room - 1].rsplit(' ', 1)[0].rstrip(',;:-.') + '…'
    return ('%s Review: Fees, Leverage and Safety | CoinHammy' % name, full)


def url_path(p):
    """đường dẫn file bản Anh (không .html) -> địa chỉ công khai: en/index -> en/ (trang chủ), còn lại giữ nguyên"""
    return p[:-5] if p.endswith('/index') else p


def pairs():
    """vi_file -> (en_path, title, desc), theo thứ tự cố định"""
    out = {}
    for vi, (p, ti, de) in FIXED.items(): out[vi + '.html'] = (p, ti, de)
    for sid in sorted(INTRO):
        if os.path.isfile(os.path.join(ROOT, 'danh-gia-%s.html' % sid)):
            ti, de = review_en(sid)
            out['danh-gia-%s.html' % sid] = ('en/reviews/' + sid, ti, de)
    return out


def names_map():
    """tên trang Việt (không .html) -> địa chỉ công khai bản Anh (không có / đầu)"""
    return {vi[:-5]: url_path(v[0]) for vi, v in pairs().items()}


def alt_map():
    """như names_map nhưng trang chủ có khoá '' (đúng với PAGES trong seo_head.py); seo_head dùng để khai báo hreflang cho bản Việt"""
    return {('' if k == 'index' else k): v for k, v in names_map().items()}


def sitemap_alts():
    """cho sitemap(): khoá như danh sách pages ('' là trang chủ) -> bản Anh (đã có .html trừ trang chủ en/)"""
    return {('' if vf == 'index.html' else vf): (url_path(p) if p.endswith('/index') else p + '.html') for vf, (p, _, _) in pairs().items()}


# ---------- đổi link tĩnh trong trang Anh: trỏ bản Anh nếu có, còn lại trỏ trang Việt theo địa chỉ gốc ----------
_NAMES = r'(index|cong-cu|bieu-do|quy-doi|ve-chung-toi|mien-tru-rui-ro|xep-hang|so-sanh|danh-gia|danh-gia-[a-z0-9]+|tin-tuc|kien-thuc)'
LINK = re.compile(r'(?<=["\'])/?' + _NAMES + r'\.html([#?][^"\'\s]*)?(?=["\'])')      # dạng cũ có đuôi .html
# dạng sạch (/cong-cu): mọi chuỗi trong nháy trừ CH_PAGE.alt.vi; trang chủ (/) chỉ nhận ở chỗ chắc chắn là link
LINK2 = re.compile(r'(?<!"vi":)(?<!"vi": )(["\'])/' + _NAMES.replace('index|', '') + r'([#?][^"\'\s]*)?(?=["\'])')
HOME = re.compile(r'(?<!<base )((?:href=|location\.replace\(|location\.href=|this\.href=)["\'])/([#?][^"\'\s]*)?(?=["\'])')
_ABS = re.compile(r'https://coinhammy\.com/((?:[a-z0-9-]+/)*[a-z0-9-]+)\.html')
_ENH = re.compile(r'(?<=["\'])/en/((?:[a-z0-9-]+/)*[a-z0-9-]+)\.html')


def clean_links(text):
    """link nội bộ -> địa chỉ chuẩn không đuôi .html, tuyệt đối từ gốc (index.html -> /). Địa chỉ .html chỉ là bản chuyển hướng,
    để link trỏ thẳng bản chuẩn thì Google không gặp chuyển hướng nữa."""
    text = LINK.sub(lambda m: '/' + ('' if m.group(1) == 'index' else m.group(1)) + (m.group(2) or ''), text)
    text = _ABS.sub(lambda m: 'https://coinhammy.com/' + ('' if m.group(1) == 'index' else m.group(1)), text)
    return _ENH.sub(lambda m: '/en/' + ('' if m.group(1) == 'index' else m.group(1)), text)


def relink(text):
    known = names_map(); known.update(OLD)
    text = clean_links(text)

    text = LINK2.sub(lambda m: m.group(1) + '/' + known.get(m.group(2), m.group(2)) + (m.group(3) or ''), text)
    return HOME.sub(lambda m: m.group(1) + '/' + known['index'] + (m.group(2) or ''), text)


# ---------- vá mã chọn ngôn ngữ vào trang Việt (để trang hiểu CH_PAGE: ngôn ngữ theo địa chỉ, bấm VI/EN thì sang địa chỉ kia) ----------
def patch_vi(t):
    for o in ("var lang='vi';", "var lang='vi',side='long';", "var state=clone(DEF),lang='vi',last=null"):   # cách khai báo khác nhau theo trang
        if o in t: t = t.replace(o, o.replace("lang='vi'", "lang=(window.CH_PAGE&&window.CH_PAGE.l)||'vi'"), 1); break
    t = t.replace("if(sl==='vi'||sl==='en')lang=sl;", "if(!window.CH_PAGE&&(sl==='vi'||sl==='en'))lang=sl;", 1)
    old = "lang=el.getAttribute('data-lang');try{localStorage.setItem('chm_lang',lang);}catch(x){}"
    new = ("var tg=el.getAttribute('data-lang');if(window.CH_PAGE&&tg!==window.CH_PAGE.l&&window.CH_PAGE.alt[tg]){try{localStorage.setItem('chm_lang',tg);}catch(x){}"
           "location.href=window.CH_PAGE.alt[tg]+location.hash;return;}lang=tg;try{localStorage.setItem('chm_lang',lang);}catch(x){}")
    t = t.replace(old, new, 1) if old in t else t
    o3 = "lang=b.getAttribute('data-lang');try{localStorage.setItem('chm_lang',lang);}catch(e){}"      # trang chủ
    n3 = ("var tg=b.getAttribute('data-lang');if(window.CH_PAGE&&tg!==window.CH_PAGE.l&&window.CH_PAGE.alt[tg]){try{localStorage.setItem('chm_lang',tg);}catch(e){}"
          "location.href=window.CH_PAGE.alt[tg]+location.hash;return;}lang=tg;try{localStorage.setItem('chm_lang',lang);}catch(e){}")
    t = t.replace(o3, n3, 1) if o3 in t else t
    # trang đánh giá một sàn: đã có tiêu đề SEO tĩnh theo từng ngôn ngữ, không để mã đè lại tiêu đề ngắn hơn
    o2 = "document.title=(lang==='vi'?'Đánh giá ':'')+X.name+(lang==='vi'?'':' review')+' | CoinHammy';"
    t = t.replace("if(!window.CH_PAGE)if(!window.CH_PAGE)", "if(!window.CH_PAGE)")      # (chạy lại vô hại)
    if o2 in t and ("if(!window.CH_PAGE)" + o2) not in t: t = t.replace(o2, "if(!window.CH_PAGE)" + o2, 1)
    return t


def patched(t):
    return "window.CH_PAGE&&window.CH_PAGE.l)||'vi'" in t and "!window.CH_PAGE&&(sl===" in t and 'location.href=window.CH_PAGE.alt[tg]+location.hash' in t


def en_text(vi_file):
    path, title, desc = pairs()[vi_file]
    t = open(os.path.join(ROOT, vi_file), encoding='utf-8').read()
    assert patched(t), '%s: chưa vá mã chọn ngôn ngữ (chạy python3 tools/en_pages.py --patch)' % vi_file
    vi_path = '/' if vi_file == 'index.html' else '/' + vi_file[:-5]
    up = url_path(path)
    url, vurl = '%s/%s' % (SITE, up), SITE + vi_path
    blk = ('<!--seo-->\n<meta name="description" content="%s">\n<link rel="canonical" href="%s">\n%s\n'
           '<meta property="og:type" content="website">\n<meta property="og:site_name" content="CoinHammy">\n<meta property="og:locale" content="en_US">\n'
           '<meta property="og:locale:alternate" content="vi_VN">\n<meta property="og:title" content="%s">\n<meta property="og:description" content="%s">\n'
           '<meta property="og:url" content="%s">\n<meta property="og:image" content="%s/tin/og-default.png">\n<meta property="og:image:width" content="1200">\n'
           '<meta property="og:image:height" content="630">\n<meta name="twitter:card" content="summary_large_image">\n%s\n<!--/seo-->') % (
        esc(desc), url, lang_boot.hreflang(vurl, url), esc(title), esc(desc), url, SITE, lang_boot.boot('en', vi_path, '/' + up))
    ld = re.search(r'<script type="application/ld\+json">.*?</script>', t[t.index('<!--seo-->'):t.index('<!--/seo-->')], re.S)   # trang chủ có JSON-LD tổ chức/website
    if ld: blk = blk.replace('\n<!--/seo-->', '\n' + ld.group(0) + '\n<!--/seo-->')
    t, n = re.subn(r'<title>.*?</title>\s*<!--seo-->.*?<!--/seo-->', lambda _: '<title>%s</title>\n%s' % (esc(title), blk), t, count=1, flags=re.S)
    assert n == 1, vi_file
    assert t.count('<html lang="vi">') == 1, vi_file
    t = t.replace('<html lang="vi">', '<html lang="en">')
    t = t.replace('title="Về ví dụ ban đầu" aria-label="Về ví dụ ban đầu"', 'title="Back to the sample order" aria-label="Back to the sample order"')   # nút đặt lại cạnh chữ Kết quả
    t = t.replace('<a href="#" aria-current="page"', '<a href="/%s" aria-current="page"' % up)
    # chữ điền sẵn (tools/prerender_i18n.py lưu trong tools/i18n_baked.json): áp lại để trang Anh sinh ra vẫn có sẵn chữ Anh
    import prerender_i18n
    t, _ = prerender_i18n.bake(path + '.html', relink(t))
    return path, header.apply(breadcrumb.apply(faq_ld.inject(t), path + ".html"), path + ".html", 'en')   # header bản Anh (tools/header.py)


def build(check=False):
    """ghi (hoặc chỉ kiểm tra) các trang Anh. Trả về danh sách file lệch (check=True) hoặc đã ghi"""
    stale = []
    for vf in pairs():
        path, t = en_text(vf)
        fp = os.path.join(ROOT, path + '.html')
        cur = open(fp, encoding='utf-8').read() if os.path.isfile(fp) else None
        if cur != t:
            stale.append(path + '.html')
            if not check:
                os.makedirs(os.path.dirname(fp), exist_ok=True)
                open(fp, 'w', encoding='utf-8').write(t)
    return stale


def main():
    if '--patch' in sys.argv:
        for vf in pairs():
            fp = os.path.join(ROOT, vf)
            t = open(fp, encoding='utf-8').read(); n = patch_vi(t)
            if n != t: open(fp, 'w', encoding='utf-8').write(n); print('đã vá', vf)
            assert patched(n), vf + ': vá không đủ'
        return
    st = build(check='--check' in sys.argv)
    if '--check' in sys.argv:
        print('Trang tiếng Anh lệch so với bản Việt: ' + (', '.join(st) if st else 'không')); sys.exit(1 if st else 0)
    print('Đã ghi %d trang tiếng Anh' % len(st) if st else 'Các trang tiếng Anh đã khớp bản Việt')


if __name__ == '__main__':
    main()

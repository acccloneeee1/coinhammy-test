#!/usr/bin/env python3
"""Điền sẵn nội dung vào HTML để trình duyệt vẽ được ngay, không phải chờ cả khối JavaScript chạy xong
(cải thiện LCP và giảm giật bố cục CLS). JavaScript vẫn chạy như cũ và ghi đè đúng nội dung đó.

Có 2 loại nội dung, cùng lưu trong tools/i18n_baked.json (en_pages.py và publish.py tự áp lại từ file này khi sinh trang EN,
nên trang EN sinh lại vẫn giữ nội dung điền sẵn):
  1. CHỮ: nội dung của mọi phần tử [data-i18n] (và vài id như toolH1/toolIntro/introMore) theo ngôn ngữ của trang
     (trang trong en/ điền chữ Anh, còn lại chữ Việt).
  2. DANH SÁCH TIN: trang tin-tuc, kien-thuc (+ en/news, en/learn) có sẵn bài nổi bật + 5 tin mới + lưới thẻ đầu trang,
     để ảnh bìa tải ngay thay vì đợi JS tải index.json. Chữ "x phút trước" được bỏ khỏi bản điền sẵn (JS điền lại), tránh hiện giờ cũ.

  3. TRANG TIỀN (xếp hạng, so sánh, đánh giá, 19 trang đánh giá từng sàn, về chúng tôi, miễn trừ rủi ro; VI + EN, 48 trang): chữ [data-i18n]
     như loại 1, cộng các khối do JS dựng (bảng xếp hạng, bảng so sánh, thẻ sàn, nội dung đánh giá...) liệt kê ở DYN_IDS. Mục đích: bot đọc HTML thô
     (chưa chạy JS) thấy đủ H1 + bảng + chữ thay vì trang gần như rỗng. Các khối này được bọc bởi <!--b-->...<!--/b-->, thẻ chứa có thêm data-pb="1".
     Trang đánh giá sàn mới tự được nhận (danh-gia-*.html, en/reviews/*.html); chạy lại công cụ để điền.

Cách làm: mở trang bằng trình duyệt thật (Playwright), đọc nội dung JS vừa dựng rồi ghi vào đúng thẻ trong HTML. Chạy lại bao nhiêu lần cũng được.
  python3 tools/prerender_i18n.py                  # làm lại tất cả trang trong PAGES (chữ + danh sách)
  python3 tools/prerender_i18n.py cong-cu.html     # chỉ trang chỉ định
  python3 tools/prerender_i18n.py --lists          # chỉ làm mới danh sách tin ở 4 trang danh sách (publish.py tự gọi sau mỗi bài đăng)
  python3 tools/prerender_i18n.py --check          # chỉ kiểm tra, báo lệch thì thoát mã 1 (không ghi file)
Khi nào chạy: sửa chữ trong từ điển i18n của các trang trong PAGES (bản Việt), hoặc dựng lại trang từ build -> chạy không tham số.
Đăng bài mới -> publish.py tự chạy --lists. Khách đã chọn ngôn ngữ kia (sắp bị chuyển trang) thì đoạn bảo vệ <!--pre--> ẩn các ô
chữ cho đến khi trang chuyển xong, nên không thấy chữ sai ngôn ngữ."""
import functools, glob, hashlib, http.server, json, os, re, socketserver, sys, threading

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEXT_PAGES = ['index.html', 'cong-cu.html', 'quy-doi.html', 'bieu-do.html',
              'en/index.html', 'en/tools.html', 'en/converter.html', 'en/chart-calculator.html']
LIST_PAGES = ['tin-tuc.html', 'kien-thuc.html', 'en/news.html', 'en/learn.html']
MONEY_VI = ['xep-hang.html', 'so-sanh.html', 'danh-gia.html', 've-chung-toi.html', 'mien-tru-rui-ro.html']
MONEY_EN = ['en/rankings.html', 'en/compare.html', 'en/reviews.html', 'en/about.html', 'en/risk-disclaimer.html']


def money_pages():
    g = lambda pat: sorted(os.path.relpath(f, ROOT).replace(os.sep, '/') for f in glob.glob(os.path.join(ROOT, pat)))
    return MONEY_VI + g('danh-gia-*.html') + MONEY_EN + g('en/reviews/*.html')


MONEY = money_pages()
PAGES = TEXT_PAGES + LIST_PAGES + MONEY
CHECK = '--check' in sys.argv
ONLY_LISTS = '--lists' in sys.argv
ARGS = [a for a in sys.argv[1:] if not a.startswith('--')]
EXE = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'
CACHE = os.path.join(ROOT, 'tools', 'i18n_baked.json')

# các phần tử do JS điền theo id (không dùng data-i18n) và nằm ở đầu trang công cụ
FILL_IDS = ['toolH1', 'toolIntro', 'introMore']
# khối do JS dựng (không có data-i18n) ở các trang tiền; trang nào có id nào thì điền id đó
DYN_IDS = ['picks', 'cb',                                  # xep-hang
           'vsPick', 'vsT',                                # so-sanh
           'rhCount', 'rhGrid',                            # danh-gia
           'rvH', 'rvMeta', 'rvHero', 'rvKeyN', 'rvKeyT', 'rvPCb', 'rvSafeP', 'rvFeeT', 'rvSteps', 'rvFaqB', 'rvAlt', 'rvCta2']  # danh-gia-<sàn>
TAG = re.compile(r'(<([a-zA-Z0-9]+)\b[^>]*?\bdata-i18n="([^"]+)"[^>]*>)(.*?)(</\2>)', re.S)
AGO = re.compile(r'\d+ (?:phút|giờ|ngày) trước|\d+ (?:min|h|hours?|days?) ago')


def page_lang(PAGE):
    return 'en' if PAGE.startswith('en/') else 'vi'


_S = {}


def _session():
    """một trình duyệt + một máy chủ cục bộ dùng chung cho mọi trang (nhanh hơn mở lại từng lần)"""
    if not _S:
        from playwright.sync_api import sync_playwright

        class Q(http.server.SimpleHTTPRequestHandler):
            def log_message(self, *a):
                pass

        srv = socketserver.TCPServer(('127.0.0.1', 0), functools.partial(Q, directory=ROOT))
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        pw = sync_playwright().start()
        _S.update(srv=srv, pw=pw, b=pw.chromium.launch(executable_path=EXE) if os.path.exists(EXE) else pw.chromium.launch())
    return _S


def close_session():
    if _S:
        _S['b'].close()
        _S['pw'].stop()
        _S['srv'].shutdown()
        _S.clear()


def rendered(PAGE):
    S = _session()
    ctx = S['b'].new_context(viewport={'width': 1366, 'height': 768})
    page = ctx.new_page()
    page.route('**/*', lambda r: r.continue_() if r.request.url.startswith('http://127.0.0.1') else r.abort())
    page.goto('http://127.0.0.1:%d/%s' % (S['srv'].server_address[1], PAGE), wait_until='load')
    page.wait_for_timeout(1500)
    if page.evaluate('document.documentElement.lang') != page_lang(PAGE):
        sys.exit('Trang %s không đúng ngôn ngữ của nó (%s), dừng để khỏi ghi nhầm.' % (PAGE, page_lang(PAGE)))
    pairs = page.evaluate("Array.from(document.querySelectorAll('[data-i18n]')).map(e=>[e.getAttribute('data-i18n'),e.innerHTML])")
    ids = page.evaluate("Object.fromEntries(FILL_IDS.map(i=>[i,document.getElementById(i)?document.getElementById(i).innerHTML:null]))".replace('FILL_IDS', repr(FILL_IDS)))
    lists = page.evaluate("""()=>{const g=i=>document.getElementById(i);if(!g('nhero')||!g('ngrid'))return null;
      return {hc:g('nhero').className,h:g('nhero').innerHTML,hh:g('nhero').hidden,g:g('ngrid').innerHTML,gh:g('ngrid').hidden,
              mh:g('moreH').hidden,nm:g('nmore').hidden,nc:g('ncount').textContent}}""")
    dyn = page.evaluate("""ids=>Object.fromEntries(ids.map(i=>[i,document.getElementById(i)&&!document.getElementById(i).hasAttribute('data-i18n')?document.getElementById(i).innerHTML.trim():null]).filter(x=>x[1]))""", DYN_IDS) if PAGE in MONEY else {}
    ctx.close()
    texts = {}
    for k, h in pairs:
        if k in texts and texts[k] != h:
            sys.exit('Cùng khóa "%s" nhưng nội dung khác nhau, dừng.' % k)
        texts[k] = h
    if lists:
        if '<article' not in lists['h']:
            lists = None   # chưa có bài nào (hoặc JS chưa dựng được): không ghi đè danh sách đã điền
        else:
            for k in ('h', 'g'):
                lists[k] = re.sub(r'(<span class="tm">)\s*·\s*', r'\1', AGO.sub('', lists[k]))
    return texts, ids, lists, dyn


GUARD_VP = '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n'
# hàm dựng chữ của từng kiểu trang: thêm dòng gỡ thuộc tính data-pre ngay đầu để chữ hiện lại khi JS dịch xong
FNS = [("function applyI18n(){\n  document.documentElement.lang=lang;", "function applyI18n(){\n  document.documentElement.removeAttribute('data-pre');\n  document.documentElement.lang=lang;"),
       ("function apply(){\n  document.documentElement.lang=lang;", "function apply(){\n  document.documentElement.removeAttribute('data-pre');\n  document.documentElement.lang=lang;")]


def guard_block(lang):
    other = 'vi' if lang == 'en' else 'en'
    return ('<!--pre-->\n<script>try{if(localStorage.getItem("chm_lang")==="%s")document.documentElement.setAttribute("data-pre","%s")}catch(e){}</script>\n'
            '<style>html[data-pre] [data-i18n],html[data-pre] #toolIntro,html[data-pre] #introMore,html[data-pre] [data-pb]{visibility:hidden}</style>\n<!--/pre-->\n') % (other, other)


def guard(src, lang):
    if '<!--pre-->' in src:   # đã có: thay bằng bản mới nhất (chạy lại không nhân đôi)
        src = re.sub(r'<!--pre-->.*?<!--/pre-->\n', lambda m: guard_block(lang), src, count=1, flags=re.S)
    else:
        if src.count(GUARD_VP) != 1:
            sys.exit('Không tìm thấy điểm chèn đoạn bảo vệ.')
        src = src.replace(GUARD_VP, GUARD_VP + guard_block(lang), 1)
    if "removeAttribute('data-pre')" not in src:
        hit = [(o, n) for o, n in FNS if src.count(o) == 1]
        if len(hit) != 1:
            sys.exit('Không tìm thấy hàm dựng chữ chuẩn (applyI18n/apply).')
        src = src.replace(hit[0][0], hit[0][1], 1)
    return src


def bake_lists(src, L):
    """ghi sẵn bài nổi bật + tin mới + lưới thẻ vào 4 khối nhero/moreH/ngrid/nmore của trang danh sách"""
    h = ' hidden' if L['hh'] else ''
    pats = [
        (r'<div class="[^"]*" id="nhero"[^>]*>(?:<!--b-->.*?<!--/b-->)?</div>',
         '<div class="%s" id="nhero" data-baked="1"%s><!--b-->%s<!--/b--></div>' % (L['hc'], h, L['h'])),
        (r'<div class="ngrid" id="ngrid"[^>]*>(?:<!--b-->.*?<!--/b-->)?</div>',
         '<div class="ngrid" id="ngrid"%s><!--b-->%s<!--/b--></div>' % (' hidden' if L['gh'] else '', L['g'])),
        (r'<div class="sech" id="moreH"(?: hidden)?>', '<div class="sech" id="moreH"%s>' % (' hidden' if L['mh'] else '')),
        (r'<div class="nmore" id="nmore"(?: hidden)?><p id="ncount">[^<]*</p>',
         '<div class="nmore" id="nmore"%s><p id="ncount">%s</p>' % (' hidden' if L['nm'] else '', L['nc'])),
    ]
    for pat, rep in pats:
        src, n = re.subn(pat, lambda m, r=rep: r, src, count=1, flags=re.S)
        if n != 1:
            sys.exit('Không tìm thấy khối danh sách để ghi sẵn: ' + pat[:40])
    return src


def bake_dyn(src, dyn):
    """ghi sẵn các khối do JS dựng (DYN_IDS) vào đúng thẻ có id đó; bọc bằng <!--b-->…<!--/b--> để chạy lại không nhân đôi"""
    for i, html in (dyn or {}).items():
        pat = r'(<([a-zA-Z0-9]+)\b[^>]*?\sid="%s"[^>]*?)(>)(?:<!--b-->.*?<!--/b-->)?(</\2>)' % re.escape(i)
        src, n = re.subn(pat, lambda m: m.group(1) + ('' if 'data-pb=' in m.group(1) else ' data-pb="1"') + m.group(3) + '<!--b-->' + html + '<!--/b-->' + m.group(4),
                         src, count=1, flags=re.S)
        if n != 1:
            sys.exit('Không tìm thấy thẻ id="%s" (rỗng hoặc đã điền) để ghi sẵn.' % i)
    return src


def unbaked(src):
    """HTML đã bỏ mọi phần điền sẵn: dùng để biết nguồn của trang có đổi không (khỏi phải mở trình duyệt khi --check)"""
    s = re.sub(r'<!--pre-->.*?<!--/pre-->\n', '', src, flags=re.S)
    s = re.sub(r'<!--b-->.*?<!--/b-->', '', s, flags=re.S).replace(' data-pb="1"', '')
    return TAG.sub(lambda m: m.group(1) + m.group(5), s)


def src_hash(src):
    return hashlib.sha1(unbaked(src).encode('utf-8')).hexdigest()[:16]


def load_cache():
    return json.load(open(CACHE, encoding='utf-8')) if os.path.isfile(CACHE) else {}


def bake(PAGE, src, texts=None, ids=None, lists=None, dyn=None):
    """Áp nội dung điền sẵn vào HTML của PAGE (không cần trình duyệt). Mặc định dùng nội dung lưu trong i18n_baked.json;
    trang không có trong file lưu -> trả nguyên văn. Trả về (nội dung mới, các khóa chữ không điền được)."""
    if texts is None:
        c = load_cache().get(PAGE)
        if not c:
            return src, []
        texts, ids, lists, dyn = c['texts'], c.get('ids'), c.get('lists'), c.get('dyn')
    src = guard(src, page_lang(PAGE))
    missing = []

    def fill(m):
        key = m.group(3)
        if key not in texts or not texts[key].strip():
            missing.append(key)
            return m.group(0)
        return m.group(1) + texts[key] + m.group(5)

    out = TAG.sub(fill, src)
    for i, html in (ids or {}).items():
        if html and html.strip():
            out = re.sub(r'(<([a-zA-Z0-9]+)\b[^>]*?\bid="%s"[^>]*>)(.*?)(</\2>)' % i,
                         lambda m: m.group(1) + html + m.group(4), out, count=1, flags=re.S)
    if lists:
        out = bake_lists(out, lists)
    if dyn:
        out = bake_dyn(out, dyn)
    return out, missing


def main():
    bad = 0
    cache = load_cache()
    targets = ARGS or (LIST_PAGES if ONLY_LISTS else PAGES)
    for PAGE in targets:
        path = os.path.join(ROOT, PAGE)
        cur = open(path, encoding='utf-8').read()
        c = cache.get(PAGE) or {}
        if CHECK and PAGE in MONEY and c.get('h') == src_hash(cur):
            # nguồn trang không đổi từ lần điền gần nhất: chỉ cần kiểm HTML hiện có còn khớp bản lưu, khỏi mở trình duyệt
            out, _ = bake(PAGE, cur)
            if out != cur:
                bad = 1
                print('%-24s LỆCH so với bản lưu, cần chạy lại công cụ' % PAGE)
            continue
        texts, ids, lists, dyn = rendered(PAGE)
        if lists is None and PAGE in LIST_PAGES:
            lists = c.get('lists')   # không dựng được thì giữ danh sách cũ
        out, missing = bake(PAGE, cur, texts, ids, lists, dyn)
        n = len(TAG.findall(out))
        print('%-24s ô data-i18n: %d | điền được: %d | bỏ qua: %s%s%s' % (PAGE, n, n - len(missing), missing or 'không', ' | có danh sách tin' if lists else '',
                                                                      ' | khối JS: %d' % len(dyn) if dyn else ''))
        new = {'texts': texts, 'ids': ids}
        if lists:
            new['lists'] = lists
        if dyn:
            new['dyn'] = dyn
        if PAGE in MONEY:
            new['h'] = src_hash(out)
        if out != cur or c != new:
            if CHECK:
                bad = 1
                print('  -> LỆCH, cần chạy lại công cụ để cập nhật')
            else:
                open(path, 'w', encoding='utf-8').write(out)
                cache[PAGE] = new
                print('  -> đã cập nhật')
    if not CHECK:
        json.dump(cache, open(CACHE, 'w', encoding='utf-8'), ensure_ascii=False, indent=0, sort_keys=True)
    close_session()
    if CHECK:
        sys.exit(bad)


if __name__ == '__main__':
    main()

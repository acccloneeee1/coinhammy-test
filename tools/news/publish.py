#!/usr/bin/env python3
"""CoinHammy news publisher — turns one article JSON into a page on the site.

  python3 tools/news/publish.py recent [--hours 48]   # what was published lately (for the no-repeat check)
  python3 tools/news/publish.py check  ARTICLE.json   # validate only, writes nothing
  python3 tools/news/publish.py publish ARTICLE.json  # bài tin: trang Việt tin-tuc/<slug>.html + trang Anh en/news/<slug-en>.html, cập nhật tin/index.json, log, sitemap
  python3 tools/news/publish.py learn-today           # knowledge article of today (1 per day)
  python3 tools/news/publish.py learn-recent [--days 14]   # recent knowledge articles (avoid repeating a topic)
  python3 tools/news/publish.py learn-check ART.json  # validate a knowledge article
  python3 tools/news/publish.py learn-publish ART.json  # bài kiến thức: kien-thuc/<slug>.html + en/learn/<slug-en>.html + hoc/index.json (one per day, every day)
  python3 tools/news/publish.py today                 # articles already published today (VN time): count vs the daily cap, per category
  python3 tools/news/publish.py related ART.json [--kind learn] # gợi ý bài cũ liên quan để điền "related" (mỗi bài PHẢI có 1–3 mục; 2 mục trở lên thì rải vào thân bài, dùng <p>[[rel:N]]</p> để đặt ngay dưới đoạn văn khớp) và link trong câu văn
  python3 tools/news/publish.py related-backfill      # điền "related" tự động cho bài đã đăng còn thiếu (rồi chạy rebuild)
  python3 tools/news/publish.py rebuild               # re-render every article (cả bản Việt + Anh) và hai trang danh sách tiếng Anh

Images (news): REAL pictures only - never text or a logo/domain drawn into a picture. "image" = cover (required); "images" = extra pictures inside the body, as many as the story
really needs - one for EACH important point that a picture explains better than words (a real chart screenshot, a photo of the person/place/event in the news, an on-chain transaction).
Never a picture just to fill space and never one per section by default; a story with no such point keeps "images" empty and the cover alone is enough. Each is placed in body_html as
<p>[[img:N]]</p> between two paragraphs (at least two text paragraphs between two pictures), shown full column width, with a caption_vi/caption_en saying what it shows.
"bullets" (news: required, exactly 3 short sentences in vi AND en) = the "Tóm tắt nhanh / Key points" box shown under the cover. Each image object:
  {"file": "/path/photo.jpg", "src": "<page the picture came from>", "license": "Unsplash|CC0|CC BY|public domain|chart", "credit": "(only CC BY / CC BY-SA need it: printed under the caption in smaller text; other licences never print it)",
   "alt_vi": "...", "alt_en": "...", "caption_vi": "(the ONLY text printed under a picture; required for charts and body pictures; chart = timeframe + price levels; cover too)", "caption_en": "...", "focus": [0.5, 0.4]}      # focus = the point to keep when cropping to 16:9 (x, y in 0..1)
publish copies each file to tin/img/<slug>-h.jpg / -N.jpg (cropped 16:9, 1200x675) and refuses a source page already used by another article.

Run from the repository root. Only the standard library is used.
"""
import html, json, math, os, re, sys, unicodedata
from datetime import datetime, timedelta, timezone

ROOT = os.getcwd()
KIT = os.path.join(ROOT, 'tools', 'news')
CFG = json.load(open(os.path.join(KIT, 'config.json'), encoding='utf-8'))
SITE = CFG['site'].rstrip('/')
VN = timezone(timedelta(hours=7))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import lang_boot
import breadcrumb, header
import en_pages
import prerender_i18n
import thumbs
CATS = {'btc': ('Bitcoin', 'Bitcoin'), 'alt': ('Altcoin', 'Altcoins'), 'fut': ('Futures', 'Futures'),
        'ex': ('Sàn giao dịch', 'Exchanges'), 'reg': ('Quy định', 'Regulation'), 'pol': ('Chính trị', 'Politics')}
# names of outside outlets / attribution phrases that must never appear in a published article
NO_SOURCE = re.compile(r"(cointelegraph|coindesk|the\s*block\b|decrypt\b|reuters|bloomberg|cnbc|coingape|u\.today|cryptoslate|"
                       r"bitcoin\s*magazine|cryptopotato|beincrypto|newsbtc|the\s*defiant|blockworks|watcher\.?guru|coin68|"
                       r"tạp chí bitcoin|blogtienao|vnexpress|theo (báo|trang|tờ|hãng tin|nguồn)|nguồn\s*:|source\s*:|according to (a |the )?(report|outlet)|"
                       r"reported by|as reported|first reported)", re.I)
CATS_L = {'mk': ('Thị trường', 'Market'), 'tr': ('Giao dịch', 'Trading')}
# pfx = thư mục chứa index.json + ảnh (giữ nguyên); vdir = thư mục trang Việt của bài MỚI (bài cũ ở tin/, hoc/ đã chuyển sang đây, địa chỉ cũ 301); edir = thư mục trang Anh
KINDS = {'news': {'pfx': 'tin', 'vdir': 'tin-tuc', 'edir': 'en/news', 'cats': CATS, 'ld': 'NewsArticle', 'rel': ('Tin khác', 'More news'), 'idx': ('tin', 'index.json')},
         'learn': {'pfx': 'hoc', 'vdir': 'kien-thuc', 'edir': 'en/learn', 'cats': CATS_L, 'ld': 'Article', 'rel': ('Bài kiến thức khác', 'More guides'), 'idx': ('hoc', 'index.json')}}
DAILY_CAP = 5            # articles per day, Monday-Friday only
AUTHOR = ('Ban biên tập CoinHammy', 'CoinHammy Editorial Team')
REQ = ('slug', 'cat', 'ts', 'event', 'vi', 'en')
REQ_L = ('title', 'seo_title', 'desc', 'lead', 'body_html')


def die(msg):
    print('LỖI:', msg); sys.exit(1)


def esc(s):
    return html.escape(str(s or ''), quote=True)


def slugify(s):
    s = unicodedata.normalize('NFD', s.replace('đ', 'd').replace('Đ', 'D'))
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn').lower()
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-')[:80].strip('-')

IMG_MARK = re.compile(r'<p>\s*\[\[img:(\d+)\]\]\s*</p>', re.I)
REL_MARK = re.compile(r'<p>\s*\[\[rel:(\d+)\]\]\s*</p>', re.I)   # đặt dòng "Liên quan" của related[N] ngay dưới đoạn văn đứng trước nó
CAT_COL = {'btc': '#F7931A', 'alt': '#8B5CF6', 'fut': '#06B6D4', 'ex': '#22C55E', 'reg': '#F59E0B', 'pol': '#EF4444', 'mk': '#0EA5E9', 'tr': '#14B8A6'}
FONT = "Inter,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"


def check_img(img, kind, name, slug=''):
    """Validate one image object. Real pictures only (photo, chart screenshot, official logo) - never text drawn into a picture.
    Fields: file (local jpg/png/webp, copied into <pfx>/img/ and framed 16:9) OR url (already '/<pfx>/img/..'), alt_vi, alt_en,
    license, src (page the picture came from; used for the "already used" ledger), credit (only when the licence needs it), focus [x,y] 0..1."""
    if not isinstance(img, dict): die('%s phải là object' % name)
    if img.get('gen'): die('%s: không dùng thẻ tự dựng "gen" nữa — dùng ảnh thật (ảnh chụp, chart TradingView, logo chính thức)' % name)
    f = img.get('file')
    if f:
        if not os.path.isfile(f): die('%s.file không tồn tại: %s' % (name, f))
        if not re.search(r'\.(png|jpe?g|webp)$', f, re.I): die('%s.file phải là png/jpg/webp' % name)
        if os.path.getsize(f) > 15 * 1024 * 1024: die('%s.file quá lớn (>15MB)' % name)
        try:
            from PIL import Image
            w, h = Image.open(f).size
            if min(w, h) < 640: die('%s: ảnh quá nhỏ (%dx%d) — cạnh ngắn tối thiểu 640px' % (name, w, h))
        except ImportError:
            pass
    elif str(img.get('url', '')).startswith('/'):
        if not os.path.isfile(os.path.join(ROOT, img['url'].lstrip('/'))): die('%s.url trỏ tới file chưa có trong repo: %s' % (name, img['url']))
    else:
        die('%s: cần "file" (đường dẫn ảnh đã tải về máy) — không hotlink ảnh từ trang khác' % name)
    for lg in ('vi', 'en'):
        if not str(img.get('alt_' + lg, '')).strip(): die('%s.alt_%s bắt buộc (mô tả ảnh, không chứa chữ "ảnh của")' % (name, lg))
    lic = str(img.get('license', '')).lower()
    if not lic: die('%s.license bắt buộc (public domain, CC0, CC BY, CC BY-SA, Unsplash, hoặc chart)' % name)
    if re.search(r'getty|reuters|ap photo|afp|shutterstock|editorial|bloomberg', lic + ' ' + str(img.get('credit', '')).lower() + ' ' + str(img.get('src', '')).lower()):
        die('ảnh bản quyền thương mại (Getty/Reuters/AP/AFP/Bloomberg/Shutterstock) — không được dùng (%s)' % name)
    if re.search(r'\bby\b', lic) and not img.get('credit'): die('ảnh CC BY/BY-SA phải có %s.credit (tên tác giả + giấy phép)' % name)
    if lic != 'chart' and not img.get('src'): die('%s.src bắt buộc (địa chỉ trang gốc của ảnh, để không dùng lại một ảnh cho nhiều bài)' % name)


def _framed(src, focus=None, W=1200, H=675):
    """Cover-crop to 16:9 around the focus point (the picture exactly as frame_img will save it)."""
    from PIL import Image, ImageOps
    im = ImageOps.exif_transpose(Image.open(src)); im.load()
    if im.mode != 'RGB': im = im.convert('RGB')
    fx, fy = (focus or [0.5, 0.5])[:2]
    r = W / H; w, h = im.size
    if w / h > r: cw, ch = round(h * r), h
    else: cw, ch = w, round(w / r)
    x0 = min(max(round(fx * w - cw / 2), 0), w - cw); y0 = min(max(round(fy * h - ch / 2), 0), h - ch)
    return im.crop((x0, y0, x0 + cw, y0 + ch)).resize((W, H), Image.LANCZOS)


def frame_img(src, dst, focus=None, W=1200, H=675):
    """Cover-crop to 16:9 around the focus point, re-encode as a web JPEG. No text, logo or domain is ever drawn on the picture."""
    im = _framed(src, focus, W, H)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    im.save(dst, 'JPEG', quality=84, optimize=True, progressive=True)


def framed_size(src, focus=None):
    """bytes of the cover as frame_img would store it (same crop + same JPEG settings), without writing anything"""
    import io
    buf = io.BytesIO(); _framed(src, focus).save(buf, 'JPEG', quality=84, optimize=True, progressive=True)
    return buf.tell()


def localize_news(a, kind='news'):
    """Copy every "file" image into <pfx>/img/<slug>-h.jpg / -N.jpg (16:9) and point url at it."""
    pfx = KINDS[kind]['pfx']
    items = [('h', a.get('image'))] + [(str(i), im) for i, im in enumerate(a.get('images') or [], 1)]
    for tag, im in items:
        if im and im.get('file'):
            name = '%s-%s.jpg' % (a['slug'], tag)
            frame_img(im['file'], os.path.join(ROOT, pfx, 'img', name), im.get('focus'))
            im['url'] = '/%s/img/%s' % (pfx, name); im.pop('file', None); im.pop('focus', None)


LEDGER = os.path.join(KIT, 'images_used.json')


def ledger_check(a):
    """One picture, one article: a source page already used by another article is refused."""
    used = jload(LEDGER, {})
    items = [a.get('image')] + list(a.get('images') or [])
    seen = set()
    for im in items:
        s = (im or {}).get('src')
        if not s: continue
        if s in seen: die('cùng một ảnh (%s) dùng hai lần trong bài' % s)
        seen.add(s)
        if s in used and used[s] != a['slug']: die('ảnh %s đã dùng ở bài "%s" — chọn ảnh khác' % (s, used[s]))
    return used, seen


def img_url(a, im, tag, lg, kind='news'):
    return im['url']


def img_alt(a, im, lg):
    return im.get('alt_' + lg) or a[lg]['title']


def fig_parts(im, lg):
    """(chú thích, dòng ghi tác giả) hiện dưới ảnh. Chú thích = caption_vi / caption_en.
    Dòng ghi tác giả (credit) CHỈ in cho ảnh CC BY / CC BY-SA (giấy phép bắt ghi tác giả), chữ nhỏ hơn chú thích; Unsplash, chart, public domain, CC0 không in credit."""
    cap = str(im.get('caption_' + lg) or '').strip()
    cred = str(im.get('credit') or '').strip() if re.search(r'\bby\b', str(im.get('license', '')).lower()) else ''
    return cap, cred


def fig_html(im, lg):
    cap, cred = fig_parts(im, lg)
    if not cap and not cred: return ''
    return '<figcaption>%s%s</figcaption>' % (esc(cap), ('<span class="acred">%s</span>' % esc(cred)) if cred else '')


def fill_figs(a, lg, kind, body):
    imgs = a.get('images') or []
    def f(m):
        i = int(m.group(1)); im = imgs[i - 1]
        cap = fig_html(im, lg)
        return '<figure class="afig%s"><img src="%s" alt="%s" width="1200" height="675" loading="lazy" decoding="async" referrerpolicy="no-referrer">%s</figure>' % (
            ' chart' if im.get('license') == 'chart' else '', esc(img_url(a, im, str(i), lg, kind)), esc(img_alt(a, im, lg)), cap)
    return IMG_MARK.sub(f, body)


def clean_body(h):
    """Allow only simple article markup. External links are removed (text kept); internal site links stay."""
    h = re.sub(r'(?is)<(script|style|iframe|object|embed|form)[^>]*>.*?</\1>', '', h)
    h = re.sub(r'(?i)\son\w+\s*=\s*("[^"]*"|\'[^\']*\'|[^\s>]+)', '', h)
    h = re.sub(r'(?is)<a\s[^>]*href\s*=\s*["\']\s*(https?:)?//[^"\']*["\'][^>]*>(.*?)</a>', r'\2', h)
    h = re.sub(r'(?i)</?(?!(p|h2|h3|ul|ol|li|strong|em|b|i|blockquote|a|br|table|thead|tbody|tr|th|td)\b)[a-z][^>]*>', '', h)
    return h.strip()


def words(h):
    return len(re.sub(r'<[^>]+>', ' ', h).split())

# ---- Liên quan: dòng "Liên quan: <tiêu đề bài khác>" cuối mỗi bài (BẮT BUỘC, 1–3 mục; 1 mục → cuối bài; 2+ mục → <p>[[rel:N]]</p> dưới đoạn khớp, còn lại rải giữa bài rồi cuối bài) + link trong câu văn (tuỳ chọn, chỉ khi thật sự khớp) ----
# Dòng cuối bài ghi thẳng vào HTML tĩnh nên bot đọc được ngay (khác khối "Tin khác" bên dưới là do JS dựng).
RSTOP = set('cua cac nhung mot nhieu trong tren duoc khong cung voi tuy theo khi sau truoc nay nao van con lai thi la va the and for with from that this has have are was were will its into after over amid about than'.split())


def _tok(s):
    s = unicodedata.normalize('NFD', str(s or '').lower().replace('đ', 'd'))
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return {t for t in re.findall(r'[a-z0-9]+', s) if len(t) >= 3 and t not in RSTOP}


def related_corpus():
    """mọi bài đã đăng (tin + kiến thức) từ hai file index.json"""
    out = []
    for kind in ('news', 'learn'):
        K = KINDS[kind]
        for x in jload(os.path.join(ROOT, *K['idx']), {'items': []}).get('items', []):
            out.append({**x, 'kind': kind})
    return out


def _doc(x):
    return _tok(' '.join(str(x.get(lg, {}).get(k, '')) for lg in ('vi', 'en') for k in ('title', 'desc', 'lead')) + ' ' + ' '.join(str(k) for lg in ('vi', 'en') for k in (x.get(lg, {}).get('keywords') or [])))


def related_rank(a, kind, corpus=None):
    """xếp các bài cũ theo độ liên quan với bài a (điểm = tổng độ hiếm của từ chung + thưởng cùng đồng coin / cùng mục / cùng loại). Trả về [(điểm, bài)]"""
    corpus = [c for c in (corpus if corpus is not None else related_corpus()) if not (c['kind'] == kind and c['slug'] == a.get('slug'))]
    docs = [_doc(c) for c in corpus]
    df = {}
    for d in docs:
        for t in d: df[t] = df.get(t, 0) + 1
    me = _doc(a) | _tok(a.get('event'))
    rows = []
    for c, d in zip(corpus, docs):
        sc = sum(math.log(1 + len(docs) / df[t]) for t in me & d)
        if c.get('coin') and c.get('coin') == a.get('coin') and c['coin'] != 'BTC': sc += 1.5
        if c.get('cat') == a.get('cat'): sc += 0.5
        if c['kind'] == kind: sc += 1.0   # cùng loại (tin với tin, kiến thức với kiến thức) khớp độc giả hơn
        rows.append((round(sc, 2), c))
    rows.sort(key=lambda r: (r[0], r[1].get('ts', '')), reverse=True)
    return rows


def resolve_related(a, kind):
    rel = a.get('related')
    if not isinstance(rel, list) or not 1 <= len(rel) <= 3:
        die('thiếu "related": danh sách 1–3 bài liên quan dạng [{"kind":"news|learn","slug":"..."}] (bắt buộc). Gợi ý: python3 tools/news/publish.py related ART.json')
    have = {(c['kind'], c['slug']) for c in related_corpus()}
    out = []
    for r in rel:
        if not isinstance(r, dict) or r.get('kind') not in KINDS or not r.get('slug'): die('related: mỗi mục phải là {"kind":"news|learn","slug":"..."}')
        if (r['kind'], r['slug']) not in have: die('related: không có bài đã đăng "%s/%s" (xem danh sách bằng lệnh related)' % (r['kind'], r['slug']))
        if r['kind'] == kind and r['slug'] == slugify(a.get('slug', '')): die('related: không được trỏ về chính bài này')
        if (r['kind'], r['slug']) in [(o['kind'], o['slug']) for o in out]: die('related: trùng bài %s' % r['slug'])
        out.append({'kind': r['kind'], 'slug': r['slug']})
    return out


def related_lines(a, lg):
    """danh sách (chỉ số trong related, HTML dòng "Liên quan: <tiêu đề>" in nghiêng đậm); tiêu đề + địa chỉ lấy từ index nên luôn đúng ngôn ngữ"""
    by = {(c['kind'], c['slug']): c for c in related_corpus()}
    rows = []
    for i, r in enumerate(a.get('related') or [], 1):
        c = by.get((r['kind'], r['slug']))
        url = c and (c.get('ue') if lg == 'en' else c.get('u'))
        if not (c and url and (c.get(lg) or {}).get('title')): continue
        rows.append((i, '<strong><em>%s <a href="%s">%s</a></em></strong>' % ('Liên quan:' if lg == 'vi' else 'Related:', esc(url), esc(c[lg]['title']))))
    return rows


def _rel_points(body):
    """các điểm có thể chèn dòng Liên quan: ngay sau đoạn văn thường ở cấp ngoài cùng (không trong bảng/danh sách), không dính sát ảnh/dòng khác"""
    pts = []
    for m in re.finditer(r'<p(?:\s(?![^>]*\barl\b)[^>]*)?>(?!\s*\[\[(?:img|rel):)(.*?)</p>', body, re.S | re.I):
        head = body[:m.start()]
        depth = sum(len(re.findall('<%s[ >]' % t, head, re.I)) - len(re.findall('</%s>' % t, head, re.I)) for t in ('ul', 'ol', 'table', 'blockquote'))
        if depth > 0: continue
        if re.match(r'\s*<p(?:\s+class="arl ain")?>\s*(?:\[\[(?:img|rel):|<strong><em>)', body[m.end():], re.I): continue   # sát ảnh / dòng Liên quan khác
        if re.search(r'<p class="arl ain">(?:(?!</p>).)*</p>\s*$', head, re.S): continue   # ngay sau một dòng Liên quan
        pts.append(m.end())
    return pts


def place_related(a, lg, body):
    """Luật vị trí (anh Thái, 03/11/2026): 1 bài liên quan -> cuối bài. Từ 2 bài: bài có <p>[[rel:N]]</p> nằm ngay dưới đoạn văn liên quan;
    bài không có đoạn văn khớp thì rải đều giữa thân bài, riêng bài cuối cùng nằm cuối bài (không dồn hết xuống cuối).
    Trả về (body đã chèn dòng giữa bài, HTML các dòng cuối bài)."""
    lines = related_lines(a, lg); n = len(a.get('related') or [])
    ln = lambda h, ain: '<p class="arl%s">%s</p>' % (' ain' if ain else '', h)
    marked = {int(x) for x in REL_MARK.findall(body)}
    by = dict(lines)
    body = REL_MARK.sub(lambda m: ln(by[int(m.group(1))], True) if int(m.group(1)) in by else '', body)
    rest = [(i, h) for i, h in lines if i not in marked]
    tail = []
    if n < 2 or not rest:
        tail = rest
    else:
        tail = [rest[-1]]; mid = rest[:-1]
        pts = _rel_points(body)
        if mid and pts:
            ins = {}
            for j, (i, h) in enumerate(mid, 1):
                k = min(max(round(j * len(pts) / (len(mid) + 1)) - 1, 0), len(pts) - 1)
                while k in ins and k + 1 < len(pts): k += 1
                ins[k] = h
            for k in sorted(ins, reverse=True):
                body = body[:pts[k]] + '\n' + ln(ins[k], True) + body[pts[k]:]
        else:
            tail = mid + tail
    return body, '\n'.join(ln(h, False) for i, h in tail)


def related_cmd(path):
    kind = 'learn' if '--kind' in sys.argv and sys.argv[sys.argv.index('--kind') + 1] == 'learn' else 'news'
    try:
        a = json.load(open(path, encoding='utf-8'))
    except Exception as e:
        die('không đọc được %s: %s' % (path, e))
    a['slug'] = slugify(a.get('slug', ''))
    print('Bài liên quan gợi ý (điểm cao = khớp hơn). Link trong câu văn chỉ dùng khi điểm cao VÀ ý thật sự khớp câu đó; dòng cuối bài thì chọn 1–3 bài khớp nhất, nới lỏng được.')
    for sc, c in related_rank(a, kind)[:8]:
        print('%5.1f  %-5s %s  %s\n         vi: %s  %s\n         en: %s  %s' % (sc, c['kind'], c['ts'][:10], c['slug'], c['u'], c['vi']['title'], c.get('ue', ''), c['en']['title']))


def related_backfill():
    n = 0
    for kind, sub in (('news', 'articles'), ('learn', 'learn_articles')):
        d = os.path.join(KIT, sub)
        for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
            ap = os.path.join(d, f); aa = json.load(open(ap, encoding='utf-8'))
            if aa.get('related'): continue
            pick = [c for sc, c in related_rank(aa, kind)[:2]]
            aa['related'] = [{'kind': c['kind'], 'slug': c['slug']} for c in pick]
            jsave(ap, aa); n += 1
            print('%-5s %-60s -> %s' % (kind, aa['slug'][:60], ', '.join(c['slug'][:40] for c in pick)))
    print('Đã điền "related" cho %d bài. Chạy tiếp: python3 tools/news/publish.py rebuild' % n)


def load(path, kind='news'):
    try:
        a = json.load(open(path, encoding='utf-8'))
    except Exception as e:
        die('không đọc được %s: %s' % (path, e))
    cats = KINDS[kind]['cats']
    if kind == 'learn' and isinstance(a.get('vi'), dict): a.setdefault('event', a['vi'].get('title', ''))
    for k in REQ:
        if not a.get(k): die('thiếu trường "%s"' % k)
    if a['cat'] not in cats: die('cat phải là một trong %s' % list(cats))
    # mục chính (cat) theo ý chính nhất của bài; cats = các mục liên quan khác (tuỳ chọn), bài hiện ở bộ lọc của mọi mục trong cats
    extra = a.get('cats') or []
    if not isinstance(extra, list) or any(c not in cats for c in extra): die('cats phải là danh sách các mục trong %s' % list(cats))
    a['cats'] = [a['cat']] + [c for c in dict.fromkeys(extra) if c != a['cat']]
    for lg in ('vi', 'en'):
        for k in REQ_L:
            if not a[lg].get(k): die('thiếu %s.%s' % (lg, k))
        a[lg]['body_html'] = clean_body(a[lg]['body_html'])
        bl = a[lg].get('bullets')
        if kind == 'news' and not bl: die('thiếu %s.bullets (đúng 3 câu tóm tắt, hiển thị ở khối "Tóm tắt nhanh")' % lg)
        if bl is not None:
            if not isinstance(bl, list) or not all(isinstance(x, str) for x in bl): die('%s.bullets phải là danh sách chuỗi' % lg)
            if len(bl) != 3: die('%s.bullets cần đúng 3 ý (hiện có %d)' % (lg, len(bl)))
            for x in bl:
                if not 25 <= len(x.strip()) <= 220: die('%s.bullets: mỗi ý dài 25–220 ký tự (có ý dài %d: "%s")' % (lg, len(x.strip()), x[:40]))
        txt = ' '.join([str(a[lg].get(k, '')) for k in REQ_L] + list(bl or []))
        cap = ' '.join(str(im.get('caption_' + lg, '')) for im in (a.get('images') or []))
        m = NO_SOURCE.search(txt)
        if m: die('bản %s nhắc tên nguồn/cụm ghi nguồn: "%s" — viết lại, bài không được ghi nguồn' % (lg, m.group(0)))
        if len(a[lg]['seo_title']) > 65: die('%s.seo_title dài %d ký tự (tối đa 65)' % (lg, len(a[lg]['seo_title'])))
        if not 110 <= len(a[lg]['desc']) <= 160: die('%s.desc dài %d ký tự (cần 110–160)' % (lg, len(a[lg]['desc'])))
        n = words(a[lg]['body_html'])
        if n < 350: die('%s.body_html chỉ %d từ (tối thiểu 350)' % (lg, n))
        if a[lg]['body_html'].count('<h2') < 2: die('%s.body_html cần ít nhất 2 tiêu đề phụ <h2>' % lg)
    try:
        datetime.fromisoformat(a['ts'])
    except Exception:
        die('ts phải là ISO 8601, ví dụ 2026-10-27T14:05:00+07:00')
    img = a.get('image') or None
    if img: check_img(img, kind, 'image', a.get('slug', ''))
    imgs = a.get('images') or []
    for i, im in enumerate(imgs, 1): check_img(im, kind, 'images[%d]' % i, a.get('slug', ''))
    a['images'] = imgs
    if not img:
        die('bài bắt buộc có ảnh bìa "image" (ảnh thật minh họa đúng ý chính; không dùng thẻ chữ)')
    marks = {}
    for lg in ('vi', 'en'):
        ms = [int(x) for x in IMG_MARK.findall(a[lg]['body_html'])]
        if any(m < 1 or m > len(imgs) for m in ms): die('%s.body_html có [[img:N]] vượt số ảnh trong "images" (%d ảnh)' % (lg, len(imgs)))
        if len(set(ms)) != len(ms): die('%s.body_html dùng trùng một [[img:N]]' % lg)
        marks[lg] = set(ms)
        if kind == 'news':
            miss = [i for i in range(1, len(imgs) + 1) if i not in ms]
            if miss: die('%s.body_html thiếu <p>[[img:%d]]</p> cho ảnh trong "images" (mỗi ảnh phải được đặt vào bài)' % (lg, miss[0]))
            # tối thiểu 2 đoạn văn giữa hai ảnh để ảnh không dồn cục
            parts = re.split(r'<p>\s*\[\[img:\d+\]\]\s*</p>', a[lg]['body_html'])
            for mid in parts[1:-1]:
                if len(re.findall(r'<p[ >]', mid)) < 2: die('%s.body_html: giữa hai ảnh phải có ít nhất 2 đoạn văn' % lg)
            for i, im in enumerate(imgs, 1):
                if not fig_parts(im, lg)[0]: die('images[%d] thiếu caption_%s (ghi ảnh thể hiện điều gì; credit không thay được chú thích)' % (i, lg))
    if marks['vi'] != marks['en']: die('bản Việt và bản Anh phải dùng cùng các [[img:N]]')
    # link nội bộ (cả hai bản): phải bắt đầu bằng "/" và trỏ tới trang có thật (không có trang /en/tools.html, /en/cong-cu.html...: trang chính dùng chung địa chỉ cho cả hai ngôn ngữ)
    hv = re.findall(r'href\s*=\s*["\']([^"\']+)["\']', a['vi']['body_html'])
    he = re.findall(r'href\s*=\s*["\']([^"\']+)["\']', a['en']['body_html'])
    for h in hv + he:
        if not h.startswith('/') or h.startswith('//'): die('link nội bộ phải bắt đầu bằng một dấu / (ví dụ /cong-cu): "%s"' % h)
        t = h.split('#')[0].split('?')[0].strip('/')
        ok = os.path.exists(os.path.join(ROOT, t)) or os.path.exists(os.path.join(ROOT, t + '.html')) if t else True
        if not ok: die('link nội bộ trỏ tới trang không tồn tại: "%s"' % h)
    # link trong câu văn: bản Việt trỏ trang Việt, bản Anh trỏ trang Anh (bài tin/kiến thức có địa chỉ riêng cho từng ngôn ngữ)
    for h in hv:
        if h.startswith('/en/') or h == '/en': die('bản Việt không được link sang trang Anh: "%s" (dùng địa chỉ "u" của bài trong tin/index.json)' % h)
    for h in he:
        if re.match(r'/(tin-tuc|kien-thuc|tin|hoc)/', h): die('bản Anh không được link sang trang Việt: "%s" (dùng địa chỉ "ue", dạng /en/news/... hoặc /en/learn/...)' % h)
    a['related'] = resolve_related(a, kind)
    rm = {}
    for lg in ('vi', 'en'):
        ms = [int(x) for x in REL_MARK.findall(a[lg]['body_html'])]
        if ms and len(a['related']) < 2: die('%s.body_html có [[rel:N]] nhưng chỉ có 1 bài liên quan: 1 bài thì đặt ở cuối bài, bỏ [[rel:N]]' % lg)
        if any(m < 1 or m > len(a['related']) for m in ms): die('%s.body_html có [[rel:N]] vượt số bài trong "related" (%d bài)' % (lg, len(a['related'])))
        if len(set(ms)) != len(ms): die('%s.body_html dùng trùng một [[rel:N]]' % lg)
        rm[lg] = set(ms)
    if rm['vi'] != rm['en']: die('bản Việt và bản Anh phải dùng cùng các [[rel:N]] (cùng bài ở cùng ý)')
    a['slug'] = slugify(a['slug']) or slugify(a['vi']['title'])
    a['coin'] = re.sub(r'[^A-Z0-9]', '', str(a.get('coin') or 'BTC').upper()) or 'BTC'
    return a


TF_RE = re.compile(r'(\bkhung\b|\btimeframe\b|\b(daily|hourly|weekly|monthly|intraday)\b|\d+\s*-?\s*(giờ|phút|ngày|tuần|tháng|hours?|minutes?|days?|weeks?|months?|[hmdw])\b|\b(giờ|ngày|tuần|tháng)\b)', re.I)
GENERIC_CAP = re.compile(r'^\W*(ảnh|hình|hình ảnh|biểu đồ|biểu đồ giá|ảnh minh h[oọ]a|chart|price chart|image|photo|illustration|stock photo)\W*$', re.I)


def onpage_check(a, kind='news'):
    """Luật on-page 04/11/2026 cho BÀI MỚI (check / publish / learn-check / learn-publish). Không chạy khi rebuild nên bài cũ không bị đụng.
    <title> hiển thị = seo_title + ' | CoinHammy' (12 ký tự) nên seo_title 38–48 -> thẻ 50–60; desc 150–160; seo_title khác H1;
    slug và slug_en 3–5 từ; chú thích ảnh (chart: nêu khung thời gian + mức giá); ảnh bìa sau khi cắt 16:9 + JPEG 84 ≤ 150 KB."""
    for lg in ('vi', 'en'):
        L = a[lg]; st = L['seo_title'].strip(); n = len(st)
        if not 38 <= n <= 48: die('%s.seo_title dài %d ký tự — cần 38–48 (thẻ <title> hiển thị = seo_title + " | CoinHammy" phải 50–60 ký tự): "%s"' % (lg, n, st))
        if st.casefold() == L['title'].strip().casefold(): die('%s.seo_title giống hệt %s.title (H1) — phần trước dấu "|" phải khác H1, viết lại bằng chữ khác' % (lg, lg))
        d = len(L['desc'].strip())
        if not 150 <= d <= 160: die('%s.desc dài %d ký tự — cần 150–160' % (lg, d))
    slug = a['slug']; ns = len([w for w in slug.split('-') if w])
    if not 3 <= ns <= 5: die('slug "%s" có %d từ — địa chỉ bản Việt của bài mới phải 3–5 từ (không áp dụng cho bài đã đăng; không đổi địa chỉ cũ)' % (slug, ns))
    se = str(a.get('slug_en') or '')
    if not se: die('thiếu "slug_en" — bài mới phải khai báo địa chỉ bản Anh 3–5 từ (không dấu, gạch ngang), nếu không publish.py tự tạo từ en.title và dài 8–10 từ')
    if not re.fullmatch(r'[a-z0-9]+(-[a-z0-9]+)*', se): die('slug_en "%s" chỉ gồm chữ thường không dấu, số và dấu gạch ngang' % se)
    ne = len(se.split('-'))
    if not 3 <= ne <= 5: die('slug_en "%s" có %d từ — cần 3–5 từ' % (se, ne))
    if se in taken_en(): die('slug_en "%s" đã có bài khác dùng — đặt địa chỉ Anh khác' % se)
    cover = a.get('image') or {}
    items = [('image', cover)] + [('images[%d]' % i, im) for i, im in enumerate(a.get('images') or [], 1)]
    for name, im in items:
        chart = str(im.get('license', '')).lower() == 'chart'
        body = name != 'image'
        for lg in ('vi', 'en'):
            cap = str(im.get('caption_' + lg) or '').strip()
            if not cap and (chart or body):
                die('%s.caption_%s bắt buộc%s — hiện thành <figcaption> dưới ảnh (credit không được in làm chú thích)' % (
                    name, lg, ' (ảnh biểu đồ: nêu khung thời gian và mức giá nhìn thấy trên ảnh)' if chart else ''))
            if not cap: continue
            if GENERIC_CAP.match(cap): die('%s.caption_%s quá chung chung ("%s") — nói ảnh cho thấy gì cụ thể' % (name, lg, cap))
            if chart:
                if len(cap) < 25: die('%s.caption_%s quá ngắn (%d ký tự) — ảnh biểu đồ cần nêu khung thời gian và mức giá/mốc: "%s"' % (name, lg, len(cap), cap))
                if not re.search(r'\d', TF_RE.sub(' ', cap)): die('%s.caption_%s thiếu mức giá/mốc số nhìn thấy trên ảnh: "%s"' % (name, lg, cap))
                if not TF_RE.search(cap): die('%s.caption_%s thiếu khung thời gian (ví dụ "khung 4 giờ", "4-hour chart", "daily"): "%s"' % (name, lg, cap))
    f = cover.get('file')
    if f:
        try:
            sz = framed_size(f, cover.get('focus'))
        except ImportError:
            sz = 0
        if sz > 150 * 1024: die('ảnh bìa sau khi cắt 16:9 và mã hoá JPEG chất lượng 84 nặng %d KB (> 150 KB) — nén bằng nen_bia.py hoặc chọn ảnh ít chi tiết hơn' % (sz // 1024))


def fmt_time(ts, lg):
    d = datetime.fromisoformat(ts).astimezone(VN)
    return d.strftime('%d/%m/%Y · %H:%M') if lg == 'vi' else d.strftime('%b %d, %Y · %H:%M') + ' (GMT+7)'


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


def vpath(a, kind):
    """đường dẫn trang Việt: bài cũ giữ tin/ hoc/, bài mới nằm trong tin-tuc/ kien-thuc/"""
    return '/%s/%s' % (a.get('dir') or KINDS[kind]['pfx'], a['slug'])


def epath(a, kind):
    return '/%s/%s' % (KINDS[kind]['edir'], a['slug_en'])


def redirects(rows):
    """_redirects của Cloudflare Pages: địa chỉ cũ /tin/<slug>, /hoc/<slug> chuyển vĩnh viễn (301) sang địa chỉ mới"""
    out = ['# Tự sinh bởi publish.py rebuild — đừng sửa tay. Địa chỉ cũ của bài -> địa chỉ mới (301).']
    for a, kind in sorted(rows, key=lambda r: (r[1], r[0]['slug'])):
        pfx = KINDS[kind]['pfx']; new = vpath(a, kind)
        out.append('/%s/%s %s 301' % (pfx, a['slug'], new)); out.append('/%s/%s.html %s 301' % (pfx, a['slug'], new))
    open(os.path.join(ROOT, '_redirects'), 'w', encoding='utf-8').write('\n'.join(out) + '\n')


STOP_EN = {'a', 'an', 'and', 'as', 'at', 'by', 'for', 'from', 'in', 'into', 'is', 'its', 'of', 'on', 'or', 'over', 'the', 'to', 'with', 'but', 'than', 'that', 'after', 'before', 'mid', 'way', 'while', 'amid', 'yet'}


def slug_en_for(a, taken):
    """địa chỉ bản Anh: lấy từ tiêu đề tiếng Anh, không trùng bài khác; đã có thì giữ nguyên (không đổi địa chỉ đã gửi Google)"""
    if a.get('slug_en'): return a['slug_en']
    ttl = re.sub(r"(?<=\d),(?=\d)|['\u2019]", '', a['en']['title'])     # 80,000 -> 80000 ; Moody's -> Moodys
    full = slugify(ttl.replace('%', ' percent ').replace('$', ' '))
    base = full if len(full) <= 60 else full[:61].rsplit('-', 1)[0]            # cắt ở ranh giới từ, không cụt giữa chữ
    parts = base.split('-')
    while len(parts) > 3 and parts[-1] in STOP_EN: parts.pop()                 # không kết thúc bằng từ nối (as, to, in, its...)
    base = '-'.join(parts)
    s, n = base, 2
    while s in taken:
        s = '%s-%d' % (base, n); n += 1
    return s


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


def item_paths(a, kind):
    return {'u': vpath(a, kind), 'ue': epath(a, kind)}


def jload(p, default):
    try:
        return json.load(open(p, encoding='utf-8'))
    except Exception:
        return default


def jsave(p, obj):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + '.tmp'
    json.dump(obj, open(tmp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    os.replace(tmp, p)


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


def taken_en():
    """mọi địa chỉ bản Anh đã dùng (tin + kiến thức) để không trùng"""
    s = set()
    for pfx in ('tin', 'hoc'):
        for x in jload(os.path.join(ROOT, pfx, 'index.json'), {'items': []})['items']:
            if x.get('ue'): s.add(x['ue'].rsplit('/', 1)[-1])
    return s


def today_rows():
    log = jload(os.path.join(KIT, 'log.json'), [])
    d = datetime.now(VN).strftime('%Y-%m-%d')
    return [x for x in log if x.get('ts', '')[:10] == d]


def today():
    rows = today_rows(); now = datetime.now(VN)
    print('Hôm nay %s (%s): đã đăng %d/%d bài.' % (now.strftime('%d/%m/%Y'), ['T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'CN'][now.weekday()], len(rows), DAILY_CAP))
    if now.weekday() >= 5: print('Cuối tuần: không đăng bài.')
    for x in rows: print('- %s | %s | %s' % (x['ts'][11:16], x['cat'], x['title_vi']))


def item_img(a, lg, kind='news'):
    im = a.get('image')
    return img_url(a, im, 'h', lg, kind) if im else ''


def after_publish():
    """sau khi đăng bài: tạo ảnh thu nhỏ cho thẻ bài + làm mới khối tin điền sẵn ở 4 trang danh sách (nhanh trang đầu).
    Lỗi gì ở đây cũng KHÔNG làm hỏng bài đã đăng: trang vẫn chạy bằng JS như cũ, chỉ chậm hơn và check_pages sẽ cảnh báo."""
    import subprocess
    try:
        n = thumbs.ensure()
        if n: print('Đã tạo %d ảnh thu nhỏ' % n)
    except Exception as e:
        print('CẢNH BÁO: không tạo được ảnh thu nhỏ (%s) — chạy lại: python3 tools/news/thumbs.py' % e)
    try:
        r = subprocess.run([sys.executable, '-I', os.path.join(ROOT, 'tools', 'prerender_i18n.py'), '--lists'], cwd=ROOT, capture_output=True, text=True, timeout=240)
        if r.returncode: print('CẢNH BÁO: chưa làm mới được khối tin điền sẵn — chạy lại: python3 tools/prerender_i18n.py --lists  (%s)' % ((r.stderr.strip().splitlines() or ['?'])[-1][:140]))
        else: print('Đã làm mới khối tin điền sẵn ở 4 trang danh sách')
    except Exception as e:
        print('CẢNH BÁO: chưa làm mới được khối tin điền sẵn (%s) — chạy lại: python3 tools/prerender_i18n.py --lists' % e)
    try:
        st = paginate()
        print('Phân trang danh sách: %s' % ('đã cập nhật ' + ', '.join(st) if st else 'không đổi'))
    except SystemExit:
        print('CẢNH BÁO: chưa cập nhật được phân trang — chạy lại: python3 tools/news/publish.py pages')
    except Exception as e:
        print('CẢNH BÁO: chưa cập nhật được phân trang (%s) — chạy lại: python3 tools/news/publish.py pages' % e)


def publish(path):
    a = load(path)
    onpage_check(a, 'news')
    if not os.environ.get('FORCE'):
        if datetime.now(VN).weekday() >= 5: die('cuối tuần không đăng bài (đặt FORCE=1 nếu anh Thái bảo đăng thủ công)')
        if len(today_rows()) >= DAILY_CAP: die('hôm nay đã đủ %d bài — không đăng thêm' % DAILY_CAP)
    idx = jload(os.path.join(ROOT, 'tin', 'index.json'), {'items': []})
    taken = {x['slug'] for x in idx['items']}
    base, n = a['slug'], 2
    while a['slug'] in taken:
        a['slug'] = '%s-%d' % (base, n); n += 1
    used, seen = ledger_check(a)
    localize_news(a)
    a['dir'] = KINDS['news']['vdir']; a['slug_en'] = slug_en_for(a, taken_en())
    write_article(a, 'news')
    for sx in seen: used[sx] = a['slug']
    jsave(LEDGER, used)
    jsave(os.path.join(KIT, 'articles', a['slug'] + '.json'), a)
    item = {'slug': a['slug'], 'slug_en': a['slug_en'], **item_paths(a, 'news'), 'cat': a['cat'], 'coin': a['coin'], 'ts': a['ts'], 'img': item_img(a, 'vi'), 'img_en': item_img(a, 'en'),
            **({'cats': a['cats']} if len(a['cats']) > 1 else {}),
            'vi': {'title': a['vi']['title'], 'desc': a['vi']['desc']}, 'en': {'title': a['en']['title'], 'desc': a['en']['desc']}}
    idx['items'] = sorted([item] + idx['items'], key=lambda x: x['ts'], reverse=True)[:500]
    idx['updated'] = datetime.now(VN).isoformat(timespec='seconds')
    jsave(os.path.join(ROOT, 'tin', 'index.json'), idx)
    log = jload(os.path.join(KIT, 'log.json'), [])
    cut = (datetime.now(VN) - timedelta(days=30)).isoformat()
    log = [x for x in log if x.get('ts', '') >= cut]
    log.append({'ts': datetime.now(VN).isoformat(timespec='seconds'), 'published': a['ts'], 'slug': a['slug'], 'cat': a['cat'],
                'event': a['event'], 'title_vi': a['vi']['title'], 'title_en': a['en']['title'], 'src_urls': a.get('src_urls', [])})
    jsave(os.path.join(KIT, 'log.json'), log)
    sitemap(idx['items'])
    print('ĐÃ XUẤT BẢN: %s.html + %s.html  (%d từ VI, %d từ EN)' % (vpath(a, 'news')[1:], epath(a, 'news')[1:], words(a['vi']['body_html']), words(a['en']['body_html'])))
    print('URL Việt: %s%s\nURL Anh:  %s%s' % (SITE, vpath(a, 'news'), SITE, epath(a, 'news')))
    after_publish()


def localize_image(a):
    """Copy a local image into hoc/img/ (re-encoded to a web-sized JPEG when Pillow is available) and point image.url at it."""
    img = a.get('image')
    if not img or not img.get('file'): return
    os.makedirs(os.path.join(ROOT, 'hoc', 'img'), exist_ok=True)
    src = img['file']; ext = os.path.splitext(src)[1].lower().replace('jpeg', 'jpg')
    try:
        from PIL import Image
        im = Image.open(src); im.load()
        if im.mode not in ('RGB', 'L'): im = im.convert('RGB')
        if im.width > 1600: im = im.resize((1600, round(im.height * 1600 / im.width)))
        ext = '.jpg'; dst = os.path.join(ROOT, 'hoc', 'img', a['slug'] + ext); im.save(dst, 'JPEG', quality=84, optimize=True)
    except ImportError:
        import shutil; dst = os.path.join(ROOT, 'hoc', 'img', a['slug'] + ext); shutil.copyfile(src, dst)
    img['url'] = '/hoc/img/%s%s' % (a['slug'], ext); img.pop('file', None)


def learn_rows():
    return jload(os.path.join(KIT, 'learn_log.json'), [])


def learn_today():
    d = datetime.now(VN).strftime('%Y-%m-%d'); rows = [x for x in learn_rows() if x.get('ts', '')[:10] == d]
    print('Hôm nay %s: %d bài Kiến thức (tối đa 1/ngày).' % (datetime.now(VN).strftime('%d/%m/%Y'), len(rows)))
    for x in rows: print('- %s | %s | %s' % (x['ts'][11:16], x['cat'], x['title_vi']))
    return rows


def learn_recent(days):
    cut = (datetime.now(VN) - timedelta(days=days)).isoformat(); rows = [x for x in learn_rows() if x.get('ts', '') >= cut]
    print('%d bài Kiến thức trong %d ngày qua:' % (len(rows), days))
    for x in reversed(rows): print('- %s | %s | %s' % (x['ts'][:10], x['cat'], x['title_vi']))


def learn_publish(path):
    a = load(path, 'learn')
    onpage_check(a, 'learn')
    if not os.environ.get('FORCE') and learn_today(): die('hôm nay đã có bài Kiến thức — không đăng thêm')
    idx = jload(os.path.join(ROOT, 'hoc', 'index.json'), {'items': []})
    taken = {x['slug'] for x in idx['items']}
    base, n = a['slug'], 2
    while a['slug'] in taken:
        a['slug'] = '%s-%d' % (base, n); n += 1
    used, seen = ledger_check(a)
    localize_news(a, 'learn')
    a['dir'] = KINDS['learn']['vdir']; a['slug_en'] = slug_en_for(a, taken_en())
    for sx in seen: used[sx] = a['slug']
    jsave(LEDGER, used)
    write_article(a, 'learn')
    jsave(os.path.join(KIT, 'learn_articles', a['slug'] + '.json'), a)
    item = {'slug': a['slug'], 'slug_en': a['slug_en'], **item_paths(a, 'learn'), 'cat': a['cat'], 'coin': a['coin'], 'ts': a['ts'], 'img': (a.get('image') or {}).get('url', ''),
            'vi': {'title': a['vi']['title'], 'desc': a['vi']['desc']}, 'en': {'title': a['en']['title'], 'desc': a['en']['desc']}}
    idx['items'] = sorted([item] + idx['items'], key=lambda x: x['ts'], reverse=True)[:1000]
    idx['updated'] = datetime.now(VN).isoformat(timespec='seconds')
    jsave(os.path.join(ROOT, 'hoc', 'index.json'), idx)
    log = [x for x in learn_rows() if x.get('ts', '') >= (datetime.now(VN) - timedelta(days=400)).isoformat()]
    log.append({'ts': datetime.now(VN).isoformat(timespec='seconds'), 'slug': a['slug'], 'cat': a['cat'], 'title_vi': a['vi']['title'], 'title_en': a['en']['title']})
    jsave(os.path.join(KIT, 'learn_log.json'), log)
    sitemap(jload(os.path.join(ROOT, 'tin', 'index.json'), {'items': []})['items'])
    print('ĐÃ XUẤT BẢN KIẾN THỨC: %s.html + %s.html  (%d từ VI, %d từ EN)' % (vpath(a, 'learn')[1:], epath(a, 'learn')[1:], words(a['vi']['body_html']), words(a['en']['body_html'])))
    print('URL Việt: %s%s\nURL Anh:  %s%s' % (SITE, vpath(a, 'learn'), SITE, epath(a, 'learn')))
    after_publish()


def recent(hours):
    log = jload(os.path.join(KIT, 'log.json'), [])
    cut = (datetime.now(VN) - timedelta(hours=hours)).isoformat()
    rows = [x for x in log if x.get('ts', '') >= cut]
    print('%d bài trong %d giờ qua (mới nhất trước):' % (len(rows), hours))
    for x in reversed(rows):
        print('- %s | %s | %s\n  sự kiện: %s\n  nguồn: %s' % (x['ts'], x['cat'], x['title_vi'], x['event'], ' '.join(x.get('src_urls', []))))


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    if cmd == 'recent':
        h = int(sys.argv[sys.argv.index('--hours') + 1]) if '--hours' in sys.argv else 48
        recent(h)
    elif cmd == 'today':
        today()
    elif cmd == 'learn-today':
        learn_today()
    elif cmd == 'learn-recent':
        learn_recent(int(sys.argv[sys.argv.index('--days') + 1]) if '--days' in sys.argv else 14)
    elif cmd == 'learn-check' and len(sys.argv) > 2:
        a = load(sys.argv[2], 'learn'); onpage_check(a, 'learn'); ledger_check(a); print('HỢP LỆ: slug=%s, %d từ VI, %d từ EN' % (a['slug'], words(a['vi']['body_html']), words(a['en']['body_html'])))
    elif cmd == 'learn-publish' and len(sys.argv) > 2:
        learn_publish(sys.argv[2])
    elif cmd == 'check' and len(sys.argv) > 2:
        a = load(sys.argv[2]); onpage_check(a, 'news'); ledger_check(a); print('HỢP LỆ: slug=%s, %d từ VI, %d từ EN' % (a['slug'], words(a['vi']['body_html']), words(a['en']['body_html'])))
    elif cmd == 'publish' and len(sys.argv) > 2:
        publish(sys.argv[2])
    elif cmd == 'en-check':
        st = en_lists(check=True) + en_pages.build(check=True); print('Trang tiếng Anh (danh sách, xếp hạng, so sánh, đánh giá) lệch so với bản Việt: ' + (', '.join(st) if st else 'không')); sys.exit(1 if st else 0)
    elif cmd == 'pages':
        st = paginate(check='--check' in sys.argv); print('Phân trang danh sách (trang 2 trở đi + hàng nút số trang): ' + (('LỆCH: ' if '--check' in sys.argv else 'đã cập nhật ') + ', '.join(st) if st else 'không đổi'))
        if '--check' not in sys.argv: sitemap(jload(os.path.join(ROOT, 'tin', 'index.json'), {'items': []})['items'])
        sys.exit(1 if st and '--check' in sys.argv else 0)
    elif cmd == 'related' and len(sys.argv) > 2:
        related_cmd(sys.argv[2])
    elif cmd == 'related-backfill':
        related_backfill()
    elif cmd == 'rebuild':
        n = 0; used_en = taken_en(); REDIR = []
        for kind, sub in (('news', 'articles'), ('learn', 'learn_articles')):
            K = KINDS[kind]; d = os.path.join(KIT, sub); ip = os.path.join(ROOT, K['pfx'], 'index.json'); idx = jload(ip, {'items': []})
            by = {x['slug']: x for x in idx['items']}
            for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
                ap = os.path.join(d, f); aa = json.load(open(ap, encoding='utf-8')); dirty = False
                if any(x.get('file') for x in [aa.get('image') or {}] + list(aa.get('images') or [])):
                    used, seen = ledger_check(aa); localize_news(aa, kind); dirty = True
                    for sx in seen: used[sx] = aa['slug']
                    jsave(LEDGER, used)
                it = by.get(aa['slug'])
                if not aa.get('slug_en'):   # bài cũ: lấy địa chỉ Anh một lần rồi giữ cố định
                    aa['slug_en'] = (it or {}).get('slug_en') or slug_en_for(aa, used_en); dirty = True
                used_en.add(aa['slug_en'])
                if aa.get('dir') != K['vdir']: aa['dir'] = K['vdir']; dirty = True   # mọi bài (kể cả bài cũ) nằm ở thư mục Việt chuẩn
                if dirty: jsave(ap, aa)
                write_article(aa, kind); n += 1
                old = os.path.join(ROOT, K['pfx'], aa['slug'] + '.html')   # trang cũ ở tin/ hoc/ -> đã chuyển, chỉ còn chuyển hướng 301
                if os.path.exists(old): os.remove(old)
                REDIR.append((aa, kind))
                if it:
                    it.update({'slug_en': aa['slug_en'], **item_paths(aa, kind)}); it['img'] = (aa.get('image') or {}).get('url', '') if kind == 'learn' else item_img(aa, 'vi')
                    if kind == 'news': it['img_en'] = item_img(aa, 'en')
                    it.pop('rt', None)
            if idx['items']: jsave(ip, idx)
        redirects(REDIR)
        render_404()
        en_lists()
        en_pages.build()
        sitemap(jload(os.path.join(ROOT, 'tin', 'index.json'), {'items': []})['items'])
        print('Đã dựng lại %d bài (mỗi bài 2 trang: Việt + Anh) và 2 trang danh sách tiếng Anh.' % n)
        after_publish()
    else:
        print(__doc__)

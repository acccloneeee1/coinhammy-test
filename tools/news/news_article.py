"""Đọc và kiểm một bài (JSON): trường bắt buộc, quy tắc on-page, địa chỉ tiếng Anh.
Tách từ publish.py; chạy từ thư mục gốc của kho (xem publish.py)."""

import json
import os
import re
from datetime import datetime

from news_core import IMG_MARK, KINDS, NO_SOURCE, REL_MARK, REQ, REQ_L, ROOT, die, jload, slugify
from news_images import check_img, fig_parts, framed_size
from news_related import resolve_related


def clean_body(h):
    """Allow only simple article markup. External links are removed (text kept); internal site links stay."""
    h = re.sub(r'(?is)<(script|style|iframe|object|embed|form)[^>]*>.*?</\1>', '', h)
    h = re.sub(r'(?i)\son\w+\s*=\s*("[^"]*"|\'[^\']*\'|[^\s>]+)', '', h)
    h = re.sub(r'(?is)<a\s[^>]*href\s*=\s*["\']\s*(https?:)?//[^"\']*["\'][^>]*>(.*?)</a>', r'\2', h)
    h = re.sub(r'(?i)</?(?!(p|h2|h3|ul|ol|li|strong|em|b|i|blockquote|a|br|table|thead|tbody|tr|th|td)\b)[a-z][^>]*>', '', h)
    return h.strip()


def words(h):
    return len(re.sub(r'<[^>]+>', ' ', h).split())


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


def taken_en():
    """mọi địa chỉ bản Anh đã dùng (tin + kiến thức) để không trùng"""
    s = set()
    for pfx in ('tin', 'hoc'):
        for x in jload(os.path.join(ROOT, pfx, 'index.json'), {'items': []})['items']:
            if x.get('ue'): s.add(x['ue'].rsplit('/', 1)[-1])
    return s

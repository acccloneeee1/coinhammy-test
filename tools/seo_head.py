#!/usr/bin/env python3
"""Chèn khối SEO (title, description, canonical, Open Graph, Twitter, JSON-LD trang chủ) vào các trang chính.
Chạy lại bao nhiêu lần cũng được (khối nằm giữa <!--seo--> ... <!--/seo-->).
  python3 tools/seo_head.py              # tất cả trang chính trong repo
  python3 tools/seo_head.py file.html..  # chỉ các file chỉ định (vd bieu-do.html sinh ra từ build)
Tên miền lấy từ tools/news/config.json."""
import html, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lang_boot, faq_ld, breadcrumb, header

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = json.load(open(os.path.join(ROOT, 'tools', 'news', 'config.json')))['site'].rstrip('/')
IMG = SITE + '/tin/og-default.png'

PAGES = {
 'index.html': ('', 'CoinHammy: Công cụ tính vị thế, hỗ trợ mạnh mẽ cho trader',
   'Công cụ miễn phí cho trader phái sinh: tính khối lượng lệnh, ký quỹ, giá thanh lý, chốt lời cắt lỗ; kèm tin tức crypto, kiến thức và xếp hạng sàn Futures.'),
 'cong-cu.html': ('cong-cu', 'Tính vị thế Futures: ký quỹ, giá thanh lý, PnL | CoinHammy',
   'Tính vị thế Futures miễn phí: biết trước khối lượng lệnh, ký quỹ, giá thanh lý ước tính và lãi/lỗ tại các mức chốt lời, cắt lỗ ngay trước khi vào lệnh.'),
 'bieu-do.html': ('bieu-do', 'Tính vị thế nâng cao kèm biểu đồ nến trực tiếp | CoinHammy',
   'Tính vị thế nâng cao CoinHammy: biểu đồ nến trực tiếp kèm RSI, sổ lệnh, giá thanh lý, chốt lời và cắt lỗ cho futures. Công cụ miễn phí, nhập số là có kết quả.'),
 'quy-doi.html': ('quy-doi', 'Quy đổi tiền và coin: VND, USD, USDT, BTC, ETH | CoinHammy',
   'Quy đổi nhanh giữa tiền pháp định, stablecoin và coin phổ biến như VND, USD, USDT, BTC, ETH. Công cụ miễn phí của CoinHammy, nhập số tiền là có kết quả.'),
 'xep-hang.html': ('xep-hang', 'Xếp hạng sàn phái sinh crypto | CoinHammy',
   'Xếp hạng các sàn phái sinh crypto trên một thang đo chung: phí giao dịch, đòn bẩy và ưu đãi dành cho người mới. Số liệu tổng hợp từ nguồn công khai của sàn.'),
 'so-sanh.html': ('so-sanh', 'So sánh sàn phái sinh crypto: phí, đòn bẩy | CoinHammy',
   'Chọn từ 2 đến 5 sàn phái sinh để so sánh phí, đòn bẩy, ưu nhược điểm và thông tin chính cạnh nhau. Số liệu tổng hợp từ nguồn công khai của từng sàn giao dịch.'),
 'danh-gia.html': ('danh-gia', 'Đánh giá sàn phái sinh crypto | CoinHammy',
   'Đánh giá chi tiết từng sàn phái sinh crypto: phí giao dịch, đòn bẩy, mức độ an toàn và ưu nhược điểm. Số liệu tổng hợp từ nguồn công khai của mỗi sàn.'),
 'tin-tuc.html': ('tin-tuc', 'Tin tức crypto mới nhất | CoinHammy',
   'Tin crypto mới nhất do CoinHammy biên tập, cập nhật liên tục trong ngày: Bitcoin, ETF, thị trường phái sinh và các sự kiện tác động đến giá của trader Futures.'),
 'kien-thuc.html': ('kien-thuc', 'Kiến thức giao dịch Futures | CoinHammy',
   'Mỗi ngày một bài: cơ chế thị trường và kỹ năng giao dịch dành cho trader Futures, từ quản lý rủi ro, tính vị thế đến đọc funding và open interest, có ví dụ.'),
 've-chung-toi.html': ('ve-chung-toi', 'Về chúng tôi | CoinHammy',
   'CoinHammy là nơi trader Futures tìm công cụ và dữ liệu cần dùng mỗi ngày: tính vị thế, quy đổi, xếp hạng sàn, tin tức và kiến thức giao dịch, miễn phí.'),
 'mien-tru-rui-ro.html': ('mien-tru-rui-ro', 'Miễn trừ rủi ro | CoinHammy',
   'Đọc kỹ trước khi dùng công cụ hoặc làm theo nội dung trên CoinHammy: giao dịch phái sinh có rủi ro cao, nội dung chỉ để tham khảo, không phải khuyến nghị.'),
}
# trang danh sách có bản tiếng Anh riêng: địa chỉ bản Anh (xem en_lists trong tools/news/publish.py)
EN_ALT = {'tin-tuc': 'en/news', 'kien-thuc': 'en/learn'}
import en_pages   # trang chính có bản Anh sinh từ bản Việt (xếp hạng, so sánh, đánh giá...)
EN_ALT.update(en_pages.alt_map())
# trang đánh giá từng sàn: mô tả lấy từ câu giới thiệu đầu trang
INTRO = json.load(open(os.path.join(ROOT, 'tools', 'seo_intro.json'), encoding='utf-8'))

def esc(s): return html.escape(s, quote=True)

MAXDESC = 160
MINDESC = 150
PADS_VI = (' Xem thêm.', ' Dữ liệu công khai.', ' Số liệu từ nguồn công khai.', ' Số liệu tổng hợp từ nguồn công khai.')
HEADS_VI = ('Đánh giá %s: phí giao dịch, đòn bẩy, an toàn và ưu nhược điểm. ', 'Đánh giá %s: phí, đòn bẩy, an toàn. ',
            'Đánh giá %s: phí và đòn bẩy. ', 'Đánh giá %s. ')

def fit_desc(name, intro, heads=HEADS_VI, pads=PADS_VI):
    """Mô tả trang đánh giá 150-160 ký tự, luôn giữ TRỌN câu giới thiệu (không cắt giữa câu):
    thử lần lượt các đầu mô tả từ dài đến ngắn; chưa vừa thì thêm câu đệm ngắn; cuối cùng mới cắt."""
    hs = [h % name for h in heads]
    first = re.match(r'.*?[.!?](?=\s|$)', intro)
    for it in ([intro, first.group(0)] if first and first.group(0) != intro else [intro]):   # câu cuối bỏ được thì bỏ cả câu, không cắt giữa câu
        for h in hs:
            if MINDESC <= len(h + it) <= MAXDESC: return h + it
        for h in hs:
            for pad in pads:
                if MINDESC <= len(h + it + pad) <= MAXDESC: return h + it + pad
    return fit(hs[0], intro)

def fit(head, intro):
    """Dự phòng: cắt ở câu trọn vẹn, rồi dấu phẩy, rồi ranh giới từ (chỉ dùng khi fit_desc không vừa)."""
    out = head
    for sent in re.findall(r'.*?[.!?](?=\s|$)|.+$', intro):
        if len(out + sent) <= MAXDESC: out += sent
        else: break
    out = out.rstrip()
    if MINDESC <= len(out) <= MAXDESC: return out
    room = MAXDESC - len(head); seg = intro[:room - 1]; k = max(seg.rfind(','), seg.rfind(';'))
    if k >= 0 and MINDESC <= len(head + seg[:k].rstrip()) + 1 <= MAXDESC: return head + seg[:k].rstrip() + '.'
    return head + intro[:room - 1].rsplit(' ', 1)[0].rstrip(' ,;:.') + '…'

def block(path, title, desc, keep_desc):
    url = SITE + '/' + path if path else SITE + '/'
    L = ['<!--seo-->']
    if not keep_desc: L.append('<meta name="description" content="%s">' % esc(desc))
    d = desc if not keep_desc else keep_desc
    L += ['<link rel="canonical" href="%s">' % url,
          '<meta property="og:type" content="website">', '<meta property="og:site_name" content="CoinHammy">',
          '<meta property="og:locale" content="vi_VN">', '<meta property="og:title" content="%s">' % esc(title),
          '<meta property="og:description" content="%s">' % esc(d), '<meta property="og:url" content="%s">' % url,
          '<meta property="og:image" content="%s">' % IMG, '<meta property="og:image:width" content="1200">',
          '<meta property="og:image:height" content="630">', '<meta name="twitter:card" content="summary_large_image">']
    if not path:
        ld = [{"@context": "https://schema.org", "@type": "Organization", "name": "CoinHammy", "url": SITE + '/', "logo": SITE + '/favicon-192.png'},
              {"@context": "https://schema.org", "@type": "WebSite", "name": "CoinHammy", "url": SITE + '/', "inLanguage": ["vi", "en"]}]
        L.append('<script type="application/ld+json">%s</script>' % json.dumps(ld, ensure_ascii=False))
    if path in EN_ALT:
        L += [lang_boot.hreflang(url, SITE + '/' + EN_ALT[path]), lang_boot.boot('vi', '/' + path, '/' + EN_ALT[path])]
    L.append('<!--/seo-->')
    return '\n'.join(L)

def meta_for(fn):
    if fn in PAGES: return PAGES[fn]
    m = re.match(r'danh-gia-(.+)\.html$', fn)
    if m and m.group(1) in INTRO:
        name, intro = INTRO[m.group(1)]
        return ('danh-gia-' + m.group(1), 'Đánh giá %s: phí, đòn bẩy, an toàn | CoinHammy' % name,
                fit_desc(name, intro))
    return None

def apply(fn, text=None, path=None):
    m = meta_for(os.path.basename(fn))
    if not m: return None
    p, title, desc = m
    t = text if text is not None else open(fn, encoding='utf-8').read()
    t = re.sub(r'\n?<!--seo-->.*?<!--/seo-->', '', t, flags=re.S)
    ex = re.search(r'<meta name="description" content="([^"]*)">', t)
    if desc and ex:   # mô tả khai báo rõ trong PAGES thì thay mô tả cũ nằm ngoài khối seo
        t = t.replace(ex.group(0) + '\n', '', 1) if ex.group(0) + '\n' in t else t.replace(ex.group(0), '', 1)
        ex = None
    keep = html.unescape(ex.group(1)) if ex else None
    assert desc or keep, fn
    blk = block(p, title, desc, keep)
    assert len(re.findall(r'<title>.*?</title>', t, flags=re.S)) == 1, fn
    t = re.sub(r'<title>.*?</title>', lambda _: '<title>%s</title>\n%s' % (esc(title), blk), t, count=1, flags=re.S)
    rel = os.path.relpath(os.path.abspath(fn), ROOT).replace(os.sep, "/")
    return header.apply(breadcrumb.apply(faq_ld.inject(t), rel), rel, 'vi')   # header dùng chung (tools/header.py)

if __name__ == '__main__':
    files = sys.argv[1:] or sorted(f for f in os.listdir(ROOT) if f.endswith('.html'))
    for f in files:
        fp = f if os.path.isabs(f) or os.path.exists(f) else os.path.join(ROOT, f)
        r = apply(fp)
        if r is None: print('bỏ qua', f); continue
        open(fp, 'w', encoding='utf-8').write(r); print('ok', f)

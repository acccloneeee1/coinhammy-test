#!/usr/bin/env python3
"""Kiểm tra SEO toàn site — chỉ đọc, không sửa gì. Báo trang nào còn thiếu/sai:
tiêu đề, mô tả, địa chỉ chuẩn (canonical), thẻ chia sẻ (og), mã Google Analytics, noindex, có trong sitemap chưa,
cùng chiều ngược lại (sitemap có địa chỉ không còn trang).
  python3 tools/check_pages.py          # in lỗi (thoát mã 1 nếu có lỗi) và cảnh báo
  python3 tools/check_pages.py -q       # chỉ in dòng tổng kết
Cách sửa khi có lỗi:
  - trang chính mới/thiếu thẻ SEO: thêm vào PAGES trong tools/seo_head.py, rồi python3 tools/seo_head.py <file>
  - thiếu mã GA: python3 tools/ga_head.py <file>
  - trang chính chưa vào sitemap: thêm tên file vào danh sách `pages` trong hàm sitemap() của tools/news/publish.py rồi chạy lại publish
  - bài tin/kiến thức: python3 tools/news/publish.py rebuild (bài do khuôn mẫu sinh ra, đừng sửa tay)"""
import html, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import breadcrumb, header

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = json.load(open(os.path.join(ROOT, 'tools', 'news', 'config.json')))['site'].rstrip('/')
SKIP = {'node_modules', '.git', 'tools', 'functions', 'img'}


def pages():
    for d, dirs, files in os.walk(ROOT):
        dirs[:] = [x for x in dirs if x not in SKIP]
        for f in sorted(files):
            if f.endswith('.html') and not (f == '404.html' and d == ROOT):   # 404.html là trang báo lỗi (noindex, không vào sitemap)
                yield os.path.join(d, f)


def clean_url(fp):
    rel = os.path.relpath(fp, ROOT).replace(os.sep, '/')[:-5]
    if rel.endswith('/index'): rel = rel[:-5]      # en/index.html -> /en/
    return SITE + '/' + ('' if rel == 'index' else rel)


def tag(t, pat):
    m = re.search(pat, t, re.S)
    return html.unescape(m.group(1)).strip() if m else None


def check(fp, txt):
    """trả về (lỗi, cảnh báo) của một trang"""
    err, warn = [], []
    url = clean_url(fp)
    title = tag(txt, r'<title>(.*?)</title>')
    desc = tag(txt, r'<meta name="description" content="([^"]*)"')
    canon = tag(txt, r'<link rel="canonical" href="([^"]*)"')
    if not title: err.append('thiếu <title>')
    elif len(title) < 20: err.append('tiêu đề quá ngắn (%d ký tự): "%s"' % (len(title), title))
    elif len(title) > 75: warn.append('tiêu đề dài %d ký tự (Google dễ cắt, nên ≤ 65)' % len(title))
    if not desc: err.append('thiếu mô tả (meta description)')
    elif len(desc) < 70: err.append('mô tả quá ngắn (%d ký tự)' % len(desc))
    elif len(desc) > 160: warn.append('mô tả dài %d ký tự (nên ≤ 160)' % len(desc))
    if not canon: err.append('thiếu địa chỉ chuẩn (canonical)')
    elif canon != url: err.append('canonical sai: %s (đúng phải là %s)' % (canon, url))
    for p, name in (('og:title', 'og:title'), ('og:description', 'og:description'), ('og:image', 'og:image (ảnh chia sẻ)'), ('og:url', 'og:url')):
        if not re.search(r'<meta property="%s" content="[^"]+"' % re.escape(p), txt): err.append('thiếu ' + name)
    og_url = tag(txt, r'<meta property="og:url" content="([^"]*)"')
    if og_url and og_url != url: err.append('og:url sai: %s (đúng phải là %s)' % (og_url, url))
    n_ga = len(re.findall(r'<!--ga-->', txt))
    if n_ga == 0: err.append('thiếu mã Google Analytics')
    elif n_ga > 1: err.append('mã Google Analytics bị nhân đôi (%d lần)' % n_ga)
    if re.search(r'<meta[^>]+name="robots"[^>]+noindex', txt, re.I): err.append('đang noindex (Google sẽ không lập chỉ mục)')
    if len(re.findall(r'<h1[\s>]', txt)) == 0: warn.append('không có thẻ <h1>')
    if len(re.findall(r'<!--seo-->', txt)) > 1: err.append('khối SEO bị nhân đôi')
    if 'href="/favicon.ico"' not in txt or 'href="/favicon-192.png"' not in txt: err.append('thiếu thẻ favicon (/favicon.ico, /favicon-192.png)')
    if 'fonts.googleapis' in txt or 'fonts.gstatic' in txt: err.append('còn nạp Google Fonts (phải dùng font tự host: chạy tools/fonts_selfhost.py)')
    elif '<!--fonts-->' not in txt and "'Be Vietnam Pro'" in txt: err.append('thiếu khối font tự host (chạy tools/fonts_selfhost.py)')
    err += breadcrumb.verify(os.path.relpath(fp, ROOT).replace(os.sep, '/'), txt)   # đường dẫn phân cấp: có đủ và chữ hiện khớp schema
    err += header.verify(os.path.relpath(fp, ROOT).replace(os.sep, '/'), txt)       # header dùng chung (tools/header.py): đúng 1 khối, đúng ngôn ngữ, không còn header cũ
    return err, warn


def main():
    quiet = '-q' in sys.argv
    sm = open(os.path.join(ROOT, 'sitemap.xml'), encoding='utf-8').read()
    in_sitemap = set(re.findall(r'<loc>([^<]+)</loc>', sm))
    results, titles, descs, urls = [], {}, {}, set()
    for fp in pages():
        txt = open(fp, encoding='utf-8').read()
        err, warn = check(fp, txt)
        url = clean_url(fp); urls.add(url)
        if url not in in_sitemap: err.append('chưa có trong sitemap.xml')
        t = tag(txt, r'<title>(.*?)</title>'); d = tag(txt, r'<meta name="description" content="([^"]*)"')
        if t: titles.setdefault(t, []).append(os.path.relpath(fp, ROOT))
        if d: descs.setdefault(d, []).append(os.path.relpath(fp, ROOT))
        results.append((os.path.relpath(fp, ROOT), err, warn))
    for fn, e, w in results:
        for t, fs in titles.items():
            if len(fs) > 1 and fn in fs: w.append('trùng tiêu đề với: ' + ', '.join(x for x in fs if x != fn)); break
        for d, fs in descs.items():
            if len(fs) > 1 and fn in fs: w.append('trùng mô tả với: ' + ', '.join(x for x in fs if x != fn)); break
    # cặp bản Việt/Anh: hreflang phải trỏ tới trang có thật và trang đó trỏ ngược lại
    pair_err = []
    texts = {clean_url(fp): open(fp, encoding='utf-8').read() for fp in pages()}
    for u, tx in texts.items():
        alts = dict(re.findall(r'<link rel="alternate" hreflang="(vi|en)" href="([^"]*)"', tx))
        if not alts: continue
        for lg, au in alts.items():
            if au not in texts: pair_err.append('%s: hreflang %s trỏ tới trang không tồn tại: %s' % (u, lg, au))
            elif u not in re.findall(r'<link rel="alternate" hreflang="(?:vi|en)" href="([^"]*)"', texts[au]): pair_err.append('%s: trang %s không trỏ ngược lại' % (u, au))
        if re.search(r'<html lang="(vi|en)"', tx) and re.search(r'<html lang="(vi|en)"', tx).group(1) != ('en' if u == alts.get('en') else 'vi'):
            pair_err.append('%s: thuộc tính lang của trang không khớp với bản Việt/Anh' % u)
    import subprocess
    st = subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'news', 'publish.py'), 'en-check'], cwd=ROOT, capture_output=True, text=True)
    if st.returncode: pair_err.append('trang danh sách tiếng Anh lệch bản Việt — chạy: python3 tools/news/publish.py rebuild')
    # chữ/khối điền sẵn trong HTML của trang chủ, công cụ và 48 trang tiền (VI/EN) phải khớp nội dung thật; lệch chỉ là CẢNH BÁO (JS vẫn ghi đúng chữ, chỉ chớp nhẹ)
    pr = subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'prerender_i18n.py'), '--check'], cwd=ROOT, capture_output=True, text=True)
    if pr.returncode:
        print('CẢNH BÁO: nội dung điền sẵn (trang chủ, công cụ, trang tiền) đã lỗi thời -> chạy: python3 tools/prerender_i18n.py'
              if 'LỆCH' in pr.stdout else 'CẢNH BÁO: không chạy được kiểm tra chữ điền sẵn (tools/prerender_i18n.py --check): ' + (pr.stderr.strip().splitlines() or ['?'])[-1][:120])
    # khối tin điền sẵn ở 4 trang danh sách phải là bài MỚI NHẤT, và mọi ảnh bìa phải có bản thu nhỏ; lệch chỉ là CẢNH BÁO (JS vẫn dựng đúng, chỉ chậm hơn)
    for pg, ix in (('tin-tuc.html', 'tin'), ('en/news.html', 'tin'), ('kien-thuc.html', 'hoc'), ('en/learn.html', 'hoc')):
        try:
            items = json.load(open(os.path.join(ROOT, ix, 'index.json'), encoding='utf-8')).get('items', [])
            html_pg = open(os.path.join(ROOT, pg), encoding='utf-8').read()
            m = re.search(r'id="nhero"[^>]*><!--b-->.*?<article class="nh">.*?<h2><a href="([^"]+)"', html_pg, re.S)
            want = (items[0].get('ue') if pg.startswith('en/') else items[0].get('u')) or ''
            if items and (not m or m.group(1) != want):
                print('CẢNH BÁO: %s: khối tin điền sẵn không phải bài mới nhất -> chạy: python3 tools/prerender_i18n.py --lists' % pg)
        except Exception as e:
            print('CẢNH BÁO: không kiểm được khối tin điền sẵn của %s (%s)' % (pg, e))
    th = subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'news', 'thumbs.py'), '--check'], cwd=ROOT, capture_output=True, text=True)
    if th.returncode: print('CẢNH BÁO: có ảnh bìa chưa có bản thu nhỏ -> chạy: python3 tools/news/thumbs.py')
    hp = subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'header.py'), '--check'], cwd=ROOT, capture_output=True, text=True)
    if hp.returncode: print('LỖI: trang Việt / mẫu bài viết lệch header dùng chung -> chạy: python3 tools/header.py  (%s)' % ((hp.stdout.strip().splitlines() or ['?'])[0][:80]))
    orphan = sorted(u for u in in_sitemap if u not in urls)
    n_err = sum(len(e) for _, e, _ in results) + len(orphan) + len(pair_err)
    n_warn = sum(len(w) for _, _, w in results)
    if not quiet:
        for fn, e, w in results:
            for m in e: print('LỖI  %-48s %s' % (fn, m))
            for m in w: print('lưu ý %-48s %s' % (fn, m))
        for m in pair_err: print('LỖI  bản Việt/Anh                                  ' + m)
        for u in orphan: print('LỖI  sitemap.xml                                   có địa chỉ không còn trang: ' + u)
    bad = sum(1 for _, e, _ in results if e) + len(orphan) + len(pair_err)
    print('Đã kiểm %d trang: %d trang có lỗi (%d lỗi), %d lưu ý, sitemap %d địa chỉ.' % (len(results), bad, n_err, n_warn, len(in_sitemap)))
    sys.exit(1 if n_err else 0)


if __name__ == '__main__':
    main()

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

import json
import os
import sys
from datetime import datetime, timedelta

from news_core import DAILY_CAP, KINDS, KIT, ROOT, SITE, VN, die, epath, item_paths, jload, jsave, vpath
from news_images import LEDGER, item_img, ledger_check, localize_news
from news_related import related_backfill, related_cmd
from news_article import load, onpage_check, slug_en_for, taken_en, words
from news_render import redirects, render_404, write_article
from news_lists import en_lists, paginate, sitemap
import en_pages
import thumbs


def today_rows():
    log = jload(os.path.join(KIT, 'log.json'), [])
    d = datetime.now(VN).strftime('%Y-%m-%d')
    return [x for x in log if x.get('ts', '')[:10] == d]


def today():
    rows = today_rows(); now = datetime.now(VN)
    print('Hôm nay %s (%s): đã đăng %d/%d bài.' % (now.strftime('%d/%m/%Y'), ['T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'CN'][now.weekday()], len(rows), DAILY_CAP))
    if now.weekday() >= 5: print('Cuối tuần: không đăng bài.')
    for x in rows: print('- %s | %s | %s' % (x['ts'][11:16], x['cat'], x['title_vi']))


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

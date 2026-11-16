#!/usr/bin/env python3
"""Chèn mã đo lường Google Analytics 4 vào mọi trang HTML (kể cả mẫu bài viết tools/news/template.html).
Mã nằm giữa <!--ga--> ... <!--/ga--> ngay sau <meta charset>, chạy lại bao nhiêu lần cũng được (thay khối cũ, không nhân đôi).
Chỉ gửi số liệu khi trang chạy trên coinhammy.com, nên bản xem thử *.pages.dev và máy cục bộ không làm nhiễu số liệu.
  python3 tools/ga_head.py                 # tất cả trang trong repo
  python3 tools/ga_head.py file.html ...   # chỉ các file chỉ định
Đổi mã đo lường: sửa GA_ID bên dưới rồi chạy lại."""
import os, re, sys

GA_ID = 'G-SKYKGDY3FE'
HOST = 'coinhammy.com'
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANCHOR = '<meta charset="utf-8">'

BLOCK = (
    '<!--ga-->\n'
    "<script>if(location.hostname==='%(h)s'){var s=document.createElement('script');s.async=1;"
    "s.src='https://www.googletagmanager.com/gtag/js?id=%(id)s';document.head.appendChild(s);"
    "window.dataLayer=window.dataLayer||[];window.gtag=function(){dataLayer.push(arguments)};"
    "gtag('js',new Date());gtag('config','%(id)s');}</script>\n"
    '<!--/ga-->'
) % {'h': HOST, 'id': GA_ID}

OLD = re.compile(r'<!--ga-->.*?<!--/ga-->', re.S)


def patch(path):
    src = open(path, encoding='utf-8').read()
    if OLD.search(src):
        out = OLD.sub(lambda m: BLOCK, src, count=1)
    elif ANCHOR in src:
        out = src.replace(ANCHOR, ANCHOR + '\n' + BLOCK, 1)
    else:
        return None
    if out != src:
        open(path, 'w', encoding='utf-8').write(out)
        return True
    return False


def all_pages():
    for d, dirs, files in os.walk(ROOT):
        dirs[:] = [x for x in dirs if x not in ('node_modules', '.git')]
        for f in files:
            if f.endswith('.html'):
                yield os.path.join(d, f)


if __name__ == '__main__':
    targets = [os.path.abspath(a) for a in sys.argv[1:]] or sorted(all_pages())
    changed = skipped = same = 0
    for p in targets:
        r = patch(p)
        if r is None:
            skipped += 1
            print('BỎ QUA (không có <meta charset="utf-8">):', os.path.relpath(p, ROOT))
        elif r:
            changed += 1
        else:
            same += 1
    print('Đã chèn/cập nhật: %d trang, không đổi: %d, bỏ qua: %d' % (changed, same, skipped))

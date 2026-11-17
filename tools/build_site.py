#!/usr/bin/env python3
"""Dựng bản triển khai vào dist/: tách CSS và JS nhúng lặp lại giữa các trang ra file dùng chung trong /assets/.

Trang nguồn trong kho KHÔNG bị sửa (các công cụ khác vẫn đọc và vá CSS/JS ngay trong trang như cũ).
Chỉ bản trong dist/ được viết lại: khối <style>/<script> giống hệt nhau ở từ 2 trang trở lên được thay,
đúng tại vị trí cũ, bằng <link rel="stylesheet"> / <script src>, nên thứ tự áp dụng CSS và thứ tự chạy JS giữ nguyên.
dist/ cũng không chứa file nội bộ (.claude, tools, functions, README...).

  python tools/build_site.py            # dựng vào dist/ (lệnh build của Cloudflare Pages, thư mục xuất: dist)
  python tools/build_site.py --check    # chỉ kiểm và in thống kê, không ghi gì
  python tools/build_site.py --out DIR  # dựng vào thư mục khác (ví dụ ngoài kho để xem thử)

Tên file trong /assets/ chứa mã băm nội dung, nên _headers cho trình duyệt giữ 1 năm.
"""
import collections
import hashlib
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = 'dist'
ASSET_DIR = 'assets'
SKIP_DIRS = frozenset({'.git', '.claude', 'tools', 'functions', 'node_modules', '.wrangler', '__pycache__', OUT_DIR})
SKIP_ROOT_FILES = frozenset({'README.md', 'README.txt', '.gitignore'})

MIN_PAGES = 2                                   # khối phải có ở ít nhất chừng này trang mới tách
MIN_BYTES = {'style': 2048, 'script': 4096}     # khối nhỏ hơn thì để nguyên trong trang (đỡ một lượt tải)
FILE_PREFIX = {'style': 'c', 'script': 'j'}
EXTENSION = {'style': 'css', 'script': 'js'}
CLOSE_TAG = {'style': b'</style>', 'script': b'</script>'}
# Chỉ tách thẻ mở đúng các dạng này; JSON-LD và thẻ có thuộc tính khác thì để nguyên.
EXTRACTABLE_OPEN = {'style': (b'<style>', b'<style id="chh-css">'), 'script': (b'<script>',)}
# Khối font phải nằm sẵn trong trang để chữ không giật khi tải (xem README mục "Font chữ tự host").
KEEP_INLINE_REGIONS = ((b'<!--fonts-->', b'<!--/fonts-->'),)
HASH_LEN = 16

Block = collections.namedtuple('Block', 'kind start end open_tag body')

_CSS_URL = re.compile(rb'url\(\s*["\']?([^"\')\s]*)')
_ROOTED_URL = re.compile(rb'^(/|data:|https?:|#)')
_LINK_TAG = re.compile(rb'<link rel="stylesheet"( id="[\w-]+")? href="/(%s/c-[0-9a-f]{%d}\.css)">' % (ASSET_DIR.encode(), HASH_LEN))
_SCRIPT_TAG = re.compile(rb'<script src="/(%s/j-[0-9a-f]{%d}\.js)"></script>' % (ASSET_DIR.encode(), HASH_LEN))
_AFTER_TAG_NAME = (b'>', b' ', b'\n', b'\t', b'\r')


def _tag_kind(html, lt):
    """Trả 'style' / 'script' nếu tại vị trí lt là thẻ mở tương ứng, ngược lại None."""
    for kind in CLOSE_TAG:
        name_end = lt + 1 + len(kind)
        if html[lt + 1:name_end].lower() == kind.encode() and html[name_end:name_end + 1] in _AFTER_TAG_NAME:
            return kind
    return None


def iter_blocks(html):
    """Duyệt tuần tự các khối <style>/<script> của trang; bỏ qua chú thích HTML và không nhìn vào bên trong khối."""
    pos = 0
    while True:
        lt = html.find(b'<', pos)
        if lt < 0:
            return
        if html.startswith(b'<!--', lt):
            close = html.find(b'-->', lt + 4)
            if close < 0:
                return
            pos = close + 3
            continue
        kind = _tag_kind(html, lt)
        if kind is None:
            pos = lt + 1
            continue
        tag_end = html.find(b'>', lt)
        close = html.find(CLOSE_TAG[kind], tag_end + 1) if tag_end >= 0 else -1
        if close < 0:
            return
        end = close + len(CLOSE_TAG[kind])
        yield Block(kind, lt, end, html[lt:tag_end + 1], html[tag_end + 1:close])
        pos = end


def _in_keep_region(html, start):
    for opener, closer in KEEP_INLINE_REGIONS:
        region = html.rfind(opener, 0, start)
        if region >= 0 and html.find(closer, region) > start:
            return True
    return False


def _has_relative_url(css):
    """CSS tách ra file thì url() tương đối sẽ tính theo /assets/ chứ không theo trang: khối như vậy không được tách."""
    return any(not _ROOTED_URL.match(url) for url in _CSS_URL.findall(css))


def is_candidate(html, block):
    if block.open_tag not in EXTRACTABLE_OPEN[block.kind]:
        return False
    if len(block.body) < MIN_BYTES[block.kind] or _in_keep_region(html, block.start):
        return False
    return not (block.kind == 'style' and _has_relative_url(block.body))


def asset_name(kind, body):
    digest = hashlib.sha256(body).hexdigest()[:HASH_LEN]
    return '%s/%s-%s.%s' % (ASSET_DIR, FILE_PREFIX[kind], digest, EXTENSION[kind])


def plan_assets(pages):
    """pages: {đường dẫn: nội dung bytes}. Trả {tên file trong assets: nội dung} cho các khối có ở >= MIN_PAGES trang."""
    page_count = collections.Counter()
    bodies = {}
    for html in pages.values():
        names_in_page = set()
        for block in iter_blocks(html):
            if is_candidate(html, block):
                name = asset_name(block.kind, block.body)
                names_in_page.add(name)
                bodies[name] = block.body
        page_count.update(names_in_page)
    return {name: body for name, body in bodies.items() if page_count[name] >= MIN_PAGES}


def _reference_tag(block, name):
    if block.kind == 'style':
        attrs = block.open_tag[len(b'<style'):-1]
        return b'<link rel="stylesheet"' + attrs + b' href="/' + name.encode() + b'">'
    return b'<script src="/' + name.encode() + b'"></script>'


def rewrite_page(html, assets):
    """Trả trang mới: khối nào có trong assets thì thay bằng thẻ trỏ tới file, tại đúng vị trí cũ."""
    pieces = []
    pos = 0
    for block in iter_blocks(html):
        if not is_candidate(html, block):
            continue
        name = asset_name(block.kind, block.body)
        if name not in assets:
            continue
        pieces.append(html[pos:block.start])
        pieces.append(_reference_tag(block, name))
        pos = block.end
    pieces.append(html[pos:])
    return b''.join(pieces)


def restore_page(html, assets):
    """Ngược của rewrite_page: nhúng lại nội dung file vào trang. Dùng để tự kiểm rằng việc tách không làm mất gì."""
    html = _LINK_TAG.sub(lambda m: b'<style' + (m.group(1) or b'') + b'>' + assets[m.group(2).decode()] + b'</style>', html)
    return _SCRIPT_TAG.sub(lambda m: b'<script>' + assets[m.group(1).decode()] + b'</script>', html)


def collect_files(root):
    """Trả (pages, others): pages = {đường dẫn tương đối: bytes} cho .html, others = danh sách file còn lại sẽ chép nguyên."""
    pages = {}
    others = []
    for folder, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for filename in sorted(files):
            rel = os.path.relpath(os.path.join(folder, filename), root).replace(os.sep, '/')
            if rel in SKIP_ROOT_FILES:
                continue
            if filename.endswith('.html'):
                with open(os.path.join(folder, filename), 'rb') as handle:
                    pages[rel] = handle.read()
            else:
                others.append(rel)
    return pages, others


def transform(pages):
    """Trả (trang đã viết lại, assets). Dừng với lỗi nếu nhúng ngược lại không ra đúng trang gốc."""
    assets = plan_assets(pages)
    rewritten = {rel: rewrite_page(html, assets) for rel, html in pages.items()}
    broken = [rel for rel, html in rewritten.items() if restore_page(html, assets) != pages[rel]]
    if broken:
        raise SystemExit('LỖI: tách rồi nhúng lại không ra trang gốc ở %d trang, ví dụ: %s' % (len(broken), ', '.join(broken[:5])))
    return rewritten, assets


def write_output(root, out_dir, rewritten, assets, others):
    if os.path.isdir(out_dir):
        shutil.rmtree(out_dir)
    for rel in others:
        target = os.path.join(out_dir, rel)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.copyfile(os.path.join(root, rel), target)
    for rel, content in list(rewritten.items()) + list(assets.items()):
        target = os.path.join(out_dir, rel)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, 'wb') as handle:
            handle.write(content)


def summary(pages, rewritten, assets):
    before = sum(len(html) for html in pages.values())
    after = sum(len(html) for html in rewritten.values())
    shared = sum(len(body) for body in assets.values())
    css = sum(1 for name in assets if name.endswith('.css'))
    return ('%d trang: HTML %.1f MB -> %.1f MB; %d file dùng chung (%d CSS, %d JS, %.2f MB)'
            % (len(pages), before / 1e6, after / 1e6, len(assets), css, len(assets) - css, shared / 1e6))


def _output_dir(argv):
    if '--out' not in argv:
        return os.path.join(ROOT, OUT_DIR)
    position = argv.index('--out')
    if position + 1 >= len(argv):
        raise SystemExit('LỖI: --out cần kèm đường dẫn thư mục')
    return os.path.abspath(argv[position + 1])


def main(argv):
    out_dir = _output_dir(argv)
    if os.path.isdir(os.path.join(ROOT, ASSET_DIR)):
        raise SystemExit('LỖI: kho đã có thư mục %s/, trùng với nơi đặt file dùng chung của bản dựng' % ASSET_DIR)
    pages, others = collect_files(ROOT)
    rewritten, assets = transform(pages)
    print(summary(pages, rewritten, assets))
    if '--check' in argv:
        print('Chỉ kiểm, không ghi gì.')
        return 0
    write_output(ROOT, out_dir, rewritten, assets, others)
    print('Đã dựng vào %s (%d file khác chép nguyên).' % (out_dir, len(others)))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

#!/usr/bin/env python3
"""Ảnh thu nhỏ cho thẻ bài ở các trang danh sách (tin-tuc, kien-thuc, en/news, en/learn).

Mỗi ảnh bìa tin/img/x-h.jpg (1200px, ~120KB) có thêm hai bản WebP nhẹ: x-h-480.webp (~13KB) và x-h-960.webp (~40KB).
Trang danh sách chọn bản vừa màn hình qua srcset; ảnh gốc vẫn là ảnh dự phòng (thiếu bản nhỏ thì trình duyệt tự dùng ảnh gốc).
Trang bài viết vẫn dùng ảnh gốc, không đổi.

  python3 tools/news/thumbs.py            # tạo bản nhỏ còn thiếu cho mọi ảnh bìa trong tin/index.json và hoc/index.json (chạy lại vô hại)
  python3 tools/news/thumbs.py --check    # chỉ liệt kê ảnh còn thiếu bản nhỏ (thoát mã 1 nếu thiếu)
publish.py tự gọi khi đăng bài, nên bài mới luôn có đủ bản nhỏ. Cần Pillow."""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WIDTHS = (480, 960)
JPG = re.compile(r'^(/(?:tin|hoc)/img/.+)\.jpg$', re.I)   # khớp đúng quy tắc của chThumb() trong trang danh sách


def thumb_paths(url):
    m = JPG.match(url or '')
    return [os.path.join(ROOT, '%s-%d.webp' % (m.group(1).lstrip('/'), w)) for w in WIDTHS] if m else []


def cover_urls():
    """mọi ảnh bìa (bản Việt + bản Anh) đang dùng trong 2 danh sách bài"""
    out = []
    for pfx in ('tin', 'hoc'):
        p = os.path.join(ROOT, pfx, 'index.json')
        if not os.path.isfile(p):
            continue
        for it in json.load(open(p, encoding='utf-8')).get('items', []):
            for k in ('img', 'img_en'):
                if it.get(k) and it[k] not in out:
                    out.append(it[k])
    return out


def missing():
    return [u for u in cover_urls() if any(not os.path.isfile(t) for t in thumb_paths(u))]


def ensure(urls=None):
    """tạo bản nhỏ còn thiếu. Trả về số file đã tạo. Lỗi từng ảnh chỉ in cảnh báo (trang vẫn chạy bằng ảnh gốc)."""
    try:
        from PIL import Image
    except ImportError:
        print('CẢNH BÁO: chưa cài Pillow, bỏ qua ảnh thu nhỏ (trang vẫn chạy bằng ảnh gốc)')
        return 0
    n = 0
    for u in (urls if urls is not None else cover_urls()):
        src = os.path.join(ROOT, u.lstrip('/'))
        for w, t in zip(WIDTHS, thumb_paths(u)):
            if os.path.isfile(t) or not os.path.isfile(src):
                continue
            try:
                im = Image.open(src).convert('RGB')
                if im.width > w:   # ảnh gốc nhỏ hơn bản này thì giữ nguyên cỡ, không phóng to
                    im = im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)
                im.save(t, 'WEBP', quality=74, method=4)
                n += 1
            except Exception as e:
                print('CẢNH BÁO: không tạo được %s: %s' % (os.path.relpath(t, ROOT), e))
    return n


if __name__ == '__main__':
    if '--check' in sys.argv:
        m = missing()
        print('Ảnh bìa thiếu bản thu nhỏ: ' + (', '.join(m) if m else 'không'))
        sys.exit(1 if m else 0)
    print('Đã tạo %d ảnh thu nhỏ' % ensure())

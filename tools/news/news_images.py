"""Ảnh của bài viết: kiểm ảnh, cắt khung 16:9, sổ ảnh đã dùng, thẻ <figure>.
Tách từ publish.py; chạy từ thư mục gốc của kho (xem publish.py)."""

import os
import re

from news_core import IMG_MARK, KINDS, KIT, ROOT, die, esc, jload


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


def item_img(a, lg, kind='news'):
    im = a.get('image')
    return img_url(a, im, 'h', lg, kind) if im else ''


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

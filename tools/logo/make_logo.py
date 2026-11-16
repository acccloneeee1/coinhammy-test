#!/usr/bin/env python3
"""Sinh toàn bộ logo/favicon của CoinHammy từ MỘT file gốc: tools/logo/logo-coinhammy-1024.png
(hamster trắng trên nền xanh phẳng, bo góc, góc trong suốt).

  python3 tools/logo/make_logo.py            # tạo favicon.ico, favicon-192.png, apple-touch-icon.png ở thư mục gốc
                                             # + đổi logo header/footer (ảnh 96px nhúng sẵn) và thẻ favicon trong MỌI trang
  python3 tools/logo/make_logo.py --check    # chỉ kiểm tra, không ghi

Muốn đổi logo: thay file 1024 gốc (giữ nền xanh phẳng #0F80A8, hamster trắng) rồi chạy lại. Chạy nhiều lần vẫn ra cùng kết quả.
Favicon Google: nền vuông tràn viền (Google tự cắt tròn), hamster thu ~72% để râu không bị cắt; cỡ là bội của 48px."""
import base64, glob, io, os, re, sys
from PIL import Image, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, 'tools', 'logo', 'logo-coinhammy-1024.png')
CHECK = '--check' in sys.argv

im = Image.open(SRC).convert('RGBA')
assert im.size == (1024, 1024), 'file gốc phải là 1024x1024'
px = im.convert('RGB')
BG = tuple(px.getpixel((512, 120)))                     # màu nền phẳng lấy từ chính file gốc
R = im.getchannel('R').point(lambda v: v)                # nền có R thấp, hamster trắng R=255
bgr = BG[0]
alpha = R.point(lambda v: max(0, min(255, int((v - bgr) * 255 / (255 - bgr)))))
alpha = Image.composite(alpha, Image.new('L', alpha.size, 0), im.getchannel('A'))   # góc trong suốt không tính
bb = alpha.point(lambda v: 255 if v > 40 else 0).getbbox()
glyph = alpha.crop(bb); gw, gh = glyph.size

def fav(size, frac=0.72, bold=0):
    ss = 4; Z = size * ss
    g = glyph.filter(ImageFilter.MaxFilter(bold)) if bold else glyph
    tw = int(Z * frac); th = int(gh * tw / gw); gs = g.resize((tw, th), Image.LANCZOS)
    t = Image.new('RGB', (Z, Z), BG); t.paste((255, 255, 255), ((Z - tw) // 2, (Z - th) // 2), gs)
    return t.resize((size, size), Image.LANCZOS)

def png_bytes(i):
    b = io.BytesIO(); i.save(b, 'PNG', optimize=True); return b.getvalue()

out = {}
out['favicon-192.png'] = png_bytes(fav(192))
out['apple-touch-icon.png'] = png_bytes(fav(180))
ic = [fav(16, 0.80, 9), fav(32, 0.78, 9), fav(48, 0.74, 7)]
b = io.BytesIO(); ic[2].save(b, 'ICO', sizes=[(16, 16), (32, 32), (48, 48)], append_images=[ic[1], ic[0]]); out['favicon.ico'] = b.getvalue()

# logo header/footer: hamster trắng trên nền trong suốt, 96px (nền xanh + bo góc do CSS .mark lo, đổi theo giao diện sáng/tối)
hg = alpha.resize((96, 96), Image.LANCZOS)
white = Image.new('RGBA', (96, 96), (255, 255, 255, 0)); white.putalpha(hg)
MARK = 'data:image/png;base64,' + base64.b64encode(png_bytes(white)).decode()

ICONS = ('<link rel="icon" href="/favicon.ico" sizes="48x48">'
         '<link rel="icon" type="image/png" href="/favicon-192.png" sizes="192x192">'
         '<link rel="apple-touch-icon" href="/apple-touch-icon.png">')
RE_ICON = re.compile(r'<link rel="(?:icon|apple-touch-icon)"[^>]*>')
RE_MARK = re.compile(r'(<img class="mark" src=")data:image/png;base64,[A-Za-z0-9+/=]+(")')

files = [f for f in glob.glob(os.path.join(ROOT, '**', '*.html'), recursive=True) if '/node_modules/' not in f and '/.wrangler/' not in f]
files.append(os.path.join(ROOT, 'tools', 'news', 'template.html'))
changed = 0
for f in sorted(set(files)):
    s = open(f, encoding='utf-8').read(); t = s
    if 'rel="icon"' in t:
        first = RE_ICON.search(t)
        t = t[:first.start()] + ICONS + t[first.end():]
        rest = RE_ICON.sub('', t[first.start() + len(ICONS):])
        t = t[:first.start() + len(ICONS)] + rest
    t = RE_MARK.sub(lambda m: m.group(1) + MARK + m.group(2), t)
    if t != s:
        changed += 1
        if not CHECK: open(f, 'w', encoding='utf-8').write(t)
if not CHECK:
    for n, data in out.items(): open(os.path.join(ROOT, n), 'wb').write(data)
print('%s: %d trang đổi, nền %s, hamster %s, ảnh header %d byte, ico %d byte' % ('KIỂM TRA' if CHECK else 'ĐÃ GHI', changed, '#%02X%02X%02X' % BG, bb, len(MARK), len(out['favicon.ico'])))

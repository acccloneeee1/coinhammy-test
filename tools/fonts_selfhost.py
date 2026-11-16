#!/usr/bin/env python3
"""Font chữ tự host (thư mục /fonts) thay cho Google Fonts, để trang không bị giật khi font về.

Vì sao: với Google Fonts, trình duyệt phải đi 3 bước nối đuôi (HTML -> CSS của Google -> file font) và
file chữ có dấu tiếng Việt về sau file chữ Latin vài trăm ms, nên tiêu đề/menu bị xuống dòng rồi co lại
(CLS ~0.3 trên trang chủ). Ở đây: mỗi kiểu chữ là MỘT file gồm Latin + Latin-ext + Vietnamese, @font-face
nằm sẵn trong HTML, file chính được nạp trước (preload), và có font dự phòng đã chỉnh bề rộng khớp font thật
để nếu font về chậm thì chữ chỉ đổi nét chứ gần như không đổi chỗ.

Cách dùng:
  python3 tools/fonts_selfhost.py          # áp khối font vào mọi trang .html (an toàn chạy lại nhiều lần)
  python3 tools/fonts_selfhost.py --check  # chỉ kiểm: trang nào còn Google Fonts / khối font lệch

Khối font nằm giữa  <!--fonts--> ... <!--/fonts-->  trong <head>. Sửa khối ở BLOCK bên dưới rồi chạy lại.
Font gốc (OFL) lấy từ github.com/google/fonts, cắt còn Latin + Vietnamese bằng fonttools (xem README, mục Font chữ).
"""
import re, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
PRELOAD = ["BeVietnamPro-Regular", "BeVietnamPro-Medium", "BeVietnamPro-SemiBold", "BeVietnamPro-Bold", "BeVietnamPro-ExtraBold", "SpaceGrotesk", "Quicksand", "JetBrainsMono"]


# Dải ký tự có trong file font (Latin + Latin-ext + Vietnamese). Font dự phòng chỉ phủ đúng dải này, ký tự ngoài dải (mũi tên, ký hiệu...)
# vẫn rơi về font hệ thống như trước.
UR = "U+0000-00FF,U+0100-02BA,U+0102-0103,U+0110-0111,U+0128-0129,U+0131,U+0152-0153,U+0168-0169,U+01A0-01A1,U+01AF-01B0,U+02BB-02BC,U+02BD-02C5,U+02C6,U+02C7-02CC,U+02CE-02D7,U+02DA,U+02DC,U+02DD-02FF,U+0300-0301,U+0303-0304,U+0304,U+0308,U+0308-0309,U+0323,U+0329,U+1D00-1DBF,U+1E00-1E9F,U+1EA0-1EF9,U+1EF2-1EFF,U+2000-206F,U+2020,U+20A0-20AB,U+20AB,U+20AC,U+20AD-20C4,U+2113,U+2122,U+2191,U+2193,U+2212,U+2215,U+2C60-2C7F,U+A720-A7FF,U+FEFF,U+FFFD"


def _face(fam, w, f, extra=""):
    return "@font-face{font-family:'%s';font-style:normal;font-weight:%s;font-display:swap;src:url(/fonts/%s.woff2) format('woff2')%s}" % (fam, w, f, extra)


def _fb(fam, w, local, adj):
    src = ",".join("local('%s')" % x for x in local)
    return "@font-face{font-family:'%s';font-weight:%s;src:%s;size-adjust:%s%%;unicode-range:%s}" % (fam, w, src, adj, UR)


ARIAL = ["Arial", "Helvetica Neue", "Liberation Sans"]
ARIAL_B = ["Arial Bold", "Helvetica Neue Bold", "Liberation Sans Bold"]
CSS = "".join([
    _face("Be Vietnam Pro", 400, "BeVietnamPro-Regular"), _face("Be Vietnam Pro", 500, "BeVietnamPro-Medium"),
    _face("Be Vietnam Pro", 600, "BeVietnamPro-SemiBold"), _face("Be Vietnam Pro", 700, "BeVietnamPro-Bold"),
    _face("Be Vietnam Pro", 800, "BeVietnamPro-ExtraBold"),
    _face("Space Grotesk", "500 700", "SpaceGrotesk"), _face("Quicksand", 700, "Quicksand"),
    _face("JetBrains Mono", "400 600", "JetBrainsMono"), _face("Source Serif 4", "400 700", "SourceSerif4"),
    # font dự phòng: dùng Arial co giãn cho bề rộng chữ khớp font thật (đo trên chuỗi tiếng Việt và tiếng Anh)
    _fb("BVP Fallback", 400, ARIAL, 109), _fb("BVP Fallback", 500, ARIAL, 110.5), _fb("BVP Fallback", 600, ARIAL_B, 103.5),
    _fb("BVP Fallback", 700, ARIAL_B, 105), _fb("BVP Fallback", 800, ARIAL_B, 106.5),
    _fb("SG Fallback", 500, ARIAL, 109.5), _fb("SG Fallback", 700, ARIAL_B, 101.2),
    _fb("QS Fallback", 700, ARIAL_B, 100.7),
    _fb("JBM Fallback", "400 600", ["Courier New", "Liberation Mono"], 100),
])
BLOCK = "<!--fonts-->" + "".join(
    '<link rel="preload" href="/fonts/%s.woff2" as="font" type="font/woff2" crossorigin>' % f for f in PRELOAD
) + "<style>" + CSS + "</style><!--/fonts-->"

# Bốn kiểu chữ được thêm font dự phòng vào ngăn xếp font-family (mỗi cặp: cũ -> mới)
STACKS = [
    ("--sans:'Be Vietnam Pro',system-ui", "--sans:'Be Vietnam Pro','BVP Fallback',system-ui"),
    ("--mono:'JetBrains Mono',ui-monospace", "--mono:'JetBrains Mono','JBM Fallback',ui-monospace"),
    ('"Space Grotesk","Be Vietnam Pro",system-ui', '"Space Grotesk","SG Fallback","Be Vietnam Pro",system-ui'),
    ("'Quicksand',var(--sans)", "'Quicksand','QS Fallback',var(--sans)"),
]
GLINK = re.compile(r'<link rel="preconnect" href="https://fonts\.googleapis\.com">\s*<link rel="preconnect" href="https://fonts\.gstatic\.com" crossorigin>\s*<link href="https://fonts\.googleapis\.com/css2[^"]*" rel="stylesheet">')
MARK = re.compile(r"<!--fonts-->.*?<!--/fonts-->", re.S)


def pages():
    out = [p for p in ROOT.rglob("*.html") if "node_modules" not in p.parts and ".git" not in p.parts]
    return sorted(out)


def apply(src):
    n = src
    if "<!--fonts-->" in n:
        n = MARK.sub(lambda m: BLOCK, n, count=1)
    else:
        n = GLINK.sub(lambda m: BLOCK, n, count=1)
    for a, b in STACKS:
        if b not in n:
            n = n.replace(a, b)
    return n


def main():
    check = "--check" in sys.argv
    only = [a for a in sys.argv[1:] if not a.startswith("--")]
    bad, changed = [], 0
    for p in pages():
        if only and str(p.relative_to(ROOT)) not in only:
            continue
        s = p.read_text(encoding="utf-8")
        if "fonts.googleapis" not in s and "<!--fonts-->" not in s and "'Be Vietnam Pro'" not in s:
            continue  # trang không dùng font của site
        n = apply(s)
        if n != s:
            if check:
                bad.append(str(p.relative_to(ROOT)))
            else:
                p.write_text(n, encoding="utf-8"); changed += 1
        if "fonts.googleapis" in n or "fonts.gstatic" in n:
            bad.append(str(p.relative_to(ROOT)) + " (còn Google Fonts)")
    if check:
        print("OK: mọi trang dùng font tự host đúng khối" if not bad else "LỆCH:\n  " + "\n  ".join(bad))
        sys.exit(1 if bad else 0)
    print("đã cập nhật %d trang" % changed + ("; còn lệch: %s" % bad if bad else ""))


if __name__ == "__main__":
    main()

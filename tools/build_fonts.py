#!/usr/bin/env python3
"""Dựng lại thư mục /fonts (font tự host): tải font gốc OFL từ github.com/google/fonts, cắt còn Latin + Latin-ext + Vietnamese,
nén woff2. Chỉ cần chạy khi muốn đổi/cập nhật font; sau đó chạy `python3 tools/fonts_selfhost.py` để áp khối font vào trang.

  pip install fonttools brotli
  python3 tools/build_fonts.py
"""
import pathlib, subprocess, sys, tempfile, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "fonts"
BASE = "https://raw.githubusercontent.com/google/fonts/main/ofl/"
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from fonts_selfhost import UR  # cùng dải ký tự với khối @font-face

FEATURES = "kern,liga,calt,ccmp,locl,mark,mkmk,tnum,zero,case,ss01"
# tên file ra : (đường dẫn font gốc, trục wght cần giữ — None nếu font tĩnh)
JOBS = {
    **{"BeVietnamPro-%s" % n: ("bevietnampro/BeVietnamPro-%s.ttf" % n, None) for n in ("Regular", "Medium", "SemiBold", "Bold", "ExtraBold")},
    "SpaceGrotesk": ("spacegrotesk/SpaceGrotesk[wght].ttf", "wght=500:700"),
    "Quicksand": ("quicksand/Quicksand[wght].ttf", "wght=700"),
    "JetBrainsMono": ("jetbrainsmono/JetBrainsMono[wght].ttf", "wght=400:600"),
    "SourceSerif4": ("sourceserif4/SourceSerif4[opsz,wght].ttf", "wght=400:700"),
}


def run(*a):
    subprocess.run(list(a), check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main():
    OUT.mkdir(exist_ok=True)
    tmp = pathlib.Path(tempfile.mkdtemp())
    for name, (path, axis) in JOBS.items():
        src = tmp / (name + ".ttf")
        urllib.request.urlretrieve(BASE + urllib.request.quote(path, safe="/,"), src)
        if axis:
            inst = tmp / (name + "-i.ttf")
            run("fonttools", "varLib.instancer", str(src), axis, "-o", str(inst), "-q")
            src = inst
        run("pyftsubset", str(src), "--unicodes=" + UR.replace("U+", ""), "--flavor=woff2", "--layout-features=" + FEATURES,
            "--no-hinting", "--output-file=" + str(OUT / (name + ".woff2")))
        print("%-26s %6d byte" % (name, (OUT / (name + ".woff2")).stat().st_size))


if __name__ == "__main__":
    main()

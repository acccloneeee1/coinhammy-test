#!/usr/bin/env python3
"""Chấm điểm sàn theo thang 3 tier của anh Thái (chốt 06/11/2026).

Thang điểm (đã gồm đủ hai đầu, mỗi mức điểm chỉ thuộc đúng một tier):
  Tier 1: 9,8 → 8,5   (Top 1 luôn 9,8)
  Tier 2: 8,4 → 7,5
  Tier 3: 7,4 → 6,5
Số sàn mỗi tier mặc định chia đều theo thứ tự hiển thị (n // 3, n // 3, phần dư vào Tier 3;
19 sàn = 6 / 6 / 7). Trong tier, điểm trải đều từ đầu trên xuống đầu dưới, làm tròn 0,1, luôn giảm dần.

Thứ tự sàn = thứ tự hiển thị trên web: sàn ĐÃ có link giới thiệu (có trong AFFH) đứng trước, sàn chưa
có link đứng sau; trong mỗi nhóm giữ thứ tự đã lưu trong tools/diem-san.json.

Cách dùng (chạy ở thư mục gốc repo):
  python3 tools/diem_san.py                      # đồng bộ thứ tự theo AFFH rồi chấm lại, in kế hoạch (chưa ghi)
  python3 tools/diem_san.py --apply              # ghi điểm vào mọi trang + tools/news/template.html + diem-san.json
  python3 tools/diem_san.py --move kraken --to 3 --apply   # đổi vị trí rồi chấm lại
  python3 tools/diem_san.py --apply --rebuild    # ghi xong tự chạy en_pages + prerender + check_pages
  python3 tools/diem_san.py --check              # kiểm các trang đang khớp kế hoạch chưa
Sau khi --apply mà không --rebuild: chạy `python3 tools/en_pages.py`, `python3 tools/prerender_i18n.py`
(~4 phút), `python3 tools/check_pages.py`.
"""
import argparse, glob, json, os, re, subprocess, sys
from decimal import Decimal, ROUND_HALF_UP

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = os.path.join(ROOT, "tools", "diem-san.json")
TIERS = [("Tier 1", Decimal("9.8"), Decimal("8.5")),
         ("Tier 2", Decimal("8.4"), Decimal("7.5")),
         ("Tier 3", Decimal("7.4"), Decimal("6.5"))]


def read(p):
    with open(os.path.join(ROOT, p), encoding="utf-8") as f:
        return f.read()


def affh():
    m = re.search(r"AFFH=(\{.*?\})", read("xep-hang.html"))
    return json.loads(m.group(1))


def site_ids():
    return re.findall(r"\{id:'([a-z0-9]+)',score:", read("xep-hang.html"))


def load_order():
    with open(CFG, encoding="utf-8") as f:
        return json.load(f)["order"]


def sync_order(order, aff):
    ids = site_ids()
    order = [x for x in order if x in ids] + [x for x in ids if x not in order]   # sàn mới thêm vào cuối nhóm của nó
    return [x for x in order if x in aff] + [x for x in order if x not in aff]


def sizes(n):
    a = n // 3
    return [a, a, n - 2 * a]


def q(x):
    return x.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)


def score_plan(order):
    out, i = [], 0
    for (name, hi, lo), k in zip(TIERS, sizes(len(order))):
        vals = [hi] if k == 1 else [q(hi - (hi - lo) * j / (k - 1)) for j in range(k)]
        for j in range(1, len(vals)):                     # luôn giảm dần, mỗi bậc ≥ 0,1
            if vals[j] >= vals[j - 1]:
                vals[j] = vals[j - 1] - Decimal("0.1")
        for v in vals:
            out.append((order[i], name, v)); i += 1
    return out


def files():
    fs = glob.glob(os.path.join(ROOT, "**", "*.html"), recursive=True)
    fs.append(os.path.join(ROOT, "tools", "news", "template.html"))
    return sorted(set(f for f in fs if os.path.exists(f)))


def patterns(ex):
    a = re.compile(r"(id:'%s',score:)[0-9.]+" % ex)
    b = re.compile(r'("id": "%s",(?: "[a-z_]+": (?:"[^"]*"|[0-9.]+|null),)*? "score": )[0-9.]+' % ex)
    return a, b


def apply_scores(plan):
    changed = 0
    for f in files():
        s = o = open(f, encoding="utf-8").read()
        for ex, _, v in plan:
            for p in patterns(ex):
                s = p.sub(lambda m: m.group(1) + str(v), s)
        if s != o:
            open(f, "w", encoding="utf-8").write(s); changed += 1
    return changed


def check(plan):
    bad = 0
    for f in files():
        s = open(f, encoding="utf-8").read()
        for ex, _, v in plan:
            for p in patterns(ex):
                for m in p.finditer(s):
                    got = re.search(r"[0-9.]+$", m.group(0)).group(0)
                    if got != str(v):
                        bad += 1
                        if bad <= 15:
                            print("lệch:", os.path.relpath(f, ROOT), ex, got, "≠", v)
    print("Khớp hoàn toàn" if not bad else "Còn %d chỗ lệch" % bad)
    return bad == 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--move"); ap.add_argument("--to", type=int)
    ap.add_argument("--apply", action="store_true"); ap.add_argument("--rebuild", action="store_true")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()

    aff = affh()
    order = sync_order(load_order(), aff)
    if a.move:
        if a.move not in order or not a.to or not 1 <= a.to <= len(order):
            sys.exit("Cần --move <id sàn> --to <vị trí 1..%d>. Id hợp lệ: %s" % (len(order), ", ".join(order)))
        order.remove(a.move); order.insert(a.to - 1, a.move)
        if order != sync_order(order, aff):
            sys.exit("Vị trí này trái quy tắc 'sàn có link giới thiệu đứng trước': web sẽ vẫn hiển thị sàn có link "
                     "trước. Muốn đảo thật thì thêm/bỏ link trong AFFH trước.")
    plan = score_plan(order)
    for i, (ex, tier, v) in enumerate(plan, 1):
        print("%2d  %-10s %-7s %s  %s" % (i, ex, tier, v, "(có link)" if ex in aff else ""))
    if a.check:
        sys.exit(0 if check(plan) else 1)
    if not a.apply:
        print("\n(chưa ghi — thêm --apply để ghi)"); return
    with open(CFG, "w", encoding="utf-8") as f:
        json.dump({"order": order}, f, ensure_ascii=False, indent=1); f.write("\n")
    print("\nĐã ghi điểm vào %d file." % apply_scores(plan))
    if a.rebuild:
        for cmd in (["tools/en_pages.py"], ["tools/prerender_i18n.py"], ["tools/check_pages.py"]):
            print("→", " ".join(cmd)); subprocess.run([sys.executable] + cmd, cwd=ROOT)
    else:
        print("Nhớ chạy: python3 tools/en_pages.py ; python3 tools/prerender_i18n.py ; python3 tools/check_pages.py")


if __name__ == "__main__":
    main()

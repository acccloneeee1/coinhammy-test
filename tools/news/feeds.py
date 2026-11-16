#!/usr/bin/env python3
"""Quét feed tin crypto bằng curl (không qua WebFetch) và in tin mới nhất theo giờ.

  python3 tools/news/feeds.py [--hours 24] [--per 12] [--only cointelegraph,coindesk] [--desc]
  python3 tools/news/feeds.py --read <link bài>     # đọc nội dung bài gốc: curl trước, bị chặn/cần JavaScript thì tự mở bằng trình duyệt (WebFetch không mở được link lấy từ feed)

Mỗi dòng: tuổi tin | nguồn | tiêu đề | link. Giờ lấy từ pubDate (UTC) nên lọc "trong 24 giờ" chính xác.
Nguồn nào lỗi chỉ in cảnh báo ở stderr, các nguồn khác vẫn chạy.
In 2 khối: (1) báo uy tín + SEC/Fed = nguồn chính; (2) feed tin Binance = nguồn phụ, chỉ để bắt tin nóng khi báo chưa đăng
và xác nhận chéo sự việc, KHÔNG lấy dữ kiện từ đó. Bỏ khối 2 bằng --no-binance.
Đây là nguồn khám phá; bài gốc vẫn phải đọc (WebFetch link) và kiểm chéo >= 2 nguồn độc lập.
"""
import argparse, datetime as dt, email.utils, html, json, re, subprocess, sys
from concurrent.futures import ThreadPoolExecutor

FEEDS = {
    "cointelegraph": "https://cointelegraph.com/rss",
    "coindesk": "https://www.coindesk.com/arc/outboundfeeds/rss",
    "decrypt": "https://decrypt.co/feed",
    "theblock": "https://www.theblock.co/rss.xml",
    "cryptoslate": "https://cryptoslate.com/feed/",
    "blockworks": "https://blockworks.com/feed",
    "sec": "https://www.sec.gov/news/pressreleases.rss",
    "fed": "https://www.federalreserve.gov/feeds/press_all.xml",
}
BINANCE = "https://www.binance.com/bapi/composite/v4/friendly/pgc/feed/news/list?pageIndex=1&pageSize=20"
UA = "Mozilla/5.0"
CRYPTO = re.compile(r"bitcoin|btc|ether|eth\\b|crypto|xrp|solana|\\bsol\\b|token|stablecoin|coinbase|binance|\\betf|defi|blockchain|\\bsec\\b|cftc|hyperliquid|circle|ripple|tether|usdt|usdc|mining|miner|web3|nft|doge|meme|onchain|on-chain|wallet|whale|liquidat|futures|perp|airdrop|stake|staking|exchange|kraken|okx|bybit|polymarket|prediction market|\\bfed\\b|powell|tariff", re.I)


def get(url, extra=(), ua=True):
    r = subprocess.run(["curl", "-sL", "-m", "25", *(["-A", UA] if ua else []), *extra, url], capture_output=True)
    return r.stdout.decode("utf-8", "replace")


def clean(s):
    s = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", s or "", flags=re.S)
    return html.unescape(re.sub(r"\s+", " ", s)).strip()


def when(s):
    s = clean(s)
    try:
        d = email.utils.parsedate_to_datetime(s)
    except Exception:
        try:
            d = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
        except Exception:
            return None
    return d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)


def parse(name, xml):
    out = []
    for it in re.findall(r"<item[ >].*?</item>|<entry[ >].*?</entry>", xml, re.S):
        t = re.search(r"<title[^>]*>(.*?)</title>", it, re.S)
        d = re.search(r"<(?:pubDate|published|updated|dc:date)>(.*?)</", it, re.S)
        l = re.search(r"<link>(.*?)</link>", it, re.S) or re.search(r'<link[^>]*href="([^"]+)"', it)
        if t and d and (when(d.group(1))):
            ds = re.search(r"<(?:description|summary)[^>]*>(.*?)</(?:description|summary)>", it, re.S)
            ds = clean(re.sub(r"<[^>]+>", " ", clean(ds.group(1)))) if ds else ""
            out.append((when(d.group(1)), name, clean(t.group(1)), re.sub(r"[?&]utm_.*$", "", clean(l.group(1))) if l else "", ds))
    return out


def binance():
    try:
        j = json.loads(get(BINANCE, ("-H", "clienttype: web", "-H", "lang: en"), ua=False))
        out = []
        for v in j["data"]["vos"]:
            ts = int(v.get("date") or 0)
            crypto = v.get("tradingPairs") or v.get("coinPairList") or CRYPTO.search(v.get("title") or "")
            if ts and crypto:   # bỏ tin cổ phiếu/địa chính trị không liên quan crypto
                out.append((dt.datetime.fromtimestamp(ts / 1000 if ts > 1e11 else ts, dt.timezone.utc),
                            "binance-feed", clean(v.get("title")), v.get("webLink") or v.get("shareLink") or "", ""))
        return out
    except Exception as e:
        print("!! binance-feed lỗi:", e, file=sys.stderr)
        return []


def one(kv):
    name, url = kv
    items = parse(name, get(url))
    if not items:
        print(f"!! {name}: không đọc được mục nào (feed lỗi hoặc bị chặn)", file=sys.stderr)
    return items


def extract(raw):
    """HTML -> (tiêu đề, nội dung bài)"""
    body = ""
    for m in re.finditer(r'"articleBody"\s*:\s*"((?:[^"\\]|\\.)*)"', raw):
        try:
            body = json.loads('"' + m.group(1) + '"')
            break
        except Exception:
            pass
    if not body:
        raw2 = re.sub(r"<(script|style|nav|header|footer|aside|noscript)[^>]*>.*?</\1>", " ", raw, flags=re.S)
        arts = re.findall(r"<article[^>]*>(.*?)</article>", raw2, re.S)
        seg = max(arts, key=len) if arts else raw2
        ps = [clean(re.sub(r"<[^>]+>", " ", p)) for p in re.findall(r"<(?:p|li)[^>]*>(.*?)</(?:p|li)>", seg, re.S)]
        seen, keep = set(), []
        for p in ps:
            if len(p) >= 50 and p not in seen and not re.search(r"[a-z][A-Z][a-z]+[A-Z][a-z]+[A-Z]", p[:120]):
                seen.add(p); keep.append(p)
        body = "\n".join(keep)
    t = re.search(r"<title[^>]*>(.*?)</title>", raw, re.S)
    return (clean(t.group(1)) if t else "?"), body


BLOCKED = re.compile(r"security checkpoint|just a moment|attention required|access denied|verifying your browser|are you a robot", re.I)


def browser_html(url):
    """Mở bài bằng Chromium có sẵn trong phiên (không giả dạng gì): đọc được trang cần JavaScript mà curl không dựng được.
    Trang nào vẫn chặn (kiểm tra bot, CAPTCHA) thì bỏ qua nguồn đó, không tìm cách vượt."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_context(locale="en-US", viewport={"width": 1280, "height": 900}).new_page()
        try:
            pg.goto(url, wait_until="domcontentloaded", timeout=45000)
            pg.wait_for_timeout(6000)
            txt = pg.evaluate("(()=>{var c=[...document.querySelectorAll('article,main,[class*=post-content],[class*=article-body],[class*=post__content]')];"
                              "var e=c.sort((a,b)=>b.innerText.length-a.innerText.length)[0]||document.body;return e.innerText})()")
            return pg.content(), txt
        finally:
            b.close()


def read_article(url, limit=7000):
    try:
        title, body = extract(get(url))
    except Exception:
        title, body = "?", ""
    if len(body) < 600 or BLOCKED.search(title):          # curl bị chặn hoặc trang cần JavaScript -> đọc bằng trình duyệt
        try:
            html, txt = browser_html(url)
            t2, b2 = extract(html)
            if len(b2) < 600:                                  # trang không dùng thẻ <p>: lấy chữ hiển thị, giữ các dòng dài (đoạn văn)
                seen, keep = set(), []
                for ln in txt.split("\n"):
                    ln = ln.strip()
                    if len(ln) >= 80 and ln not in seen: seen.add(ln); keep.append(ln)
                if len("\n".join(keep)) > len(b2): b2 = "\n".join(keep)
            if len(b2) > len(body) and not BLOCKED.search(t2): title, body = t2, b2
        except Exception as e:
            print("!! trình duyệt không mở được: %s" % str(e)[:120], file=sys.stderr)
    print("TIÊU ĐỀ:", title)
    print(clean(body) if "\n" not in body else body[:limit])
    if len(body.strip()) < 600 or BLOCKED.search(title):
        print("!! không trích được nội dung (trang chặn truy cập tự động): bỏ nguồn này, dùng nguồn khác; hoặc WebSearch tên sự việc rồi WebFetch link do WebSearch trả về", file=sys.stderr)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=float, default=24)
    ap.add_argument("--per", type=int, default=12, help="tối đa mục mỗi nguồn")
    ap.add_argument("--only", default="")
    ap.add_argument("--no-binance", action="store_true", help="bỏ khối feed Binance")
    ap.add_argument("--desc", action="store_true", help="in thêm đoạn tóm tắt của feed dưới mỗi tin")
    ap.add_argument("--read", default="", help="đọc nội dung một bài theo link")
    a = ap.parse_args()
    if a.read:
        read_article(a.read); sys.exit(0)
    feeds = {k: v for k, v in FEEDS.items() if not a.only or k in a.only.split(",")}
    now = dt.datetime.now(dt.timezone.utc)
    with ThreadPoolExecutor(8) as ex:
        res = list(ex.map(one, feeds.items())) if not a.only or [k for k in a.only.split(",") if k in FEEDS] else []
    bn = [] if a.no_binance and "binance-feed" not in a.only else (binance() if (not a.only or "binance-feed" in a.only) else [])

    def pick(groups, per):
        rows = []
        for items in groups:
            items = sorted(items, key=lambda x: x[0], reverse=True)[:per]
            rows += [r for r in items if 0 <= (now - r[0]).total_seconds() / 3600 <= a.hours]
        return sorted(rows, key=lambda x: x[0], reverse=True)

    def show(rows):
        for d, n, t, l, ds in rows:
            h = (now - d).total_seconds() / 3600
            print(f"{h:5.1f}h | {n} | {t[:110]} | {l}")
            if a.desc and ds:
                print("      ↳", ds[:320])

    rows = pick(res, a.per)
    if rows or not bn:
        print(f"# KHỐI 1 — BÁO/CƠ QUAN (nguồn chính): {len(rows)} mục trong {a.hours:g} giờ qua (bây giờ {now:%d/%m %H:%M} UTC)")
        show(rows)
    if bn:
        brow = pick([bn], 40)[:15]
        print(f"\n# KHỐI 2 — BINANCE (nguồn phụ: bắt tin nóng khi báo chưa đăng + xác nhận chéo; không lấy dữ kiện từ đây): {len(brow)} mục")
        show(brow)

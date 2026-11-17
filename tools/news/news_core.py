"""Phần lõi dùng chung của bộ đăng bài: đường dẫn, cấu hình, chuyên mục, hàm tiện ích nhỏ.
Tách từ publish.py; chạy từ thư mục gốc của kho (xem publish.py)."""

import html
import json
import os
import re
import sys
import unicodedata
from datetime import datetime, timedelta, timezone


ROOT = os.getcwd()
KIT = os.path.join(ROOT, 'tools', 'news')
CFG = json.load(open(os.path.join(KIT, 'config.json'), encoding='utf-8'))
SITE = CFG['site'].rstrip('/')
VN = timezone(timedelta(hours=7))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
CATS = {'btc': ('Bitcoin', 'Bitcoin'), 'alt': ('Altcoin', 'Altcoins'), 'fut': ('Futures', 'Futures'),
        'ex': ('Sàn giao dịch', 'Exchanges'), 'reg': ('Quy định', 'Regulation'), 'pol': ('Chính trị', 'Politics')}
# names of outside outlets / attribution phrases that must never appear in a published article
NO_SOURCE = re.compile(r"(cointelegraph|coindesk|the\s*block\b|decrypt\b|reuters|bloomberg|cnbc|coingape|u\.today|cryptoslate|"
                       r"bitcoin\s*magazine|cryptopotato|beincrypto|newsbtc|the\s*defiant|blockworks|watcher\.?guru|coin68|"
                       r"tạp chí bitcoin|blogtienao|vnexpress|theo (báo|trang|tờ|hãng tin|nguồn)|nguồn\s*:|source\s*:|according to (a |the )?(report|outlet)|"
                       r"reported by|as reported|first reported)", re.I)
CATS_L = {'mk': ('Thị trường', 'Market'), 'tr': ('Giao dịch', 'Trading')}
# pfx = thư mục chứa index.json + ảnh (giữ nguyên); vdir = thư mục trang Việt của bài MỚI (bài cũ ở tin/, hoc/ đã chuyển sang đây, địa chỉ cũ 301); edir = thư mục trang Anh
KINDS = {'news': {'pfx': 'tin', 'vdir': 'tin-tuc', 'edir': 'en/news', 'cats': CATS, 'ld': 'NewsArticle', 'rel': ('Tin khác', 'More news'), 'idx': ('tin', 'index.json')},
         'learn': {'pfx': 'hoc', 'vdir': 'kien-thuc', 'edir': 'en/learn', 'cats': CATS_L, 'ld': 'Article', 'rel': ('Bài kiến thức khác', 'More guides'), 'idx': ('hoc', 'index.json')}}
DAILY_CAP = 5            # articles per day, Monday-Friday only
AUTHOR = ('Ban biên tập CoinHammy', 'CoinHammy Editorial Team')
REQ = ('slug', 'cat', 'ts', 'event', 'vi', 'en')
REQ_L = ('title', 'seo_title', 'desc', 'lead', 'body_html')


def die(msg):
    print('LỖI:', msg); sys.exit(1)


def esc(s):
    return html.escape(str(s or ''), quote=True)


def slugify(s):
    s = unicodedata.normalize('NFD', s.replace('đ', 'd').replace('Đ', 'D'))
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn').lower()
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-')[:80].strip('-')

IMG_MARK = re.compile(r'<p>\s*\[\[img:(\d+)\]\]\s*</p>', re.I)
REL_MARK = re.compile(r'<p>\s*\[\[rel:(\d+)\]\]\s*</p>', re.I)   # đặt dòng "Liên quan" của related[N] ngay dưới đoạn văn đứng trước nó
CAT_COL = {'btc': '#F7931A', 'alt': '#8B5CF6', 'fut': '#06B6D4', 'ex': '#22C55E', 'reg': '#F59E0B', 'pol': '#EF4444', 'mk': '#0EA5E9', 'tr': '#14B8A6'}
FONT = "Inter,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"


def fmt_time(ts, lg):
    d = datetime.fromisoformat(ts).astimezone(VN)
    return d.strftime('%d/%m/%Y · %H:%M') if lg == 'vi' else d.strftime('%b %d, %Y · %H:%M') + ' (GMT+7)'


def vpath(a, kind):
    """đường dẫn trang Việt: bài cũ giữ tin/ hoc/, bài mới nằm trong tin-tuc/ kien-thuc/"""
    return '/%s/%s' % (a.get('dir') or KINDS[kind]['pfx'], a['slug'])


def epath(a, kind):
    return '/%s/%s' % (KINDS[kind]['edir'], a['slug_en'])


def item_paths(a, kind):
    return {'u': vpath(a, kind), 'ue': epath(a, kind)}


def jload(p, default):
    try:
        return json.load(open(p, encoding='utf-8'))
    except Exception:
        return default


def jsave(p, obj):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + '.tmp'
    json.dump(obj, open(tmp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    os.replace(tmp, p)

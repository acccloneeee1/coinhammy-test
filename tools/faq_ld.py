#!/usr/bin/env python3
"""Sinh khối JSON-LD FAQPage từ chính khối hỏi đáp đang hiện trên trang (trang chủ và 19 trang đánh giá sàn, cả bản Việt lẫn Anh).
Đọc chữ đã điền sẵn trong HTML nên schema luôn khớp đúng chữ khách thấy (Google yêu cầu hai thứ phải giống nhau).
Được gọi từ tools/seo_head.py (bản Việt) và tools/en_pages.py (bản Anh); không cần chạy tay."""
import html, json, re

MARK = 'id="faq-ld"'
OLD = re.compile(r'\n?<script type="application/ld\+json" id="faq-ld">.*?</script>', re.S)


def _txt(s):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', '', s))).strip()


def extract(t):
    """[(câu hỏi, trả lời)] của khối hỏi đáp trong trang, rỗng nếu trang không có"""
    m = re.search(r'id="rvFaqB"[^>]*><!--b-->(.*?)<!--/b-->', t, re.S)          # trang đánh giá một sàn
    if m: return [(_txt(q), _txt(a)) for q, a in re.findall(r'<h3[^>]*>(.*?)</h3>\s*<p[^>]*>(.*?)</p>', m.group(1), re.S)]
    m = re.search(r'<section class="blk" id="faq">(.*?)</section>', t, re.S)    # trang chủ
    if m: return [(_txt(q), _txt(a)) for q, a in re.findall(r'<details[^>]*>\s*<summary[^>]*>(.*?)</summary>\s*<p[^>]*>(.*?)</p>\s*(?:<div class=\"more\">.*?</div>\s*)?</details>', m.group(1), re.S)]
    return []


def inject(t):
    """đặt (hoặc bỏ) khối FAQPage ngay trước <!--/seo-->; chạy lại bao nhiêu lần cũng được"""
    t = OLD.sub('', t)
    qa = [(q, a) for q, a in extract(t) if q and a]
    if not qa or '<!--/seo-->' not in t: return t
    ld = {"@context": "https://schema.org", "@type": "FAQPage",
          "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in qa]}
    blk = '<script type="application/ld+json" %s>%s</script>\n' % (MARK, json.dumps(ld, ensure_ascii=False))
    return t.replace('<!--/seo-->', blk + '<!--/seo-->', 1)

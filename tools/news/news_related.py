"""Dòng "Liên quan": xếp hạng bài cũ theo độ khớp, đặt link vào thân bài, điền bù cho bài cũ.
Tách từ publish.py; chạy từ thư mục gốc của kho (xem publish.py)."""

import json
import math
import os
import re
import sys
import unicodedata

from news_core import KINDS, KIT, REL_MARK, ROOT, die, esc, jload, jsave, slugify


# ---- Liên quan: dòng "Liên quan: <tiêu đề bài khác>" cuối mỗi bài (BẮT BUỘC, 1–3 mục; 1 mục → cuối bài; 2+ mục → <p>[[rel:N]]</p> dưới đoạn khớp, còn lại rải giữa bài rồi cuối bài) + link trong câu văn (tuỳ chọn, chỉ khi thật sự khớp) ----
# Dòng cuối bài ghi thẳng vào HTML tĩnh nên bot đọc được ngay (khác khối "Tin khác" bên dưới là do JS dựng).
RSTOP = set('cua cac nhung mot nhieu trong tren duoc khong cung voi tuy theo khi sau truoc nay nao van con lai thi la va the and for with from that this has have are was were will its into after over amid about than'.split())


def _tok(s):
    s = unicodedata.normalize('NFD', str(s or '').lower().replace('đ', 'd'))
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return {t for t in re.findall(r'[a-z0-9]+', s) if len(t) >= 3 and t not in RSTOP}


def related_corpus():
    """mọi bài đã đăng (tin + kiến thức) từ hai file index.json"""
    out = []
    for kind in ('news', 'learn'):
        K = KINDS[kind]
        for x in jload(os.path.join(ROOT, *K['idx']), {'items': []}).get('items', []):
            out.append({**x, 'kind': kind})
    return out


def _doc(x):
    return _tok(' '.join(str(x.get(lg, {}).get(k, '')) for lg in ('vi', 'en') for k in ('title', 'desc', 'lead')) + ' ' + ' '.join(str(k) for lg in ('vi', 'en') for k in (x.get(lg, {}).get('keywords') or [])))


def related_rank(a, kind, corpus=None):
    """xếp các bài cũ theo độ liên quan với bài a (điểm = tổng độ hiếm của từ chung + thưởng cùng đồng coin / cùng mục / cùng loại). Trả về [(điểm, bài)]"""
    corpus = [c for c in (corpus if corpus is not None else related_corpus()) if not (c['kind'] == kind and c['slug'] == a.get('slug'))]
    docs = [_doc(c) for c in corpus]
    df = {}
    for d in docs:
        for t in d: df[t] = df.get(t, 0) + 1
    me = _doc(a) | _tok(a.get('event'))
    rows = []
    for c, d in zip(corpus, docs):
        sc = sum(math.log(1 + len(docs) / df[t]) for t in me & d)
        if c.get('coin') and c.get('coin') == a.get('coin') and c['coin'] != 'BTC': sc += 1.5
        if c.get('cat') == a.get('cat'): sc += 0.5
        if c['kind'] == kind: sc += 1.0   # cùng loại (tin với tin, kiến thức với kiến thức) khớp độc giả hơn
        rows.append((round(sc, 2), c))
    rows.sort(key=lambda r: (r[0], r[1].get('ts', '')), reverse=True)
    return rows


def resolve_related(a, kind):
    rel = a.get('related')
    if not isinstance(rel, list) or not 1 <= len(rel) <= 3:
        die('thiếu "related": danh sách 1–3 bài liên quan dạng [{"kind":"news|learn","slug":"..."}] (bắt buộc). Gợi ý: python3 tools/news/publish.py related ART.json')
    have = {(c['kind'], c['slug']) for c in related_corpus()}
    out = []
    for r in rel:
        if not isinstance(r, dict) or r.get('kind') not in KINDS or not r.get('slug'): die('related: mỗi mục phải là {"kind":"news|learn","slug":"..."}')
        if (r['kind'], r['slug']) not in have: die('related: không có bài đã đăng "%s/%s" (xem danh sách bằng lệnh related)' % (r['kind'], r['slug']))
        if r['kind'] == kind and r['slug'] == slugify(a.get('slug', '')): die('related: không được trỏ về chính bài này')
        if (r['kind'], r['slug']) in [(o['kind'], o['slug']) for o in out]: die('related: trùng bài %s' % r['slug'])
        out.append({'kind': r['kind'], 'slug': r['slug']})
    return out


def related_lines(a, lg):
    """danh sách (chỉ số trong related, HTML dòng "Liên quan: <tiêu đề>" in nghiêng đậm); tiêu đề + địa chỉ lấy từ index nên luôn đúng ngôn ngữ"""
    by = {(c['kind'], c['slug']): c for c in related_corpus()}
    rows = []
    for i, r in enumerate(a.get('related') or [], 1):
        c = by.get((r['kind'], r['slug']))
        url = c and (c.get('ue') if lg == 'en' else c.get('u'))
        if not (c and url and (c.get(lg) or {}).get('title')): continue
        rows.append((i, '<strong><em>%s <a href="%s">%s</a></em></strong>' % ('Liên quan:' if lg == 'vi' else 'Related:', esc(url), esc(c[lg]['title']))))
    return rows


def _rel_points(body):
    """các điểm có thể chèn dòng Liên quan: ngay sau đoạn văn thường ở cấp ngoài cùng (không trong bảng/danh sách), không dính sát ảnh/dòng khác"""
    pts = []
    for m in re.finditer(r'<p(?:\s(?![^>]*\barl\b)[^>]*)?>(?!\s*\[\[(?:img|rel):)(.*?)</p>', body, re.S | re.I):
        head = body[:m.start()]
        depth = sum(len(re.findall('<%s[ >]' % t, head, re.I)) - len(re.findall('</%s>' % t, head, re.I)) for t in ('ul', 'ol', 'table', 'blockquote'))
        if depth > 0: continue
        if re.match(r'\s*<p(?:\s+class="arl ain")?>\s*(?:\[\[(?:img|rel):|<strong><em>)', body[m.end():], re.I): continue   # sát ảnh / dòng Liên quan khác
        if re.search(r'<p class="arl ain">(?:(?!</p>).)*</p>\s*$', head, re.S): continue   # ngay sau một dòng Liên quan
        pts.append(m.end())
    return pts


def place_related(a, lg, body):
    """Luật vị trí (anh Thái, 03/11/2026): 1 bài liên quan -> cuối bài. Từ 2 bài: bài có <p>[[rel:N]]</p> nằm ngay dưới đoạn văn liên quan;
    bài không có đoạn văn khớp thì rải đều giữa thân bài, riêng bài cuối cùng nằm cuối bài (không dồn hết xuống cuối).
    Trả về (body đã chèn dòng giữa bài, HTML các dòng cuối bài)."""
    lines = related_lines(a, lg); n = len(a.get('related') or [])
    ln = lambda h, ain: '<p class="arl%s">%s</p>' % (' ain' if ain else '', h)
    marked = {int(x) for x in REL_MARK.findall(body)}
    by = dict(lines)
    body = REL_MARK.sub(lambda m: ln(by[int(m.group(1))], True) if int(m.group(1)) in by else '', body)
    rest = [(i, h) for i, h in lines if i not in marked]
    tail = []
    if n < 2 or not rest:
        tail = rest
    else:
        tail = [rest[-1]]; mid = rest[:-1]
        pts = _rel_points(body)
        if mid and pts:
            ins = {}
            for j, (i, h) in enumerate(mid, 1):
                k = min(max(round(j * len(pts) / (len(mid) + 1)) - 1, 0), len(pts) - 1)
                while k in ins and k + 1 < len(pts): k += 1
                ins[k] = h
            for k in sorted(ins, reverse=True):
                body = body[:pts[k]] + '\n' + ln(ins[k], True) + body[pts[k]:]
        else:
            tail = mid + tail
    return body, '\n'.join(ln(h, False) for i, h in tail)


def related_cmd(path):
    kind = 'learn' if '--kind' in sys.argv and sys.argv[sys.argv.index('--kind') + 1] == 'learn' else 'news'
    try:
        a = json.load(open(path, encoding='utf-8'))
    except Exception as e:
        die('không đọc được %s: %s' % (path, e))
    a['slug'] = slugify(a.get('slug', ''))
    print('Bài liên quan gợi ý (điểm cao = khớp hơn). Link trong câu văn chỉ dùng khi điểm cao VÀ ý thật sự khớp câu đó; dòng cuối bài thì chọn 1–3 bài khớp nhất, nới lỏng được.')
    for sc, c in related_rank(a, kind)[:8]:
        print('%5.1f  %-5s %s  %s\n         vi: %s  %s\n         en: %s  %s' % (sc, c['kind'], c['ts'][:10], c['slug'], c['u'], c['vi']['title'], c.get('ue', ''), c['en']['title']))


def related_backfill():
    n = 0
    for kind, sub in (('news', 'articles'), ('learn', 'learn_articles')):
        d = os.path.join(KIT, sub)
        for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
            ap = os.path.join(d, f); aa = json.load(open(ap, encoding='utf-8'))
            if aa.get('related'): continue
            pick = [c for sc, c in related_rank(aa, kind)[:2]]
            aa['related'] = [{'kind': c['kind'], 'slug': c['slug']} for c in pick]
            jsave(ap, aa); n += 1
            print('%-5s %-60s -> %s' % (kind, aa['slug'][:60], ', '.join(c['slug'][:40] for c in pick)))
    print('Đã điền "related" cho %d bài. Chạy tiếp: python3 tools/news/publish.py rebuild' % n)

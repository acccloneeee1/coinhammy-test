#!/usr/bin/env python3
"""Khai báo ngôn ngữ cho các trang có HAI địa chỉ (bản Việt + bản Anh): thẻ hreflang và đoạn script chọn ngôn ngữ.
Dùng chung cho bài viết (tools/news/publish.py) và trang danh sách (tools/seo_head.py).

Luật chọn ngôn ngữ (chạy ngay đầu trang, trước khi vẽ):
  1. khách đã chọn VI/EN (lưu trong trình duyệt)  -> theo lựa chọn đó
  2. chưa chọn: trình duyệt đặt tiếng Việt hoặc múi giờ Việt Nam -> Việt, còn lại -> Anh (và lưu lại)
  3. trang đang mở khác ngôn ngữ đó -> chuyển sang địa chỉ của bản kia
  Máy tìm kiếm / bot xem trước link KHÔNG bị chuyển hướng (Google đọc được cả hai bản). Gồm mọi công cụ của Google (Googlebot, Google-InspectionTool = nút "Kiểm tra URL trực tiếp" của Search Console, GoogleOther, AdsBot...): chữ "google" trong BOT."""
import json

BOT = r'bot|crawl|spider|slurp|bing|preview|facebookexternalhit|whatsapp|zalo|telegram|linkedin|lighthouse|pagespeed|headless|google'


def hreflang(vi_url, en_url):
    """3 thẻ alternate: vi, en và x-default (bản Việt)"""
    return ('<link rel="alternate" hreflang="vi" href="%s">\n<link rel="alternate" hreflang="en" href="%s">\n'
            '<link rel="alternate" hreflang="x-default" href="%s">') % (vi_url, en_url, vi_url)


def boot(page_lang, vi_path, en_path):
    """vi_path / en_path: đường dẫn bắt đầu bằng '/' của hai bản"""
    alt = json.dumps({'vi': vi_path, 'en': en_path})
    return ('<script>(function(){var P=window.CH_PAGE={l:"%s",alt:%s};try{var bot=/%s/i.test(navigator.userAgent),s=localStorage.getItem("chm_lang");'
            'if(s!=="vi"&&s!=="en"){var tz=Intl.DateTimeFormat().resolvedOptions().timeZone||"",ls=navigator.languages||[navigator.language||""];'
            's=(/^Asia\\/(Ho_Chi_Minh|Saigon)$/.test(tz)||ls.some(function(x){return /^vi/i.test(x);}))?"vi":"en";if(!bot)localStorage.setItem("chm_lang",s);}'
            'if(!bot&&s!==P.l&&P.alt[s])location.replace(P.alt[s]+location.hash);}catch(e){}})();</script>') % (page_lang, alt, BOT) + PREFETCH


# tải sẵn bản ngôn ngữ kia CHỈ khi khách rê chuột/chạm vào nút VI/EN (không tải khi trang rảnh: đã đo thấy làm trang chủ chậm thêm ~1,7s trên mạng chậm)
PREFETCH = ('<script>(function(){var P=window.CH_PAGE;if(!P||!P.alt)return;var done={};'
            'function pf(l){var u=P.alt[l];if(!u||l===P.l||done[u])return;done[u]=1;try{var k=document.createElement("link");'
            'if(k.relList&&k.relList.supports&&k.relList.supports("prefetch")){k.rel="prefetch";k.href=u;k.as="document";document.head.appendChild(k);}'
            'else if(window.fetch){fetch(u,{credentials:"same-origin"}).catch(function(){});}}catch(e){}}'
            'function hot(e){var b=e.target.closest?e.target.closest("[data-lang]"):null;if(b)pf(b.getAttribute("data-lang"));}'
            '["pointerover","touchstart","focusin"].forEach(function(n){document.addEventListener(n,hot,{passive:true});});'
            '})();</script>')

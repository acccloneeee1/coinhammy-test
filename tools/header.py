#!/usr/bin/env python3
"""Header dùng chung cho mọi trang (một nguồn duy nhất).

Gồm 3 phần trong một khối <!--chh-->…<!--/chh--> chèn ngay trước <div class="wrap">:
  - CSS (tiền tố chh-, không đụng class của trang),
  - HTML: dải giá chạy + thanh menu (logo, Công cụ, Sàn giao dịch, Tin tức, Kiến thức, nút ngôn ngữ, nút sáng/tối, nút ☰ trên điện thoại),
  - JS: menu thả xuống, menu ngôn ngữ, ngăn kéo điện thoại, dải giá (dữ liệu thật: Binance, CoinGecko, alternative.me; có lưu đệm).
Dải giá và thanh menu ghim chung khi cuộn (máy tính và điện thoại). Khung tối đa 1440px (nội dung 1360px), lề 40px (điện thoại 16px).

Dùng lại của header cũ: font và biến màu của trang, logo (<img class="mark">, make_logo.py vẫn thay được), nút sáng/tối giữ
id="themeBtn" nên mã sáng/tối sẵn có của từng trang (lưu chm_theme, hiệu ứng mặt trời/mặt trăng) chạy y như cũ, đổi ngôn ngữ
vẫn lưu chm_lang rồi sang địa chỉ bản kia (lấy từ window.CH_PAGE.alt của trang), nhãn và cách định dạng số của dải giá cũ.

Ngoài chèn khối mới, apply() còn gỡ header cũ: thẻ <header class="top">, các luật CSS chỉ dành cho nó (.top, .pl, .pr, .seg,
.icon-btn, #mpanel, #menuBtn, dải .mq…), phần JS thu gọn header khi cuộn + menu điện thoại cũ (giữ bộ liquid glass mà các
thẻ khác của trang dùng), quy tắc /*hdr-pre*/. Chạy lại bao nhiêu lần cũng ra cùng kết quả.

  python3 tools/header.py            # áp cho mọi trang Việt ở thư mục gốc + gỡ header cũ khỏi mẫu bài viết
  python3 tools/header.py --check    # chỉ kiểm, thoát mã 1 nếu có trang lệch
Trang Anh (en/…), bài viết, danh sách phân trang, 404: tự có khi chạy en_pages.py / publish.py (đã gọi apply())."""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TPL = os.path.join(ROOT, 'tools', 'news', 'template.html')
INTRO = json.load(open(os.path.join(ROOT, 'tools', 'seo_intro.json'), encoding='utf-8'))

# sàn: (mã, màu ô chữ, màu chữ) theo A–Z; tên lấy từ seo_intro.json
EX = [('binance', '#F3BA2F', '#241A00'), ('bingx', '#2A6BFF', '#FFFFFF'), ('bitget', '#00C2D1', '#00262B'), ('bitunix', '#9AE62B', '#132300'),
      ('blofin', '#F28C1F', '#2A1500'), ('bybit', '#F7A600', '#241A00'), ('coinbase', '#0052FF', '#FFFFFF'), ('cryptocom', '#0B2D4A', '#FFFFFF'),
      ('deribit', '#05B08A', '#00261D'), ('gate', '#2354E6', '#FFFFFF'), ('htx', '#1B6EF3', '#FFFFFF'), ('kraken', '#7132F5', '#FFFFFF'),
      ('kucoin', '#23AF91', '#04201A'), ('lbank', '#F5B70A', '#241A00'), ('mexc', '#1D6FEA', '#FFFFFF'), ('okx', '#4B5563', '#FFFFFF'),
      ('phemex', '#3C6CF6', '#FFFFFF'), ('primexbt', '#1E5BFF', '#FFFFFF'), ('weex', '#E6B800', '#241A00')]
REC = ['deribit', 'binance', 'okx', 'bybit', 'bitget']          # "Đề xuất của CoinHammy" (theo thứ tự anh Thái chọn)
COINS = [('BTC', 'Bitcoin'), ('ETH', 'Ethereum'), ('SOL', 'Solana'), ('BNB', 'BNB'), ('XRP', 'XRP'), ('DOGE', 'Dogecoin'), ('HYPE', 'Hyperliquid')]

T = {
 'vi': dict(home='/', pos='/cong-cu', chart='/bieu-do', conv='/quy-doi', reviews='/danh-gia', ex='/danh-gia-%s', rank='/xep-hang', cmp='/so-sanh',
            news='/tin-tuc', learn='/kien-thuc', nTools='Công cụ', nEx='Sàn giao dịch', nNews='Tin tức', nLearn='Kiến thức',
            capTools='Công cụ miễn phí cho trader Futures', tPos='Tính vị thế', tPosD='Ký quỹ, giá thanh lý, lãi lỗ tại TP/SL',
            tChart='Biểu đồ nâng cao', tChartD='Tính vị thế trên biểu đồ nến trực tiếp', tConv='Quy đổi', tConvD='VND, USD, USDT, BTC, ETH',
            capCex='Sàn giao dịch tập trung', capRec='Đề xuất của CoinHammy', allRv='Tất cả đánh giá', rankL='Bảng xếp hạng', cmpL='So sánh sàn',
            rec='Đề xuất', main='Menu chính', lang='Ngôn ngữ / Language', theme='Đổi sáng/tối', menu='Menu', tk='Giá thị trường'),
 'en': dict(home='/en/', pos='/en/tools', chart='/en/chart-calculator', conv='/en/converter', reviews='/en/reviews', ex='/en/reviews/%s',
            rank='/en/rankings', cmp='/en/compare', news='/en/news', learn='/en/learn', nTools='Tools', nEx='Exchanges', nNews='News', nLearn='Learn',
            capTools='Free tools for futures traders', tPos='Position calculator', tPosD='Margin, liquidation price, PnL at TP/SL',
            tChart='Advanced chart', tChartD='Size positions on a live candlestick chart', tConv='Converter', tConvD='VND, USD, USDT, BTC, ETH',
            capCex='Centralized exchanges', capRec='CoinHammy picks', allRv='All reviews', rankL='Rankings', cmpL='Compare exchanges',
            rec='Recommended', main='Main', lang='Ngôn ngữ / Language', theme='Toggle light/dark', menu='Menu', tk='Market prices'),
}
# chữ cho dải giá (giống nhãn của dải thống kê cũ ở trang chủ)
TKL = {
 'vi': dict(cap='Vốn hóa thị trường', vol='Khối lượng 24 giờ', oi='OI BTC', fund='Funding BTC', ls='Long/Short', fg='Sợ hãi & Tham lam',
            unitB=' tỷ', unitT=' nghìn tỷ', fgl=['Sợ hãi cực độ', 'Sợ hãi', 'Trung lập', 'Tham lam', 'Tham lam cực độ']),
 'en': dict(cap='Market cap', vol='24h volume', oi='BTC OI', fund='BTC funding', ls='Long/short', fg='Fear & Greed',
            unitB='B', unitT='T', fgl=['Extreme fear', 'Fear', 'Neutral', 'Greed', 'Extreme greed']),
}

SVG_DOWN = '<svg viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M2.5 4.5 6 8l3.5-3.5"/></svg>'
SVG_LANG = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
            '<path d="M3 6h8M7 3.5V6"/><path d="M4.8 6c.9 3.3 2.9 5.6 5.7 6.9"/><path d="M9.2 6c-.8 3.6-2.6 6-5.7 7.4"/><path d="M12.5 20.5 16.5 11l4 9.5M13.9 17.4h5.2"/></svg>')
SVG_CHECK = '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m3.5 8.5 3 3 6-6.5"/></svg>'
SVG_THEME = ('<svg class="tg" width="18" height="18" viewBox="0 0 24 24" aria-hidden="true"><circle class="tg-core" cx="12" cy="12" r="5" fill="currentColor"/>'
             '<g class="tg-rays" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></g>'
             '<g class="tg-moon"><g transform="translate(24 0) scale(-1 1)"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" fill="currentColor" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/></g></g></svg>')
SVG_MENU = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true">'
            '<path class="chh-l1" d="M4 7h16"/><path class="chh-l2" d="M4 12h16"/><path class="chh-l3" d="M4 17h16"/></svg>')
ICON = {
 'pos': '<rect x="4" y="3" width="16" height="18" rx="3"/><path d="M8 7h8M8 12h2M14 12h2M8 16h2M14 16h2"/>',
 'chart': '<path d="M4 20V4M4 20h16"/><path d="M8 15v-4M12 15V8M16 15v-6M20 15v-2"/>',
 'conv': '<path d="M4 8h13l-3-3M20 16H7l3 3"/>',
}

CSS = r"""
:root{--chh-h:83px;--chh-shadow:0 16px 40px -16px rgba(20,24,29,.28)}
html{scroll-padding-top:calc(var(--chh-h) + 16px)}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--chh-shadow:0 16px 40px -16px rgba(0,0,0,.7)}}
:root[data-theme="dark"]{--chh-shadow:0 16px 40px -16px rgba(0,0,0,.7)}
@media (max-width:900px){:root{--chh-h:77px}}
.chh-stk,.chh-drw{font-family:var(--sans);-webkit-font-smoothing:antialiased}
.chh-stk *,.chh-drw *{box-sizing:border-box}
.chh-stk{position:sticky;top:env(safe-area-inset-top,0px);z-index:60;font-size:15px;line-height:1.5;text-align:left}
.chh-stk::before{content:"";position:absolute;left:0;right:0;bottom:100%;height:env(safe-area-inset-top,0px);background:var(--surface)}
.chh-in{max-width:1440px;margin:0 auto;padding-left:max(40px,env(safe-area-inset-left,0px));padding-right:max(40px,env(safe-area-inset-right,0px))}
@media (max-width:767px){.chh-in{padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px))}}
:where(.chh-stk,.chh-drw) a{text-decoration:none;color:inherit}
:where(.chh-stk,.chh-drw) nav a{padding:0;font-size:inherit;font-weight:inherit;color:inherit}
.chh-stk :focus-visible,.chh-drw :focus-visible{outline:2px solid var(--focus);outline-offset:2px;border-radius:6px}
/* dải giá chạy */
.chh-tk{background:var(--surface);border-bottom:1px solid var(--hair);height:30px;overflow:hidden;position:relative;font-size:12px;line-height:1;
  -webkit-mask:linear-gradient(90deg,transparent,#000 40px,#000 calc(100% - 40px),transparent);mask:linear-gradient(90deg,transparent,#000 40px,#000 calc(100% - 40px),transparent)}
.chh-trk{display:flex;width:max-content;height:100%;animation:chh-tk 60s linear infinite}
.chh-tk:hover .chh-trk,.chh-tk:focus-within .chh-trk{animation-play-state:paused}
@keyframes chh-tk{to{transform:translateX(-50%)}}
.chh-set{display:flex;align-items:center;height:100%}
.chh-ti{display:flex;align-items:center;gap:6px;height:100%;padding:0 16px;white-space:nowrap;color:var(--muted);border-right:1px solid var(--hair)}
.chh-ti b{color:var(--text);font-weight:700;letter-spacing:.01em}
.chh-px,.chh-v{font-family:var(--mono);font-weight:600;color:var(--text);font-variant-numeric:tabular-nums;transition:color .25s}
.chh-ch{font-family:var(--mono);font-weight:600;font-variant-numeric:tabular-nums}
.chh-up{color:var(--up)}.chh-dn{color:var(--down)}
.chh-px.chh-fu{color:var(--up)}.chh-px.chh-fd{color:var(--down)}
.chh-fg{display:inline-flex;align-items:center;gap:6px}
.chh-fg i{width:7px;height:7px;border-radius:50%;background:var(--muted);display:inline-block}
.chh-ti.chh-na{display:none}
@media (prefers-reduced-motion:reduce){.chh-trk{animation:none}.chh-tk{overflow-x:auto;-webkit-mask:none;mask:none;scrollbar-width:none}.chh-set+.chh-set{display:none}}
/* thanh menu */
.chh-hd{position:relative;background:var(--surface);border-bottom:1px solid var(--border)}
.chh-bar{display:flex;align-items:center;gap:24px;height:52px}
.chh-brand{display:flex;align-items:center;gap:10px;flex:none;color:var(--text)}
.chh-brand .mark{display:block;flex:none;width:30px;height:30px;border-radius:19%;background:var(--accent)}   /* nền logo cùng màu chữ Hammy */
.chh-brand span{font-family:'Quicksand','QS Fallback',var(--sans);font-weight:700;font-size:21.2px;letter-spacing:0;line-height:1.5}
.chh-brand b{color:var(--accent);font-weight:inherit}
.chh-nav{display:flex;align-items:center;gap:2px;height:100%;flex:1;min-width:0}
.chh-ni{height:100%;display:flex;align-items:center}
.chh-ni[data-m]{position:relative}
.chh-nl{position:relative;top:1px;display:inline-flex;align-items:center;gap:5px;height:34px;padding:0 11px 1px;border:0;background:none;font:inherit;font-size:14px;font-weight:500;color:var(--muted);border-radius:8px;cursor:pointer;white-space:nowrap}
.chh-nav .chh-nl{padding:0 11px 1px;font-size:14px;font-weight:500;color:var(--muted)}
.chh-nav .chh-nl:hover,.chh-ni.open>.chh-nl{color:var(--text);background:var(--surface2)}
.chh-nav .chh-nl.chh-cur{color:var(--text)}
.chh-nl.chh-cur::after{content:"";position:absolute;bottom:-9px;left:11px;right:11px;height:2px;background:var(--accent);border-radius:2px}
.chh-nl svg{width:11px;height:11px;transition:transform .2s;opacity:.7;position:relative;top:1px}
.chh-ni.open>.chh-nl svg{transform:rotate(180deg)}
.chh-right{display:flex;align-items:center;gap:6px;flex:none;margin-left:auto}
.chh-ib,.chh-lgb{position:relative;width:32px;height:32px;padding:0;display:inline-flex;align-items:center;justify-content:center;border:0;border-radius:9px;background:transparent;color:var(--muted);cursor:pointer;-webkit-tap-highlight-color:transparent;
  transition:background .25s var(--ease),color .25s var(--ease),transform .3s cubic-bezier(.34,1.5,.5,1)}
.chh-ib:hover,.chh-lgb:hover,.chh-lg.open .chh-lgb{background:color-mix(in srgb,var(--text) 7%,transparent);color:var(--text)}
.chh-ib:active,.chh-lgb:active{transform:scale(.96)}
.chh-ib svg{width:17px;height:17px}
.chh-lgb svg{width:18px;height:18px}
@media (max-width:900px){.chh-ib::before,.chh-lgb::before{content:"";position:absolute;inset:-6px}}
/* nút sáng/tối: hiệu ứng mặt trời <-> mặt trăng của header cũ */
#themeBtn .tg{overflow:visible}
#themeBtn .tg-core{transform-box:fill-box;transform-origin:center}
#themeBtn .tg-rays,#themeBtn .tg-moon{transform-box:view-box;transform-origin:12px 12px}
#themeBtn .tg-moon{transform:rotate(70deg) scale(.3);opacity:0}
#themeBtn[data-dark="1"] .tg-core{transform:scale(.2);opacity:0}
#themeBtn[data-dark="1"] .tg-rays{transform:rotate(-90deg) scale(.3);opacity:0}
#themeBtn[data-dark="1"] .tg-moon{transform:none;opacity:1}
#themeBtn.tgr .tg-core,#themeBtn.tgr .tg-rays,#themeBtn.tgr .tg-moon{transition:transform .6s cubic-bezier(.34,1.5,.5,1),opacity .35s var(--ease)}
@media (prefers-reduced-motion:reduce){#themeBtn .tg-core,#themeBtn .tg-rays,#themeBtn .tg-moon{transition:none!important}}
/* menu ngôn ngữ */
.chh-lg{position:relative}
.chh-lgm{position:absolute;right:0;top:calc(100% + 10px);min-width:160px;padding:6px;background:var(--surface);border:1px solid var(--border);border-radius:10px;box-shadow:var(--chh-shadow);
  opacity:0;visibility:hidden;transform:translateY(-4px);transition:opacity .14s,transform .14s,visibility 0s .14s;z-index:5}
.chh-lg.open .chh-lgm{opacity:1;visibility:visible;transform:none;transition:opacity .14s,transform .14s}
.chh-lgm a{display:flex;align-items:center;justify-content:space-between;gap:10px;height:34px;padding:0 10px;border-radius:7px;font-size:13px;color:var(--text)}
.chh-lgm a:hover{background:var(--surface2)}
.chh-lgm a svg{width:14px;height:14px;color:var(--accent);visibility:hidden}
.chh-lgm a[aria-current]{font-weight:600}
.chh-lgm a[aria-current] svg{visibility:visible}
/* menu thả xuống (rộng vừa nội dung, neo dưới mục menu) */
.chh-mega{position:absolute;left:-8px;top:100%;width:max-content;max-width:calc(100vw - 32px);padding-top:4px;opacity:0;visibility:hidden;transform:translateY(-4px);
  transition:opacity .15s,transform .15s,visibility 0s .15s;pointer-events:none;z-index:2}
.chh-ni.open .chh-mega{opacity:1;visibility:visible;transform:none;transition:opacity .15s,transform .15s;pointer-events:auto}
.chh-mp{background:var(--surface);border:1px solid var(--border);border-radius:12px;box-shadow:var(--chh-shadow);overflow:hidden}
.chh-mg{display:flex}
.chh-col{padding:14px 18px 10px;min-width:0}
.chh-col+.chh-col{border-left:1px solid var(--hair)}
.chh-cap{font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin:0 0 6px;line-height:1.5}
.chh-tl{display:flex;flex-direction:column}
.chh-nav .chh-tool{display:flex;gap:12px;align-items:center;padding:7px 10px;margin:0 -10px;border-radius:8px;min-width:0}
.chh-tool:hover,.chh-tool[aria-current]{background:var(--surface2)}
.chh-tool .chh-ic{flex:none;width:30px;height:30px;border-radius:8px;display:grid;place-items:center;background:color-mix(in srgb,var(--accent) 14%,transparent);color:var(--accent)}
.chh-tool .chh-ic svg{width:16px;height:16px}
.chh-tool>span:last-child{min-width:0}
.chh-tool b{display:block;font-size:13px;font-weight:600;color:var(--text);line-height:1.35}
.chh-tool small{display:block;font-size:11.5px;color:var(--muted);line-height:1.35;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.chh-exg{display:grid;grid-template-columns:repeat(2,minmax(176px,auto));grid-template-rows:repeat(10,auto);grid-auto-flow:column;column-gap:28px}
.chh-exr{display:grid;grid-template-columns:minmax(150px,auto)}
.chh-nav .chh-ex{display:flex;align-items:center;gap:10px;height:34px;padding:0 10px;margin:0 -10px;border-radius:8px;color:var(--text);font-size:13.5px;font-weight:500;min-width:0;white-space:nowrap;line-height:1.5}
.chh-ex:hover,.chh-ex[aria-current]{background:var(--surface2)}
.chh-ex>span{min-width:0;overflow:hidden;text-overflow:ellipsis}
.chh-mono{flex:none;display:block;width:20px;height:20px;border-radius:5px;background:url(/img/ex-logos-1.webp) 0 0/380px 20px no-repeat;font-style:normal}
/* nhãn "Đề xuất": chữ xanh, không khung, chân chữ ngang chân tên sàn */
.chh-stk .chh-rec,.chh-drw .chh-rec{flex:none;display:inline-block;position:relative;top:1px;color:var(--accent);font-size:9px;font-weight:600;line-height:1;letter-spacing:.01em;overflow:visible}
.chh-ex .chh-rec,.chh-dx .chh-rec{margin-left:-4px}
.chh-mft{display:flex;flex-wrap:wrap;gap:4px 26px;padding:10px 18px;border-top:1px solid var(--hair);background:var(--surface2);font-size:13px;line-height:1.5}
.chh-nav .chh-mft a{color:var(--accent);font-weight:600;font-size:13px}
.chh-nav .chh-mft a:hover{color:var(--accent);text-decoration:underline;text-underline-offset:3px}
/* nút ☰ (điện thoại): có khung; dấu X căn giữa khi mở */
.chh-menu{display:none;border:1px solid var(--border)!important;background:var(--surface)!important;color:var(--text)!important}
.chh-menu svg{overflow:visible}
.chh-menu path{transform-box:view-box;transform-origin:12px 12px;transition:transform .35s var(--ease),opacity .2s}
html.chh-open .chh-menu .chh-l1{transform:rotate(45deg) translateY(5px)}
html.chh-open .chh-menu .chh-l2{opacity:0;transform:scaleX(.2)}
html.chh-open .chh-menu .chh-l3{transform:rotate(-45deg) translateY(-5px)}
/* ngăn kéo điện thoại */
.chh-drw{display:none}
@media (max-width:900px){
  .chh-nav{display:none}
  .chh-menu{display:inline-flex}
  .chh-bar{height:48px;gap:12px;justify-content:space-between}
  .chh-right{gap:3px}.chh-menu{margin-left:10px}
  .chh-tk{height:28px;font-size:11.5px;-webkit-mask:none;mask:none}.chh-ti{padding:0 12px}.chh-ti .chh-nm{display:none}
  .chh-drw{display:block;position:fixed;left:0;right:0;top:calc(var(--chh-h) + env(safe-area-inset-top,0px));max-height:calc(100dvh - var(--chh-h) - env(safe-area-inset-top,0px));z-index:59;background:var(--surface);border-bottom:1px solid var(--border);box-shadow:var(--chh-shadow);overflow-y:auto;overscroll-behavior:contain;
    padding:8px max(16px,env(safe-area-inset-right,0px)) 8px max(16px,env(safe-area-inset-left,0px));
    opacity:0;visibility:hidden;transform:translateY(-6px);transition:opacity .18s,transform .18s,visibility 0s .18s;font-size:15px;line-height:1.5;text-align:left;color:var(--text)}
  html.chh-open .chh-drw{opacity:1;visibility:visible;transform:none;transition:opacity .18s,transform .18s}
}
.chh-acc{border:0}
.chh-acc>button,.chh-dl{display:flex;align-items:center;justify-content:space-between;width:100%;height:48px;border:0;background:none;font:inherit;font-size:15.5px;font-weight:600;color:var(--text);cursor:pointer;padding:0}
.chh-acc>button svg{width:13px;height:13px;color:var(--muted);transition:transform .2s}
.chh-acc.open>button svg{transform:rotate(180deg)}
.chh-ab{display:none;padding:0 0 10px}
.chh-acc.open .chh-ab{display:block}
.chh-ab .chh-tool{display:flex;gap:12px;align-items:center;margin:0;padding:9px 2px;border-radius:8px}
.chh-ab .chh-cap{margin:6px 0 4px}
.chh-dg{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));grid-auto-flow:column;column-gap:12px;margin-bottom:6px}
.chh-dg.n19{grid-template-rows:repeat(10,auto)}.chh-dg.n5{grid-template-rows:repeat(3,auto)}
.chh-dx{display:flex;align-items:center;gap:10px;min-width:0;height:44px;font-size:15px;font-weight:500;color:var(--text);white-space:nowrap}
.chh-dx>span:not(.chh-rec){min-width:0;overflow:hidden;text-overflow:ellipsis}
.chh-dx[aria-current]{color:var(--accent)}
.chh-lk{display:flex;flex-wrap:wrap;justify-content:space-between;gap:0 4px;margin-top:6px;padding:4px 0}
.chh-lk a{display:inline-flex;align-items:center;height:36px;color:var(--accent);font-size:13px;font-weight:600;white-space:nowrap}
.chh-lk a::after{content:" \2192";white-space:pre}
"""

JS = r"""
(function(){
var dc=document,R=dc.documentElement,C=__CFG__;
function q(s,e){return (e||dc).querySelector(s);}function qa(s,e){return [].slice.call((e||dc).querySelectorAll(s));}
/* menu thả xuống: rê chuột (máy tính) + bấm + Esc */
var items=qa('.chh-ni[data-m]'),tm,fine=matchMedia('(hover:hover) and (pointer:fine)');
function close(ex){items.forEach(function(n){if(n!==ex){n.classList.remove('open');q('.chh-nl',n).setAttribute('aria-expanded','false');}});}
function open(n){close(n);lgClose();var m=q('.chh-mega',n);m.style.left='';n.classList.add('open');q('.chh-nl',n).setAttribute('aria-expanded','true');
  var over=m.getBoundingClientRect().right-(R.clientWidth-16);if(over>0)m.style.left=(-8-over)+'px';}
items.forEach(function(n){var b=q('.chh-nl',n);
  b.addEventListener('click',function(){n.classList.contains('open')?close():open(n);});
  n.addEventListener('mouseenter',function(){if(!fine.matches)return;clearTimeout(tm);tm=setTimeout(function(){open(n);},90);});
  n.addEventListener('mouseleave',function(){if(!fine.matches)return;clearTimeout(tm);tm=setTimeout(close,160);});});
/* menu ngôn ngữ: link thật sang bản kia; lưu chm_lang như nút VI/EN cũ */
var lg=q('.chh-lg'),lb=lg&&q('.chh-lgb',lg);
function lgClose(){if(lg){lg.classList.remove('open');lb.setAttribute('aria-expanded','false');}}
if(lg){lb.addEventListener('click',function(e){e.stopPropagation();var on=!lg.classList.contains('open');close();lg.classList.toggle('open',on);lb.setAttribute('aria-expanded',on?'true':'false');});
  qa('.chh-lgm a',lg).forEach(function(a){var l=a.getAttribute('hreflang');
    a.addEventListener('click',function(e){try{localStorage.setItem('chm_lang',l);}catch(x){}if(a.hasAttribute('aria-current')){e.preventDefault();lgClose();}});
    var pf=function(){if(a.hasAttribute('aria-current')||a._pf)return;a._pf=1;try{var k=dc.createElement('link');k.rel='prefetch';k.href=a.getAttribute('href');dc.head.appendChild(k);}catch(x){}};
    ['pointerenter','touchstart','focus'].forEach(function(ev){a.addEventListener(ev,pf,{passive:true});});});}
dc.addEventListener('click',function(e){if(!e.target.closest('.chh-ni[data-m]'))close();if(!e.target.closest('.chh-lg'))lgClose();});
dc.addEventListener('keydown',function(e){if(e.key!=='Escape')return;var o=q('.chh-ni.open');close();if(o)q('.chh-nl',o).focus();if(lg&&lg.classList.contains('open')){lgClose();lb.focus();}setMenu(false);});
/* ngăn kéo điện thoại */
var mb=dc.getElementById('chh-menu');
function setMenu(on){if(R.classList.contains('chh-open')===on)return;R.classList.toggle('chh-open',on);if(mb)mb.setAttribute('aria-expanded',on?'true':'false');dispatchEvent(new Event('scroll'));}
if(mb)mb.addEventListener('click',function(){setMenu(!R.classList.contains('chh-open'));});
qa('.chh-acc>button').forEach(function(b){b.addEventListener('click',function(){var a=b.parentNode,on=!a.classList.contains('open');a.classList.toggle('open',on);b.setAttribute('aria-expanded',on?'true':'false');});});
qa('.chh-drw a').forEach(function(a){a.addEventListener('click',function(){setMenu(false);});});
dc.addEventListener('pointerdown',function(e){if(R.classList.contains('chh-open')&&!e.target.closest('.chh-drw')&&!e.target.closest('#chh-menu'))setMenu(false);},true);
addEventListener('resize',function(){if(innerWidth>900)setMenu(false);});
/* dải giá: dữ liệu thật, lưu đệm trong trình duyệt để mỗi trang không gọi lại từ đầu */
var trk=dc.getElementById('chh-trk');if(!trk)return;
var L=C.tk,SY=C.coins;
function rd(k,ttl){try{var o=JSON.parse(localStorage.getItem('chh_'+k)||'null');if(o&&(!ttl||Date.now()-o.t<ttl))return o.v;}catch(x){}return null;}
function wr(k,v){try{localStorage.setItem('chh_'+k,JSON.stringify({t:Date.now(),v:v}));}catch(x){}}
function js(u,ms){var ac=window.AbortController?new AbortController():null,t=setTimeout(function(){if(ac)ac.abort();},ms||7000);
  return fetch(u,ac?{signal:ac.signal}:{}).then(function(r){clearTimeout(t);if(!r.ok)throw 0;return r.json();});}
function spot(p){return js('https://data-api.binance.vision'+p).catch(function(){return js('https://api.binance.com'+p);});}
function nf(v,d){return new Intl.NumberFormat('en-US',{minimumFractionDigits:d,maximumFractionDigits:d}).format(v);}
function usd(v){return '$'+nf(v,v>=1?2:(v>=0.01?4:8));}
function pc(v){return (v>0?'+':'')+nf(v,2)+'%';}
function money(b){var t=b>=1000,n=t?b/1000:b;return '$'+nf(n,n>=100?0:(n>=10?1:2))+(t?L.unitT:L.unitB);}
function fgIdx(v){return v<25?0:v<45?1:v<55?2:v<75?3:4;}
var FGC=['var(--down)','#E58C3A','var(--muted)','#8FBF3F','var(--up)'];
var PX=rd('px')||{},ST=rd('st')||{};
function shw(k){qa('[data-k="'+k+'"]',trk).forEach(function(e){e.classList.remove('chh-na');});}
function set(sel,txt,cls){qa(sel,trk).forEach(function(e){if(e.textContent!==txt)e.textContent=txt;if(cls!==undefined)e.className=cls;});}
function paint(prev){
  SY.forEach(function(s){var p=PX[s];if(!p)return;
    qa('[data-k="'+s+'"] .chh-px',trk).forEach(function(e){var t=usd(p[0]);if(e.textContent!==t){e.textContent=t;
      if(prev&&prev[s]&&prev[s][0]!==p[0]){e.classList.remove('chh-fu','chh-fd');void e.offsetWidth;e.classList.add(p[0]>prev[s][0]?'chh-fu':'chh-fd');setTimeout(function(){e.classList.remove('chh-fu','chh-fd');},700);}}});
    set('[data-k="'+s+'"] .chh-ch',pc(p[1]),'chh-ch '+(p[1]>=0?'chh-up':'chh-dn'));});
  if(ST.cap>0){shw('cap');set('[data-k="cap"] .chh-v',money(ST.cap));if(isFinite(ST.capCh))set('[data-k="cap"] .chh-ch',pc(ST.capCh),'chh-ch '+(ST.capCh>=0?'chh-up':'chh-dn'));}
  if(ST.vol>0){shw('vol');set('[data-k="vol"] .chh-v',money(ST.vol));}
  if(ST.oi>0){shw('oi');set('[data-k="oi"] .chh-v',money(ST.oi));}
  if(isFinite(ST.fund)){shw('fund');set('[data-k="fund"] .chh-v',(ST.fund>=0?'+':'')+nf(ST.fund,3)+'%','chh-v '+(ST.fund>=0?'chh-up':'chh-dn'));}
  if(ST.lsl>0){shw('ls');set('[data-k="ls"] .chh-l',nf(ST.lsl*100,1)+'%');set('[data-k="ls"] .chh-s',nf((1-ST.lsl)*100,1)+'%');}
  if(ST.fg>=0){shw('fg');var i=fgIdx(ST.fg);set('[data-k="fg"] .chh-fv',ST.fg+' · '+L.fgl[i]);qa('[data-k="fg"] i',trk).forEach(function(e){e.style.background=FGC[i];});}
}
function loadPx(){
  spot('/api/v3/ticker/24hr?type=MINI&symbols='+encodeURIComponent(JSON.stringify(SY.map(function(s){return s+'USDT';})))).then(function(a){
    var prev=JSON.parse(JSON.stringify(PX));(a||[]).forEach(function(x){var s=x.symbol.replace(/USDT$/,''),l=parseFloat(x.lastPrice),o=parseFloat(x.openPrice);if(l>0&&o>0)PX[s]=[l,(l-o)/o*100];});
    wr('px',PX);paint(prev);}).catch(function(){});
}
function loadSt(){
  var done=function(){wr('st',ST);paint();};
  if(rd('cg',600000)===null)js('https://api.coingecko.com/api/v3/global',8000).then(function(j){var d=j&&j.data;if(!d)return;
    ST.cap=d.total_market_cap.usd/1e9;ST.capCh=d.market_cap_change_percentage_24h_usd;ST.vol=d.total_volume.usd/1e9;wr('cg',1);done();}).catch(function(){wr('cg',0);});
  if(rd('fg',1800000)===null)js('https://api.alternative.me/fng/?limit=1',8000).then(function(j){var v=parseInt(j&&j.data&&j.data[0]&&j.data[0].value,10);if(v>=0){ST.fg=v;wr('fg',1);done();}}).catch(function(){wr('fg',0);});
  if(rd('fd',120000)===null)js('https://fapi.binance.com/fapi/v1/premiumIndex?symbol=BTCUSDT',6000).then(function(j){
    var f=parseFloat(j.lastFundingRate)*100,mk=parseFloat(j.markPrice);if(isFinite(f))ST.fund=f;
    return js('https://fapi.binance.com/fapi/v1/openInterest?symbol=BTCUSDT',6000).then(function(o){var oi=parseFloat(o.openInterest)*mk/1e9;if(oi>0)ST.oi=oi;wr('fd',1);done();});
  }).catch(function(){wr('fd',0);});
  if(rd('ls',300000)===null)js('https://fapi.binance.com/futures/data/globalLongShortAccountRatio?symbol=BTCUSDT&period=5m&limit=1',6000).then(function(a){
    var r=parseFloat(a&&a[0]&&a[0].longAccount);if(r>0){ST.lsl=r;wr('ls',1);done();}}).catch(function(){wr('ls',0);});
}
paint();
function tick(f){if(f||!dc.hidden)loadPx();setTimeout(tick,15000);}
setTimeout(function(){tick(1);},rd('px',10000)?10000:0);   /* lần đầu luôn lấy (kể cả tab mở nền); sau đó chỉ khi tab đang xem */   /* giá vừa lấy ở trang trước (<10 giây) thì dùng luôn, lấy mới sau 10 giây */
loadSt();setInterval(function(){if(!dc.hidden)loadSt();},60000);
dc.addEventListener('visibilitychange',function(){if(!dc.hidden){if(!rd('px',15000))loadPx();loadSt();}});
})();
"""


def esc(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')


def section(rel):
    """trang thuộc mục nào của menu + mã trang để tô đúng mục con"""
    p = rel.lstrip('/')
    p = p[:-5] if p.endswith('.html') else p
    p = p[:-6] if p.endswith('/index') else p
    if p.startswith('en/'): p = p[3:]
    elif p == 'en': p = ''
    TOOLS = {'cong-cu': 'pos', 'tools': 'pos', 'bieu-do': 'chart', 'chart-calculator': 'chart', 'quy-doi': 'conv', 'converter': 'conv'}
    if p in TOOLS: return 'tools', TOOLS[p]
    m = re.match(r'(?:danh-gia-|reviews/)([a-z0-9]+)$', p)
    if m and m.group(1) in INTRO: return 'ex', 'ex:' + m.group(1)
    if p in ('danh-gia', 'reviews'): return 'ex', 'reviews'
    if p in ('xep-hang', 'rankings'): return 'ex', 'rank'
    if p in ('so-sanh', 'compare'): return 'ex', 'cmp'
    if p in ('tin-tuc', 'news'): return 'news', 'news'
    if p.startswith(('tin-tuc/', 'news/')): return 'news', None
    if p in ('kien-thuc', 'learn'): return 'learn', 'learn'
    if p.startswith(('kien-thuc/', 'learn/')): return 'learn', None
    return None, None


def alt_links(t, lang):
    m = re.search(r'window\.CH_PAGE=\{l:"(vi|en)",alt:(\{[^{}]*\})', t)
    if m:
        try:
            a = json.loads(m.group(2))
            if a.get('vi') and a.get('en'): return a
        except ValueError:
            pass
    return {'vi': '/', 'en': '/en/'}


def logo(t):
    m = re.search(r'<img class="mark" src="(data:image/png;base64,[A-Za-z0-9+/=]+)"', t)
    if m: return m.group(1)
    m = re.search(r'<img class="mark" src="(data:image/png;base64,[A-Za-z0-9+/=]+)"', open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read())
    return m.group(1)


def render(lang, rel, alt, mark):
    S = T[lang]; K = TKL[lang]
    sec, cur = section(rel)
    ac = lambda k: ' aria-current="page"' if cur == k else ''
    name = lambda s: INTRO[s][0]
    pos = {e[0]: i for i, e in enumerate(EX)}      # vị trí logo trong ảnh ghép img/ex-logos-1.webp (thứ tự EX)
    tile = lambda s, c=None, f=None: '<i class="chh-mono" style="background-position:-%dpx 0" aria-hidden="true"></i>' % (pos[s] * 20)
    col = {s: (c, f) for s, c, f in EX}
    tools = [('pos', 'pos', 'tPos', 'tPosD'), ('chart', 'chart', 'tChart', 'tChartD'), ('conv', 'conv', 'tConv', 'tConvD')]
    tool_a = ''.join('<a class="chh-tool" href="%s"%s><span class="chh-ic"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
                     'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">%s</svg></span><span><b>%s</b><small>%s</small></span></a>'
                     % (S[u], ac(k), ICON[k], esc(S[b]), esc(S[d])) for k, u, b, d in tools)
    rec = '<span class="chh-rec">%s</span>' % esc(S['rec'])
    ex_a = ''.join('<a class="chh-ex" href="%s"%s>%s<span>%s</span>%s</a>' % (S['ex'] % s, ac('ex:' + s), tile(s, c, f), esc(name(s)), rec if s in REC else '')
                   for s, c, f in EX)
    rec_a = ''.join('<a class="chh-ex" href="%s"%s>%s<span>%s</span></a>' % (S['ex'] % s, ac('ex:' + s), tile(s, *col[s]), esc(name(s))) for s in REC)
    foot = ('<div class="chh-mft"><a href="%s"%s>%s →</a><a href="%s"%s>%s →</a><a href="%s"%s>%s →</a></div>'
            % (S['reviews'], ac('reviews'), esc(S['allRv']), S['rank'], ac('rank'), esc(S['rankL']), S['cmp'], ac('cmp'), esc(S['cmpL'])))
    nl_cur = lambda k: ' chh-cur' if sec == k else ''
    nav = (
        '<nav class="chh-nav" aria-label="%s">' % esc(S['main']) +
        '<div class="chh-ni" data-m="tools"><button type="button" class="chh-nl%s" aria-expanded="false" aria-controls="chh-m-tools">%s%s</button>'
        % (nl_cur('tools'), esc(S['nTools']), SVG_DOWN) +
        '<div class="chh-mega" id="chh-m-tools"><div class="chh-mp"><div class="chh-col"><div class="chh-cap">%s</div><div class="chh-tl">%s</div></div></div></div></div>'
        % (esc(S['capTools']), tool_a) +
        '<div class="chh-ni" data-m="ex"><button type="button" class="chh-nl%s" aria-expanded="false" aria-controls="chh-m-ex">%s%s</button>'
        % (nl_cur('ex'), esc(S['nEx']), SVG_DOWN) +
        '<div class="chh-mega" id="chh-m-ex"><div class="chh-mp"><div class="chh-mg"><div class="chh-col"><div class="chh-cap">%s</div><div class="chh-exg">%s</div></div>'
        '<div class="chh-col"><div class="chh-cap">%s</div><div class="chh-exr">%s</div></div></div>%s</div></div></div>'
        % (esc(S['capCex']), ex_a, esc(S['capRec']), rec_a, foot) +
        '<div class="chh-ni"><a class="chh-nl%s" href="%s"%s>%s</a></div>' % (nl_cur('news'), S['news'], ac('news'), esc(S['nNews'])) +
        '<div class="chh-ni"><a class="chh-nl%s" href="%s"%s>%s</a></div>' % (nl_cur('learn'), S['learn'], ac('learn'), esc(S['nLearn'])) +
        '</nav>')
    lg_a = ''.join('<a href="%s" hreflang="%s" lang="%s"%s>%s%s</a>' % (esc(alt[l]), l, l, ' aria-current="true"' if l == lang else '', n, SVG_CHECK)
                   for l, n in (('vi', 'Tiếng Việt'), ('en', 'English')))
    right = ('<div class="chh-right"><div class="chh-lg"><button type="button" class="chh-lgb" aria-haspopup="true" aria-expanded="false" aria-controls="chh-lgm" aria-label="%s">%s</button>'
             '<div class="chh-lgm" id="chh-lgm">%s</div></div>'
             '<button type="button" class="chh-ib" id="themeBtn" aria-label="%s">%s</button>'
             '<button type="button" class="chh-ib chh-menu" id="chh-menu" aria-expanded="false" aria-controls="chh-drw" aria-label="%s">%s</button></div>'
             % (esc(S['lang']), SVG_LANG, lg_a, esc(S['theme']), SVG_THEME, esc(S['menu']), SVG_MENU))
    # dải giá: ô trống "—" đến khi JS điền số (lưu đệm làm số hiện gần như ngay)
    it = ''.join('<span class="chh-ti" data-k="%s"><b>%s</b><span class="chh-nm">%s</span><span class="chh-px">—</span><span class="chh-ch">—</span></span>' % (s, s, n, ) for s, n in COINS)
    it += '<span class="chh-ti chh-na" data-k="cap"><span>%s</span><span class="chh-v">—</span><span class="chh-ch"></span></span>' % esc(K['cap'])
    it += '<span class="chh-ti chh-na" data-k="vol"><span>%s</span><span class="chh-v">—</span></span>' % esc(K['vol'])
    it += '<span class="chh-ti chh-na" data-k="oi"><span>%s</span><span class="chh-v">—</span></span>' % esc(K['oi'])
    it += '<span class="chh-ti chh-na" data-k="fund"><span>%s</span><span class="chh-v">—</span></span>' % esc(K['fund'])
    it += '<span class="chh-ti chh-na" data-k="ls"><span>%s</span><span class="chh-v"><span class="chh-up chh-l">—</span> / <span class="chh-dn chh-s">—</span></span></span>' % esc(K['ls'])
    it += '<span class="chh-ti chh-na" data-k="fg"><span>%s</span><span class="chh-v chh-fg"><i></i><span class="chh-fv">—</span></span></span>' % esc(K['fg'])
    tk = ('<div class="chh-tk" role="region" aria-label="%s" data-nosnippet><div class="chh-trk" id="chh-trk"><div class="chh-set">%s</div><div class="chh-set" aria-hidden="true">%s</div></div></div>'
          % (esc(S['tk']), it, it))
    home = S['home']
    bar = ('<header class="chh-hd"><div class="chh-in chh-bar"><a class="chh-brand" href="%s" aria-label="CoinHammy"><img class="mark" src="%s" alt="" width="30" height="30" decoding="async">'
           '<span>Coin<b>Hammy</b></span></a>%s%s</div></header>' % (home, mark, nav, right))
    # ngăn kéo điện thoại
    dx = lambda s, r: '<a class="chh-dx" href="%s"%s>%s<span>%s</span>%s</a>' % (S['ex'] % s, ac('ex:' + s), tile(s), esc(name(s)), rec if r and s in REC else '')
    dtool = ''.join('<a class="chh-tool" href="%s"%s><span class="chh-ic"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
                    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">%s</svg></span><span><b>%s</b><small>%s</small></span></a>'
                    % (S[u], ac(k), ICON[k], esc(S[b]), esc(S[d])) for k, u, b, d in tools)
    t_open = False   # bấm ☰: mọi mục đều đóng, khách tự mở
    drw = ('<div class="chh-drw" id="chh-drw">'
           '<div class="chh-acc%s"><button type="button" aria-expanded="%s" aria-controls="chh-d-tools">%s%s</button><div class="chh-ab" id="chh-d-tools">%s</div></div>'
           % (' open' if t_open else '', 'true' if t_open else 'false', esc(S['nTools']), SVG_DOWN, dtool) +
           '<div class="chh-acc%s"><button type="button" aria-expanded="%s" aria-controls="chh-d-ex">%s%s</button><div class="chh-ab" id="chh-d-ex">'
           '<div class="chh-cap">%s</div><div class="chh-dg n19">%s</div><div class="chh-cap">%s</div><div class="chh-dg n5">%s</div>'
           '<div class="chh-lk"><a href="%s"%s>%s</a><a href="%s"%s>%s</a><a href="%s"%s>%s</a></div></div></div>'
           % ('', 'false', esc(S['nEx']), SVG_DOWN, esc(S['capCex']),
              ''.join(dx(s, True) for s, c, f in EX), esc(S['capRec']), ''.join(dx(s, False) for s in REC),
              S['reviews'], ac('reviews'), esc(S['allRv']), S['rank'], ac('rank'), esc(S['rankL']), S['cmp'], ac('cmp'), esc(S['cmpL'])) +
           '<div class="chh-acc"><a class="chh-dl" href="%s"%s>%s</a></div><div class="chh-acc"><a class="chh-dl" href="%s"%s>%s</a></div></div>'
           % (S['news'], ac('news'), esc(S['nNews']), S['learn'], ac('learn'), esc(S['nLearn'])))
    cfg = json.dumps({'tk': K, 'coins': [c for c, _ in COINS]}, ensure_ascii=False, separators=(',', ':'))
    js = re.sub(r'\n\s*', '\n', JS.strip().replace('__CFG__', cfg))
    css = re.sub(r'\n\s*', '\n', CSS.strip())
    return ('<!--chh--><style id="chh-css">%s</style>\n<div class="chh-stk">%s%s</div>\n%s\n<script>%s</script><!--/chh-->\n'
            % (css, tk, bar, drw, js))


# ---------------- gỡ header cũ ----------------
OLD_SEL = re.compile(r'(?<![\w-])(?:\.top|\.pl|\.pr|\.tools|\.seg|\.icon-btn|\.mpanel|\.mq|\.mqt|\.mqs|\.mqb|\.mb[123]|\.tg-core|\.tg-rays|\.tg-moon'
                     r'|#mpanel|#mrow|#menuBtn|#mq|#themeBtn)(?![\w-])')
DROP_KF = {'mqm'}


def _skip_comment(s, i):
    j = s.find('*/', i + 2)
    return len(s) if j < 0 else j + 2


def _match(s, i):
    d = 0; n = len(s)
    while i < n:
        c = s[i]
        if c == '/' and s.startswith('/*', i): i = _skip_comment(s, i); continue
        if c in '"\'':
            qch = c; i += 1
            while i < n and s[i] != qch:
                if s[i] == '\\': i += 1
                i += 1
            i += 1; continue
        if c == '{': d += 1
        elif c == '}':
            d -= 1
            if d == 0: return i + 1
        i += 1
    raise ValueError('CSS lệch ngoặc')


def _split_sel(sel):
    out = []; d = 0; cur = ''
    for c in sel:
        if c in '([': d += 1
        elif c in ')]': d -= 1
        if c == ',' and d == 0: out.append(cur); cur = ''
        else: cur += c
    out.append(cur); return out


def css_filter(css):
    """bỏ các luật (và phần bộ chọn) chỉ dành cho header cũ; @media rỗng thì bỏ luôn"""
    out = []; i = 0; n = len(css)
    while i < n:
        c = css[i]
        if c.isspace() or c == '}': out.append(c); i += 1; continue
        if css.startswith('/*', i): j = _skip_comment(css, i); out.append(css[i:j]); i = j; continue
        j = i
        while j < n and css[j] not in '{;':
            if css.startswith('/*', j): j = _skip_comment(css, j); continue
            j += 1
        if j >= n: out.append(css[i:]); break
        pre = css[i:j]
        if css[j] == ';': out.append(css[i:j + 1]); i = j + 1; continue
        k = _match(css, j); inner = css[j + 1:k - 1]; p = pre.strip()
        if p.startswith('@'):
            name = p.split()[0].lower()
            if name in ('@media', '@supports', '@container', '@layer'):
                fi = css_filter(inner)
                if re.sub(r'/\*.*?\*/', '', fi, flags=re.S).strip(): out.append(pre + '{' + fi + '}')
            elif not (name.endswith('keyframes') and p.split()[-1] in DROP_KF):
                out.append(css[i:k])
        else:
            sels = _split_sel(pre); keep = [s for s in sels if not OLD_SEL.search(s)]
            if len(keep) == len(sels): out.append(css[i:k])
            elif keep: out.append(re.match(r'\s*', pre).group(0) + ','.join(s.strip() for s in keep) + '{' + inner + '}')
        i = k
    return ''.join(out)


JS_OLD_SEL = "document.querySelectorAll('.pl,.pr'+(window.CH_LG_SEL?','+window.CH_LG_SEL:''))"
JS_NEW_SEL = "(window.CH_LG_SEL?document.querySelectorAll(window.CH_LG_SEL):[])"
JS_OLD_RD = "requestAnimationFrame(function(){requestAnimationFrame(function(){document.querySelectorAll('.seg').forEach(function(g){g.classList.add('rd');});});});\n"
MQ_OLD = ["  var h=base;\n  $('mqt').innerHTML='<div class=\"mqs\">'+h+'</div><div class=\"mqs\" aria-hidden=\"true\">'+h+'</div>';\n  mqFit();\n",
          "function mqFit(){\n  var t=$('mqt'),f=t&&t.firstElementChild;if(!f)return;\n  var w=f.offsetWidth;if(w>0)t.style.setProperty('--mqd',Math.max(20,Math.round(w/34))+'s');\n}\n"
          "window.addEventListener('resize',mqFit);\nif(document.fonts&&document.fonts.ready)document.fonts.ready.then(mqFit);\n"]


def strip_old(t):
    t = re.sub(r'[ \t]*<header class="top">.*?</header>\n?', '', t, count=1, flags=re.S)
    t = re.sub(r'/\*hdr-pre\*/.*?/\*/hdr-pre\*/', '', t, flags=re.S)
    t = re.sub(r'(<style[^>]*>)(.*?)(</style>)', lambda m: m.group(1) + css_filter(m.group(2)) + m.group(3), t, flags=re.S)
    # JS header cũ: bỏ phần thu gọn khi cuộn + menu điện thoại; bộ liquid glass giữ nguyên cho các thẻ khác của trang
    a = t.find('/* header collapse on scroll */')
    if a >= 0:
        b = t.find('/* mobile header menu */', a); c = t.find('  layout();\n})();\n', b)
        assert b > a and c > b, 'không cắt được JS header cũ'
        t = t[:a] + t[c + len('  layout();\n})();\n'):]
    t = t.replace(JS_OLD_SEL, JS_NEW_SEL).replace(JS_OLD_RD, '')
    for s in MQ_OLD: t = t.replace(s, '')
    # thanh "Mở tài khoản" dính đáy (điện thoại) tự ẩn khi menu ☰ mở: đọc trạng thái menu mới thay cho #mpanel cũ
    t = t.replace("var r=src.getBoundingClientRect(),panel=document.getElementById('mpanel');", 'var r=src.getBoundingClientRect();')
    t = t.replace("!(panel&&panel.classList.contains('open'))", "!document.documentElement.classList.contains('chh-open')")
    # khoảng đệm khi nhảy tới neo (#…) và khung dính trong trang: tính theo chiều cao header mới
    t = re.sub(r'scroll-padding-top:\s*\d+px', 'scroll-padding-top:calc(var(--chh-h,0px) + 16px)', t)
    # logo chân trang: nền phẳng cùng màu chữ Hammy (như header)
    t = t.replace('.brand .mark{display:block;flex:none;border-radius:19%;background:linear-gradient(135deg,var(--accent),color-mix(in srgb,var(--accent) 80%,var(--accent2)))}',
                  '.brand .mark{display:block;flex:none;border-radius:19%;background:var(--accent)}')
    t = t.replace('.res{position:sticky;top:16px}', '.res{position:sticky;top:calc(var(--chh-h,0px) + 16px)}')
    t = t.replace('.res{top:calc(72px + env(safe-area-inset-top,0px))}', '.res{top:calc(var(--chh-h,0px) + 16px + env(safe-area-inset-top,0px))}')
    return t


BLOCK = re.compile(r'<!--chh-->.*?<!--/chh-->\n?', re.S)


def page_lang(t):
    m = re.search(r'<html lang="(vi|en)"', t)
    return m.group(1) if m else 'vi'


def apply(t, rel, lang=None):
    """t: nội dung trang; rel: đường dẫn file đầu ra tính từ gốc (vd 'danh-gia-okx.html', 'en/reviews/okx.html', 'tin-tuc/abc.html')"""
    lang = lang or page_lang(t)
    t = BLOCK.sub('', t)
    t = strip_old(t)
    i = t.find('<div class="wrap">')
    assert i >= 0, '%s: không thấy <div class="wrap"> để chèn header' % rel
    return t[:i] + render(lang, rel, alt_links(t, lang), logo(t)) + t[i:]


def verify(rel, t):
    """lỗi (danh sách chuỗi) nếu trang thiếu header mới hoặc còn header cũ"""
    e = []
    if t.count('<!--chh-->') != 1 or t.count('<!--/chh-->') != 1: e.append('%s: header dùng chung không đúng 1 khối' % rel)
    if '<header class="top">' in t or 'id="mpanel"' in t: e.append('%s: còn header cũ' % rel)
    if '/*hdr-pre*/' in t: e.append('%s: còn quy tắc hdr-pre cũ' % rel)
    lg = page_lang(t)
    if '<!--chh-->' in t and ('href="%s"' % T[lg]['news']) not in t[t.index('<!--chh-->'):t.index('<!--/chh-->')]:
        e.append('%s: header không khớp ngôn ngữ trang (%s)' % (rel, lg))
    return e


def sources():
    return sorted(f for f in os.listdir(ROOT) if f.endswith('.html'))


def main():
    check = '--check' in sys.argv
    bad = []
    for f in sources():
        fp = os.path.join(ROOT, f); t = open(fp, encoding='utf-8').read()
        if '<div class="wrap">' not in t: continue
        n = apply(t, f)
        if n != t:
            bad.append(f)
            if not check: open(fp, 'w', encoding='utf-8').write(n)
    t = open(TPL, encoding='utf-8').read(); n = BLOCK.sub('', strip_old(t))      # mẫu bài viết: chỉ gỡ header cũ, publish.py chèn header theo ngôn ngữ
    if n != t:
        bad.append('tools/news/template.html')
        if not check: open(TPL, 'w', encoding='utf-8').write(n)
    if check:
        for b in bad: print('LỆCH', b)
        sys.exit(1 if bad else 0)
    print('đã cập nhật %d file' % len(bad))


if __name__ == '__main__':
    main()

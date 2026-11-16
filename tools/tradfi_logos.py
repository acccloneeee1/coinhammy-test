#!/usr/bin/env python3
"""Logo cho mã TradFi (cổ phiếu, ETF, hàng hoá, ngoại hối) trong ô chọn mã của Công cụ / Biểu đồ / Quy đổi.

Vì sao cần: các sàn (Binance, Bybit, OKX, Bitget) có hợp đồng vĩnh cửu cho cổ phiếu như NVDA, TSLA, SAMSUNG...
API giá của sàn không nói mã nào là cổ phiếu, nên trước đây logo lấy theo ký hiệu từ CoinGecko → NVDA ra logo
một token trùng tên (chiếc lá). File này giữ danh sách mã TradFi (gộp từ API của 4 sàn, 14/11/2026) và cách lấy logo:
  SYM            -> logo cổ phiếu theo chính mã đó (Parqet, dự phòng FMP)
  SYM=T          -> theo mã T (vd SAMSUNG=005930.KS, BYD=1211.HK)
  SYM=~T         -> chỉ dùng FMP với mã T (Parqet sai cho mã đó)
  SYM=@domain    -> favicon của domain (công ty chưa niêm yết: OpenAI, Anthropic...)
  SYM=!          -> không có logo phù hợp (vàng, dầu, chỉ số, tỷ giá...) -> ô chữ cái
Mã có đuôi STOCK / HKD (Bybit, Bitget) tự quy về mã gốc trong trang (chTF).
Mã trùng với coin thật trên sàn spot (BB, QNT, PAXG, XAUT) KHÔNG đưa vào: ưu tiên logo coin.

  python3 tools/tradfi_logos.py          # ghi/cập nhật khối /*chtf*/ vào các trang có ô chọn mã
  python3 tools/tradfi_logos.py --check  # chỉ kiểm tra
Bản Anh (en/...) được en_pages.py dựng lại từ bản Việt nên tự có theo."""
import os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGES = ['cong-cu.html', 'bieu-do.html', 'quy-doi.html']

SYMS = """AAL AAOI AAPL AAPU ABBV ABNB ACHR ACN ACNSTOCK ADBE ADI ADVANTEST AEHR AGPU AKAM ALAB AMAT AMC AMD AMDSTOCK AMGN
AMKR AMZN AMZU ANET ANTHROPIC APD APLD APP APPSTOCK ARKK ARM ARQQ ASML ASTS ASX AVAV AVGO AXON AXP AXTI B200 BA BABA BAC
BBSTOCK BBX BE BHARTIARTL BHP BIDU BIIB BITO BKNG BLSH BMNR BMNU BNC BOT BOTZ BP BRKB BSP BTDR BUD BWET BX BYD BZ CAT CATSTOCK
CBRS CCL CEG CGNX CIEN CIFR CL CLS CLSK CMCSA COHR COIN CONL COP COPPER CORZ COST CPNG CRCL CRDO CRM CRML CRWD CRWV CSCO
CSOPSAMSUNG2L CSOPSK2LHKD CSOPSKHYNIX2L CSOPSS2LHKD CSTOCK CSX CVNA CVXSTOCK CXMT CYPH DASHSTOCK DDOG DE DELL DFEN DHR
DIASTOCK DIS DISK DJT DKNG DOOSBOT DOOSENER DRAM DUOL DXYZ EBAY ECHO EIDO ELICE EQT ETN EURUSD EUV EVEX EWH EWJ EWT EWY EWZ
EWZS FASTRETAILING FCX FISV FLEX FLNC FLY FN FORMSTOCK FOXA FRHC FTNT FUTU FWDI GBPUSD GDX GE GEV GFS GGLL GIGADEV GIGADEVICE
GILD GLW GME GMESTOCK GNRC GOOGL GPRO GRAL GS GTLB H100 HANMI HD HDFCBANK HIMS HINDUNILVR HK0625 HK0700 HK0992 HK1810 HLT
HONHAI HOOD HORIZON HPE HPQ HSI HUAHONG HUT HYUNDAI IBB IBIT IBKR IBM ICICIBANK INDA INFQ INFY INTC INTU INTW IONQ IREN ISRG
ITC ITUB IWM JD JEPQ JIO JMKE JNJ JOBY JP225 JPM JPMUFG JPSONY KAKAO KBFG KIA KIOXIA KLAC KMB KO KOD KODEX200 KOPN KORU KR200
KSTR KTOS KUAISHOU KWEB LAOPU LASERTEC LEN LENOVO LENOVOHKD LGELECTRONICS LGENERGY LIN LITE LLY LMT LNG LRCX LT LULU LUNR LWLG
LYTE MA MAGS MAR MARA MCD MDB MDT MDTSTOCK MEDIATEK MEITU MEITUAN MELI META METU MINIMAX MINIMAXHKD MNST MO MOONSHOT MP MPWR
MRK MRNA MRVL MS MSCI MSFT MSFU MSTR MSTU MU MUFG MURATA MUU MVLL MXL NANYA NATGAS NAVER NBIS NCLD NDX100 NET NETEASE NFLX NG
NIO NKE NOC NOK NOKIA NOKSTOCK NOW NTAP NU NUSTOCK NVDA NVDL NVO NVS OKLO OKTA ON ONDS OPENAI ORCL OSCR OSS OURA OUST OXY PANW
PATH PAYP PBR PCVX PDD PENG PENGSTOCK PEP PFE PG PL PLTR POET POLYMARKET POPMART PURR PYPL QBTS QCOM QLD QNTSTOCK QNTX QQQ
QUBT RAM RDDT RDW REGN RELIANCE RGTI RIO RIOT RIVN RKLB ROK RTXSTOCK RUM SAMSUNG SAMSUNGEM SATL SBIN SBUX SDGR SECZ SENSETIME
SGOV SHAZ SHEIN SHEINHKD SHLD SHOP SIMO SITM SKDD SKHY SKHYNIX SKUU SMCI SMH SMIC SMR SNDK SNOW SNPS SNXX SOFI SOFTBANK SONY
SOXL SOXS SOXX SP500 SPCH SPCX SPIR SPOT SPXL SPY SQQQ SSBIOLOGICS SSPC STM STRC STXSTOCK STXX SUMIELEC TAIYOYUDEN TBT TCS
TEAM TEM TENCENT TENCENTHKD TER TLT TM TMF TOKYOEL TOYOTA TQQQ TSEM TSLA TSLL TSM TSTOCK TTMI TTWO TWASX TWDELTA TWLO TWST
TWTSM TWUMC TXN TZA UBER UMC UNH UNITREE URNM US100 US500 USAR USDBRL USDESTOCK USDEX USDJPY USO UVXY V VALE VEEV VICR VIST
VKTX VLO VOO VRT VRTXSTOCK VST WALSIN WDC WEN WENSTOCK WINBOND WMT WUXIBIO XAG XAU XBI XCU XIAOMI XIAOMIHKD XLE XLF XLI XLK
XLP XLU XLV XNDU XOM XP XPD XPT YAGEO YOFC YPF ZCSH ZHIPU ZHIPUHKD ZHONGJI ZM ZS""".split()

MAP = {
    # Hàn Quốc
    'SAMSUNG': '005930.KS', 'SAMSUNGEM': '009150.KS', 'SKHYNIX': '000660.KS', 'HYUNDAI': '005380.KS', 'HANMI': '042700.KS',
    'LGELECTRONICS': '066570.KS', 'NAVER': '035420.KS', 'KODEX200': '069500.KS', 'KAKAO': '035720.KS', 'KBFG': 'KB',
    'KIA': '000270.KS', 'LGENERGY': '373220.KS', 'SSBIOLOGICS': '207940.KS', 'DOOSENER': '034020.KS', 'DOOSBOT': '454910.KS',
    # Hồng Kông / Trung Quốc
    'HK0700': '0700.HK', 'TENCENT': '0700.HK', 'HK1810': '1810.HK', 'XIAOMI': '1810.HK', 'BYD': '1211.HK', 'MEITUAN': '3690.HK',
    'KUAISHOU': '1024.HK', 'POPMART': '9992.HK', 'HK0992': '0992.HK', 'LENOVO': '0992.HK', 'MEITU': '1357.HK', 'SMIC': '0981.HK',
    'HUAHONG': '1347.HK', 'SENSETIME': '0020.HK', 'HORIZON': '9660.HK', 'YOFC': '6869.HK', 'MINIMAX': '0100.HK', 'ZHIPU': '2513.HK',
    'GIGADEV': '603986.SS', 'GIGADEVICE': '603986.SS', 'ZHONGJI': '300308.SZ', 'WUXIBIO': '2269.HK', 'LAOPU': '6181.HK', 'NETEASE': 'NTES',
    # Nhật
    'TOYOTA': '7203.T', 'JPSONY': '6758.T', 'SOFTBANK': '9984.T', 'TOKYOEL': '8035.T', 'ADVANTEST': '6857.T', 'LASERTEC': '6920.T',
    'KIOXIA': '285A.T', 'JPMUFG': '8306.T', 'FASTRETAILING': '9983.T', 'MURATA': '6981.T', 'SUMIELEC': '5802.T', 'TAIYOYUDEN': '6976.T',
    # Đài Loan
    'TWTSM': '2330.TW', 'MEDIATEK': '2454.TW', 'HONHAI': '2317.TW', 'TWUMC': '2303.TW', 'TWDELTA': '2308.TW', 'TWASX': '3711.TW',
    'NANYA': '2408.TW', 'WINBOND': '2344.TW', 'WALSIN': '1605.TW', 'YAGEO': '2327.TW',
    # Ấn Độ
    'RELIANCE': 'RELIANCE.NS', 'TCS': 'TCS.NS', 'HDFCBANK': 'HDFCBANK.NS', 'ICICIBANK': 'ICICIBANK.NS', 'ITC': 'ITC.NS',
    'SBIN': 'SBIN.NS', 'BHARTIARTL': 'BHARTIARTL.NS', 'HINDUNILVR': '~HINDUNILVR.NS', 'LT': 'LT.NS',
    # Mỹ: Parqet sai hoặc logo trắng trên nền trong suốt
    'BRKB': '~BRKB', 'DJT': '~DJT', 'NOK': '@nokia.com', 'NOKIA': '@nokia.com', 'MRVL': '@marvell.com', 'BBSTOCK': '@blackberry.com',
    # chưa niêm yết (pre-market)
    'OPENAI': '@openai.com', 'ANTHROPIC': '@anthropic.com', 'MOONSHOT': '@moonshot.ai', 'OURA': '@ouraring.com',
    'POLYMARKET': '@polymarket.com', 'SHEIN': '@shein.com', 'UNITREE': '@unitree.com', 'JIO': '@jio.com',
}
NONE = """BZ CL NG XCU COPPER NATGAS XAU XAG XPT XPD USDBRL US100 US500 NDX100 SP500 JP225 HSI KR200 B200 H100 USDEX USDESTOCK
ELICE EUV HK0625 JMKE QNTSTOCK SHLD FLY CXMT CSOPSAMSUNG2L CSOPSK2LHKD CSOPSKHYNIX2L CSOPSS2LHKD""".split()


def data():
    m = dict(MAP); m.update({k: '!' for k in NONE})
    out = []
    for s in sorted(set(SYMS) | set(m)):
        out.append(s + ('=' + m[s] if s in m else ''))
    return ' '.join(out)


# coin chưa có trong kho logo Binance và ngoài top 1000 CoinGecko -> id CoinMarketCap ghi trong tools/coin_logos.json
import json
COIN = json.load(open(os.path.join(ROOT, 'tools', 'coin_logos.json'), encoding='utf-8'))['ids']


def block():
    return '/*chtf*/var CHTF=%r,CHCO=%s;/*/chtf*/\n' % (data(), json.dumps(COIN, separators=(',', ':')))


BLK_RE = re.compile(r'/\*chtf\*/.*?/\*/chtf\*/\n?', re.S)


def apply(t):
    t = BLK_RE.sub('', t)
    i = t.index('function chTF(')
    return t[:i] + block() + t[i:]


if __name__ == '__main__':
    chk = '--check' in sys.argv; bad = []
    for p in PAGES:
        fp = os.path.join(ROOT, p); t = open(fp, encoding='utf-8').read(); n = apply(t)
        if n != t:
            if chk: bad.append(p)
            else: open(fp, 'w', encoding='utf-8').write(n); print('ok', p)
    if chk:
        print('Lệch: ' + ', '.join(bad) if bad else 'CHTF khớp'); sys.exit(1 if bad else 0)

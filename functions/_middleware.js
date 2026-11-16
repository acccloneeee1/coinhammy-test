// Chuyển vĩnh viễn (301) mọi truy cập vào tên miền tạm coinhammy.pages.dev (và www) sang tên miền chính coinhammy.com.
// Giữ nguyên đường dẫn + tham số. Bản xem thử (<hash>.coinhammy.pages.dev) không bị ảnh hưởng.
// Thêm: file nội bộ của repo (công cụ, nhật ký đăng bài, README...) không được công khai -> trả 404.
// Muốn chặn thêm đường dẫn nào thì thêm vào BLOCKED. Lưu ý _routes.json: file .json/.txt/.xml... bị loại khỏi Functions
// (để không tốn lượt chạy), nên phần _routes.json chỉ loại đúng các file cần phục vụ công khai (xem README mục "Chặn file nội bộ").
// BẢN THỬ: thêm .claude (cấu hình Claude Code/ECC nằm trong repo). _routes.json của bản thử không còn loại trừ theo đuôi file
// trên toàn site (/*.js, /*.png...) mà chỉ loại đúng thư mục có file tĩnh, để mọi loại file trong /.claude/ đều đi qua đây.
const BLOCKED = /^\/(tools|functions|node_modules|\.claude)(\/|$)|^\/README\.(md|txt)$|^\/_(headers|redirects|routes\.json)$/i;
// Đường dẫn viết mã hoá (ví dụ /%2Eclaude/...) cũng phải bị chặn: giải mã rồi so lại, chỉ áp cho .claude.
const CLAUDE_DIR = /^\/\.claude(\/|$)/i;
function isClaudePath(pathname) {
  try { return CLAUDE_DIR.test(decodeURIComponent(pathname)); } catch (e) { return false; }
}

export async function onRequest(context) {
  try {
    const url = new URL(context.request.url);
    if (BLOCKED.test(url.pathname) || isClaudePath(url.pathname)) {
      try {   // dùng đúng trang 404 của web nếu lấy được, không thì trả chữ thường
        const nf = await context.env.ASSETS.fetch(new URL('/404.html', url));
        if (nf.status === 200 || nf.status === 404) return new Response(nf.body, { status: 404, headers: { 'content-type': 'text/html; charset=utf-8', 'cache-control': 'no-store', 'x-robots-tag': 'noindex' } });
      } catch (e) { /* xuống dưới */ }
      return new Response('Not found', { status: 404, headers: { 'content-type': 'text/plain; charset=utf-8', 'cache-control': 'no-store', 'x-robots-tag': 'noindex' } });
    }
    if (url.hostname === 'coinhammy.pages.dev' || url.hostname === 'www.coinhammy.com') {
      return Response.redirect('https://coinhammy.com' + url.pathname + url.search, 301);
    }
  } catch (e) { /* lỗi gì cũng cho đi tiếp, không làm sập web */ }
  return context.next();
}

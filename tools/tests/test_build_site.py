"""Test cho tools/build_site.py. Chạy: python -m unittest discover -s tools/tests"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import build_site  # noqa: E402

BIG_CSS = b'.card{color:red}' * 200          # 3200 byte, vượt ngưỡng tách CSS
BIG_JS = b'var total=1+1;' * 400             # 5600 byte, vượt ngưỡng tách JS
SMALL_CSS = b'.tiny{margin:0}'


def page(*parts):
    return b'<!doctype html><html><head>' + b''.join(parts) + b'</head><body></body></html>'


def style(body, open_tag=b'<style>'):
    return open_tag + body + b'</style>'


def script(body, open_tag=b'<script>'):
    return open_tag + body + b'</script>'


class IterBlocksTest(unittest.TestCase):
    def test_yields_style_and_script_blocks_in_document_order(self):
        html = page(style(b'a{}'), script(b'var a;'))

        blocks = list(build_site.iter_blocks(html))

        self.assertEqual([(b.kind, b.body) for b in blocks], [('style', b'a{}'), ('script', b'var a;')])

    def test_ignores_style_tag_written_inside_html_comment(self):
        html = page(b'<!-- <style>a{}</style> -->')

        self.assertEqual(list(build_site.iter_blocks(html)), [])

    def test_does_not_look_for_blocks_inside_a_script_body(self):
        html = page(script(b'var s="<style>a{}</style>";'))

        blocks = list(build_site.iter_blocks(html))

        self.assertEqual([b.kind for b in blocks], ['script'])

    def test_span_covers_whole_element(self):
        html = page(style(b'a{}'))

        block = next(build_site.iter_blocks(html))

        self.assertEqual(html[block.start:block.end], b'<style>a{}</style>')


class PlanAssetsTest(unittest.TestCase):
    def test_extracts_block_shared_by_two_pages(self):
        pages = {'a.html': page(style(BIG_CSS)), 'b.html': page(style(BIG_CSS))}

        assets = build_site.plan_assets(pages)

        self.assertEqual(list(assets.values()), [BIG_CSS])
        self.assertTrue(next(iter(assets)).startswith('assets/c-'))

    def test_keeps_block_that_appears_on_only_one_page(self):
        pages = {'a.html': page(style(BIG_CSS)), 'b.html': page(style(BIG_CSS + b'.x{}'))}

        self.assertEqual(build_site.plan_assets(pages), {})

    def test_block_repeated_within_one_page_does_not_count_as_shared(self):
        pages = {'a.html': page(style(BIG_CSS), style(BIG_CSS))}

        self.assertEqual(build_site.plan_assets(pages), {})

    def test_keeps_block_below_size_threshold(self):
        pages = {'a.html': page(style(SMALL_CSS)), 'b.html': page(style(SMALL_CSS))}

        self.assertEqual(build_site.plan_assets(pages), {})

    def test_keeps_font_block_inline(self):
        fonts = b'<!--fonts-->' + style(BIG_CSS) + b'<!--/fonts-->'
        pages = {'a.html': page(fonts), 'b.html': page(fonts)}

        self.assertEqual(build_site.plan_assets(pages), {})

    def test_extracts_block_placed_after_font_region(self):
        fonts = b'<!--fonts-->' + style(SMALL_CSS) + b'<!--/fonts-->'
        pages = {'a.html': page(fonts, style(BIG_CSS)), 'b.html': page(fonts, style(BIG_CSS))}

        self.assertEqual(list(build_site.plan_assets(pages).values()), [BIG_CSS])

    def test_keeps_css_with_relative_url(self):
        css = BIG_CSS + b'.bg{background:url(img/a.png)}'
        pages = {'a.html': page(style(css)), 'b.html': page(style(css))}

        self.assertEqual(build_site.plan_assets(pages), {})

    def test_extracts_css_with_root_and_data_urls(self):
        css = BIG_CSS + b'.a{background:url(/img/a.webp)}.b{background:url("data:image/png;base64,AA")}'
        pages = {'a.html': page(style(css)), 'b.html': page(style(css))}

        self.assertEqual(list(build_site.plan_assets(pages).values()), [css])

    def test_keeps_json_ld_and_other_attributed_scripts(self):
        json_ld = script(BIG_JS, b'<script type="application/ld+json">')
        pages = {'a.html': page(json_ld), 'b.html': page(json_ld)}

        self.assertEqual(build_site.plan_assets(pages), {})

    def test_extracts_shared_plain_script(self):
        pages = {'a.html': page(script(BIG_JS)), 'b.html': page(script(BIG_JS))}

        assets = build_site.plan_assets(pages)

        self.assertEqual(list(assets.values()), [BIG_JS])
        self.assertTrue(next(iter(assets)).endswith('.js'))


class RewritePageTest(unittest.TestCase):
    def setUp(self):
        self.pages = {
            'a.html': page(style(SMALL_CSS), style(BIG_CSS), script(BIG_JS), script(b'var onlyA=1;')),
            'b.html': page(style(BIG_CSS), script(BIG_JS)),
        }
        self.assets = build_site.plan_assets(self.pages)

    def test_replaces_shared_blocks_with_references_at_same_position(self):
        css_name = build_site.asset_name('style', BIG_CSS)
        js_name = build_site.asset_name('script', BIG_JS)

        rewritten = build_site.rewrite_page(self.pages['a.html'], self.assets)

        expected = page(style(SMALL_CSS),
                        b'<link rel="stylesheet" href="/' + css_name.encode() + b'">',
                        b'<script src="/' + js_name.encode() + b'"></script>',
                        script(b'var onlyA=1;'))
        self.assertEqual(rewritten, expected)

    def test_keeps_id_of_header_style_on_the_link(self):
        header = style(BIG_CSS, b'<style id="chh-css">')
        pages = {'a.html': page(header), 'b.html': page(header)}

        rewritten = build_site.rewrite_page(pages['a.html'], build_site.plan_assets(pages))

        self.assertIn(b'<link rel="stylesheet" id="chh-css" href="/assets/c-', rewritten)

    def test_page_without_shared_blocks_is_unchanged(self):
        html = page(style(SMALL_CSS))

        self.assertEqual(build_site.rewrite_page(html, self.assets), html)

    def test_restore_gives_back_the_original_page(self):
        for rel, html in self.pages.items():
            rewritten = build_site.rewrite_page(html, self.assets)

            self.assertEqual(build_site.restore_page(rewritten, self.assets), html, rel)


class TransformTest(unittest.TestCase):
    def test_returns_rewritten_pages_and_assets(self):
        pages = {'a.html': page(style(BIG_CSS)), 'b.html': page(style(BIG_CSS))}

        rewritten, assets = build_site.transform(pages)

        self.assertEqual(len(assets), 1)
        self.assertLess(len(rewritten['a.html']), len(pages['a.html']))

    def test_does_not_modify_the_input_pages(self):
        original = page(style(BIG_CSS))
        pages = {'a.html': original, 'b.html': original}

        build_site.transform(pages)

        self.assertEqual(pages, {'a.html': original, 'b.html': original})


class AssetNameTest(unittest.TestCase):
    def test_name_depends_only_on_content(self):
        self.assertEqual(build_site.asset_name('style', BIG_CSS), build_site.asset_name('style', BIG_CSS))
        self.assertNotEqual(build_site.asset_name('style', BIG_CSS), build_site.asset_name('style', BIG_CSS + b' '))

    def test_css_and_js_use_different_prefix_and_extension(self):
        self.assertRegex(build_site.asset_name('style', b'x'), r'^assets/c-[0-9a-f]{16}\.css$')
        self.assertRegex(build_site.asset_name('script', b'x'), r'^assets/j-[0-9a-f]{16}\.js$')


if __name__ == '__main__':
    unittest.main()

"""Test cho các hàm thuần của bộ đăng bài (tools/news/news_*.py). Chạy: python -m unittest discover -s tools/tests"""
import contextlib
import io
import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(REPO)   # news_core lấy thư mục gốc của kho từ thư mục đang đứng
sys.path.insert(0, os.path.join(REPO, 'tools'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'news'))
import news_article  # noqa: E402
import news_core  # noqa: E402
import news_images  # noqa: E402
import news_lists  # noqa: E402
import news_related  # noqa: E402


class SlugifyTest(unittest.TestCase):
    def test_removes_vietnamese_marks_and_joins_words_with_dashes(self):
        self.assertEqual(news_core.slugify('Bitcoin giảm mạnh'), 'bitcoin-giam-manh')

    def test_converts_d_with_stroke(self):
        self.assertEqual(news_core.slugify('Đồng đô la'), 'dong-do-la')

    def test_collapses_punctuation_and_trims_dashes(self):
        self.assertEqual(news_core.slugify('  ETF: 80,000 USD!  '), 'etf-80-000-usd')

    def test_caps_length_at_80_characters(self):
        self.assertLessEqual(len(news_core.slugify('tu ' * 60)), 80)


class EscTest(unittest.TestCase):
    def test_escapes_html_and_quotes(self):
        self.assertEqual(news_core.esc('<a href="x">'), '&lt;a href=&quot;x&quot;&gt;')

    def test_none_becomes_empty_string(self):
        self.assertEqual(news_core.esc(None), '')


class ArticlePathTest(unittest.TestCase):
    def test_old_vietnamese_article_uses_kind_prefix(self):
        self.assertEqual(news_core.vpath({'slug': 'abc'}, 'news'), '/tin/abc')

    def test_vietnamese_article_with_dir_uses_that_dir(self):
        self.assertEqual(news_core.vpath({'slug': 'abc', 'dir': 'tin-tuc'}, 'news'), '/tin-tuc/abc')

    def test_english_paths_per_kind(self):
        self.assertEqual(news_core.epath({'slug_en': 'x-y'}, 'news'), '/en/news/x-y')
        self.assertEqual(news_core.epath({'slug_en': 'x-y'}, 'learn'), '/en/learn/x-y')

    def test_item_paths_returns_both_addresses(self):
        article = {'slug': 'abc', 'dir': 'kien-thuc', 'slug_en': 'a-b-c'}

        self.assertEqual(news_core.item_paths(article, 'learn'), {'u': '/kien-thuc/abc', 'ue': '/en/learn/a-b-c'})


class FmtTimeTest(unittest.TestCase):
    def test_vietnamese_format_in_vietnam_time(self):
        self.assertEqual(news_core.fmt_time('2026-11-05T03:30:00+00:00', 'vi'), '05/11/2026 · 10:30')

    def test_english_format_names_the_time_zone(self):
        self.assertEqual(news_core.fmt_time('2026-11-05T03:30:00+00:00', 'en'), 'Nov 05, 2026 · 10:30 (GMT+7)')


class CleanBodyTest(unittest.TestCase):
    def test_removes_script_blocks(self):
        self.assertEqual(news_article.clean_body('<script>alert(1)</script><p>a</p>'), '<p>a</p>')

    def test_removes_inline_event_handlers(self):
        self.assertEqual(news_article.clean_body('<p onclick="x()">Hi</p>'), '<p>Hi</p>')

    def test_external_link_is_removed_but_text_kept(self):
        self.assertEqual(news_article.clean_body('<p><a href="https://example.org/x">chữ</a></p>'), '<p>chữ</p>')

    def test_internal_link_stays(self):
        body = '<p><a href="/tin-tuc/abc">bài</a></p>'

        self.assertEqual(news_article.clean_body(body), body)

    def test_drops_tags_outside_the_allowed_list(self):
        self.assertEqual(news_article.clean_body('<div><span>x</span></div>'), 'x')


class WordsTest(unittest.TestCase):
    def test_counts_words_ignoring_tags(self):
        self.assertEqual(news_article.words('<p>một hai</p><p>ba</p>'), 3)


class SlugEnForTest(unittest.TestCase):
    def test_existing_english_slug_is_kept(self):
        self.assertEqual(news_article.slug_en_for({'slug_en': 'fixed', 'en': {'title': 'Other'}}, set()), 'fixed')

    def test_built_from_english_title_without_thousands_comma(self):
        article = {'en': {'title': 'Bitcoin Falls Below $80,000 on ETF Outflows'}}

        self.assertEqual(news_article.slug_en_for(article, set()), 'bitcoin-falls-below-80000-on-etf-outflows')

    def test_percent_sign_is_spelled_out(self):
        self.assertEqual(news_article.slug_en_for({'en': {'title': 'ASTER Plunges 32%'}}, set()), 'aster-plunges-32-percent')

    def test_does_not_end_with_a_linking_word(self):
        article = {'en': {'title': 'Crypto Markets Slide Sharply as'}}

        self.assertEqual(news_article.slug_en_for(article, set()), 'crypto-markets-slide-sharply')

    def test_adds_number_when_slug_is_taken(self):
        article = {'en': {'title': 'ASTER Plunges 32%'}}

        self.assertEqual(news_article.slug_en_for(article, {'aster-plunges-32-percent'}), 'aster-plunges-32-percent-2')


class RelatedTokensTest(unittest.TestCase):
    def test_keeps_meaningful_words_without_marks(self):
        tokens = news_related._tok('Bitcoin và ETF của Mỹ')

        self.assertIn('bitcoin', tokens)
        self.assertIn('etf', tokens)

    def test_drops_stop_words_and_words_shorter_than_three_letters(self):
        tokens = news_related._tok('to be của btc')

        self.assertEqual(tokens, {'btc'})


class RelatedPointsTest(unittest.TestCase):
    def test_every_plain_paragraph_end_is_an_insertion_point(self):
        self.assertEqual(news_related._rel_points('<p>a</p><p>b</p>'), [8, 16])

    def test_paragraph_inside_a_list_is_not_a_point(self):
        body = '<ul><li><p>x</p></li></ul><p>y</p>'

        self.assertEqual(news_related._rel_points(body), [len(body)])

    def test_paragraph_right_before_an_image_is_not_a_point(self):
        self.assertEqual(news_related._rel_points('<p>a</p><p>[[img:0]]</p>'), [])


class FigPartsTest(unittest.TestCase):
    def test_credit_is_shown_only_for_attribution_licences(self):
        image = {'caption_vi': 'Biểu đồ', 'credit': 'Tác giả', 'license': 'CC BY'}

        self.assertEqual(news_images.fig_parts(image, 'vi'), ('Biểu đồ', 'Tác giả'))

    def test_credit_is_hidden_for_other_licences(self):
        image = {'caption_en': 'Chart', 'credit': 'Someone', 'license': 'Unsplash'}

        self.assertEqual(news_images.fig_parts(image, 'en'), ('Chart', ''))


class SitemapRowsTest(unittest.TestCase):
    def test_one_row_per_language_each_declaring_both_versions(self):
        rows = news_lists.sm_rows('https://x/vi', 'https://x/en', '2026-11-05')

        self.assertEqual(len(rows), 2)
        self.assertIn('<loc>https://x/vi</loc><lastmod>2026-11-05</lastmod>', rows[0])
        self.assertIn('<loc>https://x/en</loc>', rows[1])
        for row in rows:
            self.assertIn('hreflang="x-default" href="https://x/vi"', row)


class PaginationTest(unittest.TestCase):
    def test_first_page_is_the_list_page_itself(self):
        self.assertEqual(news_lists.pg_path('news', 'vi', 1), '/tin-tuc')

    def test_later_pages_use_language_specific_names(self):
        self.assertEqual(news_lists.pg_path('news', 'vi', 3), '/tin-tuc/trang-3')
        self.assertEqual(news_lists.pg_path('news', 'en', 2), '/en/news/page-2')

    def test_fit_returns_first_candidate_within_length_range(self):
        self.assertEqual(news_lists.pg_fit(['a' * 10, 'b' * 155, 'c' * 156], 150, 160, 'mô tả'), 'b' * 155)

    def test_fit_stops_when_no_candidate_fits(self):
        silent = io.StringIO()

        with contextlib.redirect_stdout(silent), contextlib.redirect_stderr(silent), self.assertRaises(SystemExit):
            news_lists.pg_fit(['quá ngắn'], 150, 160, 'mô tả')


if __name__ == '__main__':
    unittest.main()

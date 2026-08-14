import unittest
from unittest.mock import patch

from utils.html_utils import extract_article_text
from services.feed_service import FeedService


class FeedContentExtractionTest(unittest.TestCase):
    def test_extract_article_text_prefers_article_body(self):
        html = '''
        <html>
          <body>
            <div class="sidebar">广告内容不要显示</div>
            <article>
              <h1>示例标题</h1>
              <p>第一段正文内容。</p>
              <p>第二段正文内容。</p>
            </article>
            <div class="related">推荐阅读</div>
          </body>
        </html>
        '''

        text = extract_article_text(html)

        self.assertIn('第一段正文内容', text)
        self.assertIn('第二段正文内容', text)
        self.assertNotIn('广告内容不要显示', text)
        self.assertNotIn('推荐阅读', text)


class FeedContentSelectionTest(unittest.TestCase):
    def test_extract_entry_content_uses_feed_summary_without_web_fetch(self):
        """列表加载必须只用 feed 自带内容,不得逐篇抓网页(会拖慢整个列表)。"""
        summary_text = '短摘要内容' * 10
        entry = {'summary': f'<p>{summary_text}</p>', 'link': 'https://example.com/x'}

        with patch('services.feed_service.fetch_article_html') as mock_fetch:
            text = FeedService._extract_entry_content(entry)

        self.assertEqual(text.strip(), summary_text)
        mock_fetch.assert_not_called()


if __name__ == '__main__':
    unittest.main()

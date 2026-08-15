import unittest

from utils.html_utils import extract_article_blocks


class ExtractArticleBlocksTest(unittest.TestCase):
    def test_blocks_preserve_order_and_include_images(self):
        html = '''
        <html><body>
          <article>
            <p>第一段正文内容,足够长的一段文字说明。</p>
            <img src="/images/hero.jpg">
            <p>第二段正文内容,同样也是一段足够长的文字。</p>
            <figure><img data-src="https://cdn.example.com/fig.png"></figure>
            <p>第三段正文内容,最后一段足够长的文字段落。</p>
          </article>
          <nav>导航内容不要显示</nav>
        </body></html>
        '''

        blocks = extract_article_blocks(html, 'https://example.com/post/1')

        self.assertEqual(
            [b['type'] for b in blocks],
            ['text', 'image', 'text', 'image', 'text']
        )
        # 相对地址解析为绝对地址;懒加载 data-src 优先
        self.assertEqual(blocks[1]['src'], 'https://example.com/images/hero.jpg')
        self.assertEqual(blocks[3]['src'], 'https://cdn.example.com/fig.png')
        self.assertIn('第一段正文内容', blocks[0]['text'])
        self.assertNotIn('导航', blocks[4]['text'])

    def test_small_icons_and_data_uris_are_skipped(self):
        html = '''
        <html><body>
          <article>
            <p>正文段落,一段足够长的文字内容说明。</p>
            <img src="data:image/png;base64,AAAA" width="100" height="100">
            <img src="/icon.png" width="20" height="20">
            <img src="/photo.jpg">
          </article>
        </body></html>
        '''

        blocks = extract_article_blocks(html, 'https://example.com/a')

        images = [b['src'] for b in blocks if b['type'] == 'image']
        self.assertEqual(images, ['https://example.com/photo.jpg'])


if __name__ == '__main__':
    unittest.main()

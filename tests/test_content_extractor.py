import unittest
from unittest.mock import patch

from utils.content_extractor import extract_article_content


class BoilerplateRemovalTest(unittest.TestCase):
    """合成页面验证:导航/推荐/广告/评论/分享/页脚等噪音应全部过滤。"""

    HTML = '''
    <html><head>
      <meta property="og:title" content="合成文章标题">
      <meta name="author" content="张三">
      <meta property="article:published_time" content="2026-08-01T10:00:00+08:00">
    </head><body>
      <nav class="site-nav">首页 新闻 科技 关于我们</nav>
      <header class="page-header">网站头部菜单</header>
      <div class="ad-banner">这里是广告位</div>
      <article class="article-content">
        <p>正文第一段,讲的是文章的核心内容,足够长的一段文字,详细展开论述了这个问题。</p>
        <div class="share-buttons">分享到微博 分享到微信</div>
        <img src="/images/body-pic.jpg">
        <p>正文第二段,继续展开文章的内容,同样足够长的一段文字,补充了更多背景信息。</p>
        <p class="related-articles">推荐文章:另一篇无关的文章标题</p>
        <figure><img data-src="https://cdn.example.com/fig2.png"></figure>
        <p>正文第三段,收尾总结,一段足够长的文字内容说明,对全文做了最后的概括。</p>
      </article>
      <aside class="sidebar">侧边栏内容</aside>
      <section class="comments">评论区:网友A 网友B</section>
      <div class="newsletter">订阅我们的邮件</div>
      <footer class="site-footer">页脚 隐私政策 使用条款</footer>
    </body></html>
    '''

    def test_boilerplate_is_removed_and_metadata_extracted(self):
        # 合成页面过于简单,trafilatura 打分器会失真;屏蔽它以测试启发式回退路径
        with patch('utils.content_extractor.trafilatura.bare_extraction', return_value=None):
            result = extract_article_content(self.HTML, 'https://example.com/post/1')

        # 元数据提取(trafilatura 或 meta 兜底,日期可能被规范化为 YYYY-MM-DD)
        self.assertEqual(result['title'], '合成文章标题')
        self.assertEqual(result['author'], '张三')
        self.assertTrue(result['date'].startswith('2026-08-01'), result['date'])

        # 正文块:三段落 + 两张图片,按序
        self.assertEqual(
            [b['type'] for b in result['blocks']],
            ['text', 'image', 'text', 'image', 'text']
        )
        self.assertEqual(result['blocks'][1]['src'], 'https://example.com/images/body-pic.jpg')
        self.assertEqual(result['blocks'][3]['src'], 'https://cdn.example.com/fig2.png')

        all_text = result['text']
        for noise in ['首页', '广告位', '分享到', '推荐文章', '侧边栏', '网友A', '订阅我们的邮件', '隐私政策']:
            self.assertNotIn(noise, all_text, f"噪音未被过滤: {noise}")
        self.assertIn('正文第一段', all_text)
        self.assertIn('正文第三段', all_text)

        # 正文 HTML 存在且不含噪音
        self.assertIn('article-content', result['html'])
        self.assertNotIn('site-footer', result['html'])

    def test_affiliate_disclaimer_and_author_card_are_removed(self):
        """联盟营销免责声明与作者简介卡不应出现在正文中。"""
        html = '''
        <html><body>
          <article class="article-content">
            <p>正文段落,一段足够长的文章内容说明,详细介绍了事情的前因后果和发展经过。</p>
            <p class="affiliate-disclaimer-text">
              When you buy through links in our articles, we may earn a small
              commission. This does not affect our editorial independence.
            </p>
            <p>正文第二段,继续展开的一段足够长的文字,补充了很多相关的背景信息。</p>
            <p>正文第三段,最后一段总结性的文字内容,对全文观点做了完整的回顾与梳理。</p>
          </article>
          <div class="wp-block-techcrunch-post-authors">
            <div class="wp-block-tc23-author-card">
              <div class="wp-block-tc23-author-card-bio">
                Jagmeet covers startups from India. You can contact him by
                emailing mail@journalistjagmeet.com
              </div>
            </div>
          </div>
        </body></html>
        '''

        with patch('utils.content_extractor.trafilatura.bare_extraction', return_value=None):
            result = extract_article_content(html, 'https://example.com/post/2')

        all_text = result['text'].lower()
        self.assertNotIn('commission', all_text)
        self.assertNotIn('editorial independence', all_text)
        self.assertNotIn('jagmeet', all_text)
        self.assertNotIn('journalistjagmeet', all_text)
        self.assertEqual(len(result['blocks']), 3)  # 只有三段正文
        self.assertNotIn('author-card', result['html'])

    def test_empty_html_returns_empty_result(self):
        result = extract_article_content('')
        self.assertEqual(result['text'], '')
        self.assertEqual(result['blocks'], [])
        self.assertEqual(result['title'], '')


if __name__ == '__main__':
    unittest.main()

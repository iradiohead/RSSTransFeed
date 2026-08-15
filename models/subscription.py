"""Data models for subscriptions and articles"""
from datetime import datetime
from typing import Optional


class Subscription:
    """表示一个 RSS 订阅源。

    这个模型保存订阅 URL、标题和最后更新时间，用于 UI 展示和 JSON 持久化。
    """
    
    def __init__(self, id: str, url: str, title: str, last_updated: Optional[str] = None):
        """创建一个订阅对象。

        Args:
            id: 订阅唯一标识符，通常来自列表索引或生成 ID。
            url: RSS 源地址。
            title: 订阅源标题，例如站点名或 RSS 名称。
            last_updated: 最后更新时间，若为空则取当前时间。
        """
        self.id = id
        self.url = url
        self.title = title
        self.last_updated = last_updated or datetime.now().isoformat()
        self.articles = []  # Initialize articles list for UI compatibility
    
    def to_dict(self):
        """把订阅对象转换成可保存到 JSON 的字典。

        Returns:
            包含订阅主信息的字典，用于写入 subscriptions.json。
        """
        return {
            'id': self.id,
            'url': self.url,
            'title': self.title,
            'last_updated': self.last_updated
        }
    
    @staticmethod
    def from_dict(data: dict):
        """从字典恢复订阅对象。

        Args:
            data: JSON 读取后的订阅数据。

        Returns:
            还原后的 Subscription 实例。
        """
        sub = Subscription(
            id=data.get('id'),
            url=data.get('url'),
            title=data.get('title'),
            last_updated=data.get('last_updated')
        )
        # Initialize articles for backwards compatibility
        sub.articles = []
        return sub


class Article:
    """表示一篇 RSS 文章。

    该模型保存文章标题、链接、正文、发布时间等信息，供列表显示和内容渲染。
    """
    
    def __init__(self, title: str, link: str, content: str,
                 pub_date: str = "", author: str = "",
                 feed_title: str = "", guid: str = "", read: bool = False):
        """创建一篇文章对象。

        Args:
            title: 文章标题。
            link: 原文链接。
            content: 展示正文内容，通常从 RSS 摘要或网页正文提取。
            pub_date: 发布日期。
            author: 作者名。
            feed_title: 所属订阅源标题。
            guid: 唯一标识，作为已读状态判断依据。
            read: 是否已读，用于文章列表中的未读标记。
        """
        self.title = title
        self.link = link
        self.content = content
        self.pub_date = pub_date
        self.author = author
        self.feed_title = feed_title
        self.guid = guid
        self.read = read
        # 译文缓存(会话内有效,不持久化);非空表示已翻译
        self.translated_title = ""
        self.translated_content = ""
        # 块级译文:与 blocks 中的文本块对齐,保证图片位置不变;None 表示整文翻译模式
        self.translated_block_texts = None
        # 图文渲染缓存(会话内有效,不持久化):
        # blocks: 按文档顺序的正文块(段落/图片);extra_image_urls: feed 长文时追加文末的图片;
        # photos: {图片URL: PhotoImage},None 表示尚未下载
        self.blocks = []
        self.extra_image_urls = []
        self.photos = None
        # 原始 PIL 图片缓存(URL -> PIL.Image),用于按窗口宽度自适应缩放
        self.pil_images = {}
        # 正文提取算法产出的干净正文 HTML(会话内有效)
        self.clean_html = ""
        # 网页全文抓取是否失败过(失败时详情页显示摘要提示,下次选中会重试)
        self.full_text_failed = False
    
    def to_dict(self):
        """把文章对象转换成字典，便于保存到 JSON 或传递给其它模块。

        Returns:
            文章字段的序列化字典。
        """
        return {
            'title': self.title,
            'link': self.link,
            'content': self.content,
            'pubDate': self.pub_date,
            'author': self.author,
            'feedTitle': self.feed_title,
            'guid': self.guid
        }
    
    @staticmethod
    def from_dict(data: dict):
        """从字典恢复文章对象。

        Args:
            data: 文章数据字典。

        Returns:
            还原后的 Article 实例。
        """
        return Article(
            title=data.get('title', 'No Title'),
            link=data.get('link', ''),
            content=data.get('content', ''),
            pub_date=data.get('pubDate', ''),
            author=data.get('author', ''),
            feed_title=data.get('feedTitle', ''),
            guid=data.get('guid', '')
        )

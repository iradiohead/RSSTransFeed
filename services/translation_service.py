"""Service for detecting article language and translating into the OS language"""
import locale
import os

# Google 网页翻译单次请求的文本长度上限附近,留出余量
CHUNK_SIZE = 4500

# 块级翻译的批量上限与分隔符(翻译后按分隔符切回独立块)
BLOCK_BATCH_SIZE = 4000
BLOCK_SEPARATOR = "@@@"


class TranslationService:
    """负责检测文章语言,并在与操作系统语言不同时翻译成系统语言。

    语言检测使用 langdetect(纯 Python,基于 Google 语料);
    翻译使用 deep-translator 的 Google 网页翻译(source='auto' 自动识别),
    无需 API key,需要联网。长文本自动分块翻译。
    """

    @staticmethod
    def get_os_language() -> str:
        """返回操作系统界面语言代码(翻译目标),例如 'zh-CN'。

        macOS/Linux 从 locale 读取;读取失败时回退环境变量,再不行默认 'en'。
        """
        try:
            lang, _ = locale.getdefaultlocale()
        except Exception:
            lang = None
        if not lang:
            lang = os.environ.get('LANG', '')
        if not lang:
            return 'en'
        # 'zh_CN' -> 'zh-CN';'en_US.UTF-8' -> 'en-US'(去掉编码后缀)
        if '_' in lang:
            base, region = lang.split('_', 1)
            region = region.split('.')[0]
            return f"{base.lower()}-{region.upper()}"
        return lang.lower()

    @staticmethod
    def detect_language(text: str) -> str:
        """检测文本语言代码(如 'en'、'zh-cn'、'ja')。"""
        from langdetect import detect
        sample = (text or '').strip()[:2000]
        return detect(sample) if sample else ''

    @staticmethod
    def _short_code(lang: str) -> str:
        """'zh-CN' -> 'zh','en_US' -> 'en'。判断是否同一语言用。"""
        return (lang or '').split('-')[0].split('_')[0].lower()

    @staticmethod
    def _translate_chunked(text: str, target: str) -> str:
        """把长文本分块翻译后拼接,避免单次请求超长。"""
        from deep_translator import GoogleTranslator

        chunks = [
            text[i:i + CHUNK_SIZE]
            for i in range(0, len(text), CHUNK_SIZE)
        ]
        translated = []
        for chunk in chunks:
            if not chunk.strip():
                translated.append(chunk)
                continue
            translated.append(
                GoogleTranslator(source='auto', target=target).translate(chunk)
            )
        return "".join(translated)

    @staticmethod
    def needs_translation(sample: str, target: str = None) -> bool:
        """判断文本语言是否与目标语言不同(不同才需要翻译)。"""
        target = target or TranslationService.get_os_language()
        sample = (sample or '').strip()[:2000]
        if not sample:
            return False
        source = TranslationService.detect_language(sample)
        return TranslationService._short_code(source) != TranslationService._short_code(target)

    @staticmethod
    def translate_blocks(texts, target: str = None):
        """按批翻译文本块列表,返回等长的译文列表。

        多个文本块用分隔符拼接后合并翻译(减少请求数),再按分隔符切回
        独立块,保持块序与原文一致,供图文混排视图在原文位置嵌入译文。

        Args:
            texts: 待翻译的文本块列表。
            target: 目标语言代码,缺省时使用操作系统语言。

        Returns:
            与输入等长的译文列表;若翻译后分隔符丢失(无法切回),返回 None,
            调用方应回退到整文翻译。网络失败等异常向上抛出。
        """
        from deep_translator import GoogleTranslator

        target = target or TranslationService.get_os_language()

        # 只翻译非空块,空块保持为空
        non_empty = [(i, t) for i, t in enumerate(texts) if (t or '').strip()]

        batches, cur, cur_len = [], [], 0
        for i, t in non_empty:
            if cur and cur_len + len(t) + len(BLOCK_SEPARATOR) > BLOCK_BATCH_SIZE:
                batches.append(cur)
                cur, cur_len = [], 0
            cur.append((i, t))
            cur_len += len(t) + len(BLOCK_SEPARATOR)
        if cur:
            batches.append(cur)

        result = [""] * len(texts)
        for batch in batches:
            items = [t for _, t in batch]
            joined = ("\n" + BLOCK_SEPARATOR + "\n").join(items)
            out = GoogleTranslator(source='auto', target=target).translate(joined)
            parts = [p.strip() for p in out.split(BLOCK_SEPARATOR)]
            if len(parts) != len(items):
                return None  # 分隔符被翻译吞掉,放弃块级翻译
            for (i, _), p in zip(batch, parts):
                result[i] = p
        return result

    @staticmethod
    def translate_article(title: str, content: str, target: str = None):
        """翻译文章标题与正文。

        Args:
            title: 文章标题。
            content: 文章正文。
            target: 目标语言代码,缺省时使用操作系统语言。

        Returns:
            文章语言与目标语言相同时返回 None(无需翻译);
            否则返回 (翻译后标题, 翻译后正文) 元组;
            网络失败等异常会向上抛出,由调用方展示错误。
        """
        target = target or TranslationService.get_os_language()
        if not TranslationService.needs_translation(title + "\n" + (content or ''), target):
            return None

        translated_title = (
            TranslationService._translate_chunked(title, target) if title else title
        )
        translated_content = (
            TranslationService._translate_chunked(content, target) if content else content
        )
        return translated_title, translated_content

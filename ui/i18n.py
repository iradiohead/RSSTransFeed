"""UI 文案国际化:按系统语言选择界面文案。

以中文文案为键、英文翻译为值;启动时检测操作系统语言,
中文系统显示中文,英文等其它系统显示英文。
"""
from services.translation_service import TranslationService

# 以中文文案为键的翻译表(格式串使用命名占位符)
_TRANSLATIONS = {
    # 通用
    "错误": "Error",
    "成功": "Success",
    # 侧边栏与按钮
    "订阅": "Subscriptions",
    "在浏览器中打开": "Open in Browser",
    "翻译": "Translate",
    "翻译中...": "Translating...",
    "已翻译": "Translated",
    "刷新订阅": "Refresh",
    "关于": "About",
    # 文章列表
    "正在加载文章...": "Loading articles...",
    "加载失败或无文章，请点击「刷新订阅」重试":
        'Failed to load or no articles. Click "Refresh" to retry.',
    "[已读] ": "[Read] ",
    "[图片加载失败]": "[Image failed to load]",
    # 文章详情标签
    "标题: {title}\n\n": "Title: {title}\n\n",
    "(原标题: {title})\n\n": "(Original title: {title})\n\n",
    "作者: {author}\n\n": "Author: {author}\n\n",
    "链接: {link}\n\n": "Link: {link}\n\n",
    "发布时间: {date}\n\n": "Published: {date}\n\n",
    "内容:\n": "Content:\n",
    "内容(已翻译):\n": "Content (translated):\n",
    # 提示与错误
    "⚠ 全文获取失败,以下为摘要(重新选中本文会自动重试)\n\n":
        "⚠ Failed to fetch full text; showing summary (re-select this article to retry)\n\n",
    "订阅刷新完成": "Subscriptions refreshed",
    "刷新订阅时出错: {error}": "Error refreshing subscriptions: {error}",
    "无法打开链接: {error}": "Cannot open link: {error}",
    "无法添加订阅: {message}": "Failed to add subscription: {message}",
    "添加订阅时出错: {error}": "Error adding subscription: {error}",
    "翻译失败": "Translation failed",
    "翻译时出错: {error}": "Translation error: {error}",
    "文章语言与系统语言({target})相同，无需翻译":
        "The article is already in your system language ({target}), no translation needed.",
    # 对话框
    "添加订阅": "Add Subscription",
    "RSS 地址:": "RSS URL:",
    "请输入 RSS 地址": "Please enter an RSS URL",
    "取消": "Cancel",
    "添加": "Add",
    "关于 RSSTransFeed": "About RSSTransFeed",
    "RSSTransFeed Desktop Application\n\n一个原生风格的 macOS RSS 阅读器\n使用 Python 和 Tkinter 构建":
        "RSSTransFeed Desktop Application\n\nA native-style macOS RSS reader\nBuilt with Python and Tkinter",
}


def detect_ui_language() -> str:
    """根据操作系统语言返回界面语言代码:zh 或 en。"""
    os_lang = TranslationService.get_os_language() or ""
    return "zh" if os_lang.lower().startswith("zh") else "en"


_UI_LANG = detect_ui_language()


def t(text: str) -> str:
    """返回当前系统语言对应的界面文案;无翻译时原样返回。"""
    if _UI_LANG == "zh":
        return text
    return _TRANSLATIONS.get(text, text)

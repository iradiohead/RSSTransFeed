"""Small Chinese/English UI translation table."""

from services import TranslationService

_EN = {
    "订阅": "Subscriptions",
    "全部文章": "All Articles",
    "添加": "Add",
    "删除订阅": "Remove Subscription",
    "正在加载文章…": "Loading articles…",
    "加载失败或暂无文章": "Failed to load or no articles",
    "[已读] ": "[Read] ",
    "[图片加载失败]": "[Image failed to load]",
    "翻译": "Translate",
    "翻译中…": "Translating…",
    "已翻译": "Translated",
    "翻译设置": "Translation Settings",
    "百度翻译 APP ID": "Baidu Translate APP ID",
    "百度翻译密钥": "Baidu Translate Secret Key",
    "保存": "Save",
    "百度翻译设置已保存": "Baidu Translate settings saved",
    "密钥保存在当前 Windows 用户设置中。": (
        "Credentials are stored in the current Windows user settings."
    ),
    "刷新": "Refresh",
    "刷新完成": "Refresh completed",
    "浏览器打开": "Open in Browser",
    "关于": "About",
    "取消": "Cancel",
    "RSS 地址": "RSS URL",
    "添加订阅": "Add Subscription",
    "请输入有效的 RSS 地址。": "Please enter a valid RSS URL.",
    "错误": "Error",
    "确认删除": "Confirm Removal",
    "确定删除“{title}”吗？": 'Remove "{title}"?',
}

_IS_CHINESE = TranslationService.short_code(TranslationService.os_language()) == "zh"


def t(text: str) -> str:
    """Return Chinese on Chinese systems and the English fallback otherwise."""
    return text if _IS_CHINESE else _EN.get(text, text)

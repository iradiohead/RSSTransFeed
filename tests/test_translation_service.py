import unittest
from unittest.mock import patch

from services.translation_service import TranslationService


class TranslationServiceTest(unittest.TestCase):
    def test_short_code(self):
        self.assertEqual(TranslationService._short_code('zh-CN'), 'zh')
        self.assertEqual(TranslationService._short_code('en_US'), 'en')
        self.assertEqual(TranslationService._short_code('ja'), 'ja')
        self.assertEqual(TranslationService._short_code(''), '')

    def test_get_os_language_maps_locale_format(self):
        with patch('services.translation_service.locale.getdefaultlocale', return_value=('zh_CN', 'UTF-8')):
            self.assertEqual(TranslationService.get_os_language(), 'zh-CN')

    def test_get_os_language_falls_back_to_env(self):
        with patch('services.translation_service.locale.getdefaultlocale', return_value=(None, None)):
            with patch.dict('os.environ', {'LANG': 'en_US.UTF-8'}):
                self.assertEqual(TranslationService.get_os_language(), 'en-US')

    def test_translate_article_skips_when_same_language(self):
        with patch('services.translation_service.locale.getdefaultlocale', return_value=('zh_CN', 'UTF-8')):
            with patch('langdetect.detect', return_value='zh-cn'):
                result = TranslationService.translate_article('中文标题', '中文正文内容')
        self.assertIsNone(result)

    def test_translate_article_chunks_long_content(self):
        with patch('services.translation_service.locale.getdefaultlocale', return_value=('zh_CN', 'UTF-8')):
            with patch('langdetect.detect', return_value='en'):
                long_text = 'hello world ' * 600  # 约 7200 字符,超过 4500 的分块阈值
                calls = []

                class FakeTranslator:
                    def __init__(self, source=None, target=None):
                        self.target = target

                    def translate(self, text):
                        calls.append((len(text), self.target))
                        return f"[{self.target}]" + text[:10]

                with patch('deep_translator.GoogleTranslator', FakeTranslator):
                    title, content = TranslationService.translate_article('Test Title', long_text, 'zh-CN')

        self.assertGreater(len(calls), 1, "长文本应分块翻译")
        self.assertLessEqual(max(c[0] for c in calls), 4500)
        self.assertTrue(all(c[1] == 'zh-CN' for c in calls))
        self.assertIn('[zh-CN]', title)
        self.assertIn('[zh-CN]', content)


if __name__ == '__main__':
    unittest.main()

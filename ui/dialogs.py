"""Application dialogs."""

from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
)

from services.baidu_translation_service import BAIDU_APP_ID_KEY, BAIDU_SECRET_KEY
from ui.i18n import t


class AddSubscriptionDialog(QDialog):
    """Modal dialog that validates and returns one RSS URL."""

    def __init__(self, parent=None):
        """Build the URL field and localized confirmation buttons."""
        super().__init__(parent)
        self.setWindowTitle(t("添加订阅"))
        self.setMinimumWidth(460)
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("https://example.com/feed.xml")
        self.url_edit.setClearButtonEnabled(True)

        form = QFormLayout()
        form.addRow(t("RSS 地址"), self.url_edit)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(t("添加"))
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(t("取消"))
        buttons.accepted.connect(self._accept_if_valid)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)
        self.url_edit.returnPressed.connect(self._accept_if_valid)
        self.url_edit.setFocus(Qt.FocusReason.OtherFocusReason)

    @property
    def url(self) -> str:
        """Return the normalized URL currently entered by the user."""
        return self.url_edit.text().strip()

    def _accept_if_valid(self) -> None:
        """Accept only HTTP(S) URLs and keep the dialog open on invalid input."""
        if not self.url.startswith(("http://", "https://")):
            QMessageBox.warning(self, t("错误"), t("请输入有效的 RSS 地址。"))
            return
        self.accept()


class TranslationSettingsDialog(QDialog):
    """Edit Baidu Translate credentials stored for the current Windows user."""

    def __init__(self, settings: QSettings, parent=None):
        """Build credential fields populated from the application settings."""
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle(t("翻译设置"))
        self.setMinimumWidth(500)

        self.app_id_edit = QLineEdit(
            str(settings.value(BAIDU_APP_ID_KEY, "") or "")
        )
        self.secret_edit = QLineEdit(
            str(settings.value(BAIDU_SECRET_KEY, "") or "")
        )
        self.secret_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.secret_edit.setClearButtonEnabled(True)

        form = QFormLayout()
        form.addRow(t("百度翻译 APP ID"), self.app_id_edit)
        form.addRow(t("百度翻译密钥"), self.secret_edit)

        note = QLabel(t("密钥保存在当前 Windows 用户设置中。"))
        note.setWordWrap(True)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText(t("保存"))
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(t("取消"))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(note)
        layout.addWidget(buttons)

    def accept(self) -> None:
        """Persist trimmed credentials and close the settings dialog."""
        self.settings.setValue(BAIDU_APP_ID_KEY, self.app_id_edit.text().strip())
        self.settings.setValue(
            BAIDU_SECRET_KEY,
            self.secret_edit.text().strip(),
        )
        self.settings.sync()
        super().accept()


def show_about(parent=None) -> None:
    """Display application identity and its main capabilities."""
    QMessageBox.about(
        parent,
        "RSSTransFeed",
        "<h3>RSSTransFeed</h3>"
        "<p>PySide6 RSS reader with full-text extraction and translation.</p>"
        "<p>RSS 阅读、全文提取、图文混排与自动翻译。</p>",
    )

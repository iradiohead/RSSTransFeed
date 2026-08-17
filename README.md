# RSSTransFeed2

使用 PySide6 重写的桌面 RSS 阅读器。界面与网络任务完全分离，耗时操作由
`QThreadPool` 执行，不会阻塞 Qt 主线程。

## 功能

- 添加、删除和刷新 RSS 订阅
- 查看单个订阅或聚合全部文章
- 已读状态持久化（自动清理 90 天前记录）
- 后台提取网页全文并过滤广告、导航、评论等噪音
- 正文图片异步下载和图文混排
- 百度在线翻译优先，失败时自动回退本地 Argos Translate
- 可拖动的订阅/文章/正文分栏，自动记忆布局
- 首次运行自动迁移同级 `RSSTransFeed` 的订阅和已读数据

## 安装与运行

Windows PowerShell：

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

macOS Terminal：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

应用数据保存在操作系统的用户数据目录，不再写入源码目录：

- Windows：`%APPDATA%\RSSTransFeed`
- macOS：`~/Library/Application Support/RSSTransFeed`

在“翻译设置”中配置百度翻译 APP ID 和密钥后，应用会优先使用百度翻译；
请求失败或未配置时自动回退到本地 Argos。百度密钥保存在当前操作系统用户的
Qt 设置中，不会写入源码或发布包。首次使用本地翻译的语言组合时会自动下载
Argos 模型。

## 构建 Windows 发布包

在 Windows PowerShell 中运行：

```powershell
.\build-release.ps1
```

脚本会创建独立构建环境、运行测试，并生成：

```text
dist\RSSTransFeed-windows-x64.zip
```

将此 ZIP 发给用户即可。用户解压整个 `RSSTransFeed` 文件夹后，双击
`RSSTransFeed.exe` 运行，无需安装 Python。请勿只复制 EXE；同目录下的
`_internal` 文件夹包含 Qt 和离线翻译所需组件。

构建包面向与构建机器相同的 Windows CPU 架构。首次使用某个语言组合进行
翻译时仍需联网下载 Argos 模型；模型下载完成后可离线翻译。

## 构建 macOS 发布包

macOS 应用必须在 Mac 上构建，Windows 不能交叉生成 `.app`。建议使用
Python 3.12 或 3.13，在 Terminal 中运行：

```bash
bash build-release-macos.sh
```

脚本会运行测试、构建并临时签名应用，最终生成：

```text
dist/RSSTransFeed-macos-arm64.zip
```

Intel Mac 上文件名为 `RSSTransFeed-macos-x86_64.zip`。构建结果仅对应构建
机器的 CPU 架构。未经过 Apple Developer ID 公证的应用首次打开时，可能需要
在 Finder 中右键选择“打开”；公开分发建议使用正式证书签名并完成 notarization。

## 结构

- `main.py`：应用入口
- `models.py`：订阅和文章模型
- `services/storage_service.py`：JSON 数据持久化
- `services/read_state.py`：文章已读状态
- `services/feed_service.py`：RSS、文章网页和图片网络访问
- `services/baidu_translation_service.py`：百度翻译与本地回退
- `services/subscription_manager.py`：订阅生命周期与文章缓存
- `services/translation_service.py`：语言检测与本地翻译
- `utils/article_extractor.py`：HTML 清理和正文提取
- `ui/main_window.py`：主窗口交互控制
- `ui/article_browser.py`：正文、译文和图片渲染
- `ui/workers.py`：Qt 后台任务封装
- `ui/dialogs.py`：对话框
- `ui/theme.py`：深色主题
- `docs/diagrams/`：自动生成的模块依赖图
- `build-release.ps1` / `build-release-macos.sh`：Windows/macOS 发布脚本

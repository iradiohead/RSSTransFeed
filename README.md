# RSSTransFeed2

使用 PySide6 重写的桌面 RSS 阅读器。界面与网络任务完全分离，耗时操作由
`QThreadPool` 执行，不会阻塞 Qt 主线程。

## 功能

- 添加、删除和刷新 RSS 订阅
- 查看单个订阅或聚合全部文章
- 已读状态持久化（自动清理 90 天前记录）
- 后台提取网页全文并过滤广告、导航、评论等噪音
- 正文图片异步下载和图文混排
- 使用本地 Argos Translate 模型翻译到操作系统语言（不调用 Google）
- 可拖动的订阅/文章/正文分栏，自动记忆布局
- 首次运行自动迁移同级 `RSSTransFeed` 的订阅和已读数据

## 安装与运行

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

应用数据保存在 `%APPDATA%\RSSTransFeed`，不再写入源码目录。
在“翻译设置”中配置百度翻译 APP ID 和密钥后，应用会优先使用百度翻译；
请求失败或未配置时自动回退到本地 Argos。百度密钥保存在当前 Windows 用户的
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

## 结构

- `main.py`：应用入口
- `models.py`：订阅和文章模型
- `services/storage_service.py`：JSON 数据持久化
- `services/read_state.py`：文章已读状态
- `services/feed_service.py`：RSS、文章网页和图片网络访问
- `services/subscription_manager.py`：订阅生命周期与文章缓存
- `services/translation_service.py`：语言检测与本地翻译
- `utils/article_extractor.py`：HTML 清理和正文提取
- `ui/main_window.py`：主窗口交互控制
- `ui/article_browser.py`：正文、译文和图片渲染
- `ui/workers.py`：Qt 后台任务封装
- `ui/dialogs.py`：对话框
- `ui/theme.py`：深色主题
- `docs/diagrams/`：自动生成的模块依赖图

# RSSTransFeed - 模块化架构

一个原生风格的 macOS RSS 阅读器，使用 Python 和 Tkinter 构建。

## 项目结构

```
TEST/
├── main.py                           # 应用入口点
├── models/                           # 数据模型
│   ├── __init__.py
│   └── subscription.py              # Subscription 和 Article 类
├── services/                         # 业务逻辑和服务层
│   ├── __init__.py
│   ├── feed_service.py              # RSS Feed 获取和解析
│   ├── storage_service.py           # 数据持久化（JSON）
│   └── subscription_manager.py      # 订阅管理逻辑
├── ui/                              # UI 组件
│   ├── __init__.py
│   ├── app.py                       # 主应用类 (RSSReaderApp)
│   ├── styles.py                    # 主题和样式配置
│   └── dialogs.py                   # 对话框组件
├── utils/                           # 工具函数
│   ├── __init__.py
│   ├── html_utils.py               # HTML 处理
│   └── date_utils.py               # 时间格式化
├── requirements.txt                 # 项目依赖
├── subscriptions.json              # 订阅数据文件
└── README.md                        # 本文件
```

## 模块说明

### Models (`models/`)
- **Subscription**: 代表一个 RSS 订阅，包含 ID、URL、标题、最后更新时间
- **Article**: 代表一篇 RSS 文章，包含标题、链接、内容、发布时间等

### Services (`services/`)
- **StorageService**: 处理订阅数据的读写（JSON 文件）
- **FeedService**: 获取和解析 RSS Feed，验证 Feed 有效性
- **SubscriptionManager**: 管理订阅生命周期，处理文章缓存和刷新

### UI (`ui/`)
- **app.py (RSSReaderApp)**: 主应用程序，包含 UI 逻辑和事件处理
  - 左侧边栏：订阅列表
  - 右侧上部：文章列表（可拖拽调整高度）
  - 右侧下部：文章内容显示 + 底部打开浏览器按钮
- **styles.py**: 统一的深色主题配置
- **dialogs.py**: 添加订阅和关于对话框

### Utils (`utils/`)
- **html_utils.py**: 从 HTML 中提取纯文本
- **date_utils.py**: 处理多种日期格式的解析和格式化

## 快速开始

### 安装依赖
```bash
pip install -r requirements.txt
```

### 运行应用
```bash
python main.py
```

## 主要功能

- ✅ 添加/删除 RSS 订阅
- ✅ 查看全部文章或按源过滤
- ✅ 标记文章为已读/未读
- ✅ 在默认浏览器中打开文章原文
- ✅ 刷新订阅（获取最新文章）
- ✅ 可拖拽调整文章列表和内容区域高度
- ✅ 深色主题 UI

## 技术栈

- **GUI**: Tkinter
- **RSS 解析**: feedparser
- **HTML 处理**: BeautifulSoup4
- **网络**: requests
- **数据存储**: JSON 文件

## 架构优势

这个模块化设计提供了以下好处：

1. **职责分离**: 每个模块专注一个特定功能
2. **易于维护**: 代码组织清晰，易于定位和修改
3. **易于测试**: 服务层可独立测试，不依赖 UI
4. **易于扩展**: 添加新功能只需在相应模块中扩展
5. **代码复用**: 服务层和 UI 层分离，方便代码复用

## 开发建议

- 新增业务逻辑放在 `services/` 目录
- 新增数据模型放在 `models/` 目录
- 新增工具函数放在 `utils/` 目录
- UI 组件修改在 `ui/` 目录（仅涉及展示逻辑，不涉及业务逻辑）

## 技术栈

- Python 3.x
- Tkinter GUI 库
- feedparser
- beautifulsoup4
- requests

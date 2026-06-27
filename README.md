# 学院AI辅导员系统（最终打包版）

面向交付部署的最终打包版本，包含完整的 AI 辅导员系统、知识管理工具、成本测算报告和使用教程。

## 项目简介

本项目是 AI 辅导员系统的最终交付版本，整合了跨平台兼容性、知识导入管理、公告自动抓取等全部功能，并附带了成本测算报告和详细使用教程，可直接用于生产环境部署。

## 功能特性

- **微信公众号智能客服** - 学生通过公众号对话获取学校信息
- **RAG知识库** - 支持PDF/Word文档解析、向量存储、语义检索
- **意图识别** - 自动识别6种问题类型（奖助学金/宿舍/消三比/转人工/问候/其他）
- **AI智能回答** - 基于知识库生成准确回答，支持API不可达时的Fallback机制
- **转人工服务** - 复杂问题自动推送对应老师联系方式
- **知识库管理** - 支持URL/文件/批量/公告等多种导入方式
- **公告自动抓取** - 定时从学校官网抓取最新公告更新知识库
- **跨平台部署** - 支持 Windows、macOS、Linux 一键安装启动
- **成本测算** - 附带真实运营成本测算报告
- **使用教程** - 附带详细的操作教程文档

## 技术栈

| 组件 | 技术 |
|------|------|
| 后端框架 | Python 3.8+ / FastAPI |
| 向量数据库 | Chroma |
| 嵌入模型 | sentence-transformers |
| 大语言模型 | xAI Grok API (Grok-2) |
| 微信接入 | 微信公众号 API |
| 网页抓取 | beautifulsoup4 / requests |
| 文档解析 | pypdf / python-docx |
| 内网穿透 | ngrok（开发测试用） |

## 项目结构

```
ai-tutor-final-package/
├── app/                             # 核心应用代码
│   ├── ai/                          # AI模块（Grok客户端、回复生成器）
│   ├── intent/                      # 意图识别模块
│   ├── rag/                         # RAG模块（知识库、文档解析）
│   ├── wechat/                      # 微信公众号处理模块
│   ├── platform.py                  # 跨平台兼容性工具
│   ├── config.py                    # 配置加载
│   └── main.py                      # FastAPI主应用
├── config.yaml                      # 系统配置文件
├── requirements.txt                 # Python依赖
├── start.sh                         # macOS/Linux启动脚本
├── start.bat                        # Windows启动脚本
├── install_dependencies.py          # 跨平台一键安装脚本
├── import_manager.py                # 命令行知识导入工具
├── import_api.py                    # 知识导入HTTP API服务
├── school_news_fetcher.py           # 学校公告自动抓取工具
├── manage_knowledge.py              # 知识库管理工具
├── 成本测算报告.md                    # 运营成本测算文档
├── 教程.md                          # 使用教程
├── 学院嵌入公众号AI辅导员系统.pptx      # 项目介绍PPT
└── knowledge/                       # 知识库文档目录
```

## 使用方法

### 1. 安装（三选一对应你的系统）

**Windows**: 双击运行 `install_dependencies.py`

**macOS**:
```bash
python3 install_dependencies.py
```

**Linux**:
```bash
python3 install_dependencies.py
```

### 2. 配置

编辑 `config.yaml`：

```yaml
xai:
  api_key: "your-xai-api-key"
  model: "grok-2"

wechat:
  app_id: "your-wechat-appid"
  app_secret: "your-wechat-appsecret"
  token: "your-wechat-token"
  encoding_aes_key: "your-wechat-aes-key"

teacher:
  contacts:
    - name: "张老师"
      phone: "010-12345678"
      department: "学生工作办公室"
      specialty: "奖助学金,助学贷款"
```

### 3. 启动

| 系统 | 启动方式 |
|------|----------|
| Windows | 双击 `start.bat` |
| macOS/Linux | 终端运行 `./start.sh` |

服务地址: http://localhost:8000

### 4. 知识库初始化

```bash
# 导入学校文档
python import_manager.py file 学生手册.pdf

# 从学校官网抓取公告
python school_news_fetcher.py

# 查看知识库状态
python manage_knowledge.py status
```

### 5. 微信公众号对接

1. 启动 ngrok: `ngrok http 8000`
2. 登录微信公众平台，配置服务器URL为 ngrok 地址
3. 配置Token与 config.yaml 中一致

## 附带文档

- **成本测算报告.md** - 基于2万学生规模的真实运营成本分析
- **教程.md** - 详细的安装、配置、使用教程

## License

MIT

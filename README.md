# 学院嵌入公众号AI辅导员系统

在微信公众号嵌入智能客服板块，学生通过对话获取学校文件和办事流程，AI解答基础问题，复杂问题转接老师。

---

## 🌟 功能特性

- **微信公众号接入** - 接收学生消息，回复AI结果
- **RAG知识库** - 学校文件PDF/Word解析，向量存储，支持检索
- **意图识别** - 判断学生问题类型（奖助学金/宿舍/消三比/其他）
- **AI解答** - 简单问题基于知识库直接回答（xAI API + Fallback）
- **转人工** - 复杂问题推送老师联系方式（姓名+电话+工单）
- **知识库管理** - 增删学校文件和办事流程文档
- **自动抓取** - 定时从学校官网抓取最新公告
- **统一导入** - 支持URL/文件/RSS/JSON等多种方式导入知识
- **跨平台** - 支持Windows、macOS、Linux

---

## 📦 Windows安装

### 方法1：一键安装（推荐）

1. 下载并解压本文件夹
2. 双击运行 `install_dependencies.py`
3. 等待依赖安装完成

### 方法2：手动安装

1. 确保已安装 Python 3.8+
   - 下载: https://www.python.org/downloads/windows/
   
2. 安装依赖
   ```
   pip install -r requirements.txt
   ```

3. 启动
   ```
   双击 start.bat
   ```

---

## 🍎 macOS安装

### 方法1：一键安装（推荐）

1. 下载并解压本文件夹
2. 终端运行：
   ```bash
   cd ai-tutor-final-package
   python3 install_dependencies.py
   ```

### 方法2：手动安装

1. 确保已安装 Python 3.8+
   ```bash
   # 使用Homebrew安装
   brew install python@3.11
   ```

2. 安装依赖
   ```bash
   pip3 install -r requirements.txt
   ```

3. 启动
   ```bash
   chmod +x start.sh
   ./start.sh
   ```

---

## 🐧 Linux安装

### 方法1：一键安装（推荐）

1. 下载并解压本文件夹
2. 终端运行：
   ```bash
   cd ai-tutor-final-package
   python3 install_dependencies.py
   ```

### 方法2：手动安装

1. 确保已安装 Python 3.8+
   ```bash
   sudo apt-get install python3 python3-pip
   ```

2. 安装依赖
   ```bash
   pip3 install -r requirements.txt
   ```

3. 启动
   ```bash
   chmod +x start.sh
   ./start.sh
   ```

---

## ⚙️ 配置

编辑 `config.yaml`：

```yaml
xai:
  api_key: "your-xai-api-key"

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

---

## 🚀 启动

| 系统 | 启动方式 |
|------|----------|
| Windows | 双击 `start.bat` 或 `python start.bat` |
| macOS/Linux | 终端运行 `./start.sh` |

服务地址: http://localhost:8000

---

## 🛠️ 管理工具

### import_manager.py - 命令行知识导入

```bash
# 查看状态
python import_manager.py status

# 从URL导入
python import_manager.py url "https://学校.edu/公告"

# 导入文件
python import_manager.py file 文档.pdf

# 批量导入
python import_manager.py batch ./知识文件夹/

# 导入公告
python import_manager.py announce 公告.json

# 更新老师信息
python import_manager.py teacher teachers.json

# 配置数据源
python import_manager.py source --add --name "学工办" --url "https://学校.edu/news" --category scholarship

# 抓取所有数据源
python import_manager.py source --fetch
```

### import_api.py - HTTP API服务（端口8001）

```bash
# 启动API服务
python import_api.py

# 导入网页
curl "http://localhost:8001/api/import/url?url=https://学校.edu/news&category=scholarship"

# 上传文件
curl -X POST -F "file=@文档.pdf" http://localhost:8001/api/import/file

# 更新老师
curl -X POST -H "Content-Type: application/json" \
  -d '{"teachers":[{"name":"张老师","phone":"010-123","specialty":"奖学金"}]}' \
  http://localhost:8001/api/teachers
```

### manage_knowledge.py - 知识库管理

```bash
# 查看状态
python manage_knowledge.py status

# 列出所有知识
python manage_knowledge.py list

# 添加知识
python manage_knowledge.py add-scholarship -c "新奖学金内容"

# 导出备份
python manage_knowledge.py export -f backup.json

# 交互式管理
python manage_knowledge.py interactive
```

### school_news_fetcher.py - 公告自动抓取

```bash
# 测试配置
python school_news_fetcher.py --test

# 抓取并更新
python school_news_fetcher.py

# 预览模式
python school_news_fetcher.py --dry-run
```

---

## 📁 项目结构

```
ai-tutor/
├── app/
│   ├── ai/
│   │   ├── grok_client.py          # xAI Grok API客户端
│   │   └── response_generator.py    # AI回复生成器（RAG+Fallback）
│   ├── intent/
│   │   └── recognizer.py           # 意图识别（6种意图）
│   ├── rag/
│   │   ├── knowledge_base.py        # Chroma向量知识库（跨平台）
│   │   └── document_parser.py       # PDF/Word文档解析
│   ├── wechat/
│   │   └── handler.py               # 微信公众号接入处理
│   ├── platform.py                 # 跨平台兼容性工具
│   ├── config.py
│   └── main.py                      # FastAPI主应用
├── config.yaml                      # 配置文件
├── requirements.txt                 # Python依赖
├── start.sh                         # macOS/Linux启动脚本
├── start.bat                        # Windows启动脚本
├── install_dependencies.py          # 跨平台安装脚本
├── import_manager.py                # 命令行知识导入工具
├── import_api.py                    # 知识导入HTTP API服务
├── school_news_fetcher.py           # 学校公告自动抓取工具
├── manage_knowledge.py              # 知识库管理工具
├── README.md
└── knowledge/                       # 知识库文档目录
    └── uploads/
```

---

## 📊 支持的意图

| 意图 | 关键词 | 说明 |
|------|--------|------|
| scholarship | 奖学金,助学金,助学贷款 | 奖助学金相关 |
| dormitory | 宿舍,住宿,调宿,退宿 | 宿舍相关 |
| three_ratio | 消三比,达标,预警 | 消三比相关 |
| transfer_human | 转人工,找老师 | 转人工服务 |
| greeting | 你好,您好,hi | 问候语 |
| other | 其他 | 其他事务 |

---

## 📋 公告文件格式

### JSON格式
```json
[
  {"title": "2024年奖学金申请通知", "content": "申请时间：9月...", "category": "scholarship"},
  {"title": "宿舍调整通知", "content": "因专业调整...", "category": "dormitory"}
]
```

### CSV格式
```csv
title,content,category
2024年奖学金申请通知,申请时间：9月...,scholarship
宿舍调整通知,因专业调整...,dormitory
```

### TXT格式（用|分隔）
```
2024年奖学金申请通知|申请时间：9月...|scholarship
宿舍调整通知|因专业调整...|dormitory
```

---

## ⚠️ 注意事项

1. **微信公众号配置**: 需要公网可访问的URL用于接收微信消息
2. **ngrok**: 开发测试需要内网穿透，正式部署可使用真实公网服务器
3. **xAI API Key**: 需要有效的xAI API密钥（当前网络不可达时使用Fallback）
4. **HuggingFace镜像**: 已配置 `HF_ENDPOINT=https://hf-mirror.com`

---

## 🔧 故障排除

### Python未找到
- Windows: 下载安装 https://www.python.org/downloads/
- macOS: `brew install python@3.11`
- Linux: `sudo apt-get install python3 python3-pip`

### 依赖安装失败
```bash
# 升级pip后重试
pip install --upgrade pip
pip install -r requirements.txt
```

### 模型加载失败
```bash
# 设置缓存路径后重试
export HF_ENDPOINT="https://hf-mirror.com"
python install_dependencies.py
```

### 端口被占用
修改 `config.yaml` 中的端口号，或运行：
```bash
# Windows查找占用
netstat -ano | findstr :8000

# macOS/Linux查找占用
lsof -i :8000
```

---

## 📞 技术栈

- Python 3.8+ / FastAPI
- Chroma 向量数据库
- sentence-transformers 嵌入模型
- xAI Grok API
- 微信公众号 API
- beautifulsoup4 / requests 网页抓取

---

## License

MIT

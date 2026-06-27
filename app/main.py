import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, HTTPException, UploadFile, File, Form
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import yaml

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.wechat.handler import WeChatValidator, WeChatMessageBuilder, WeChatAccessToken
from app.ai.response_generator import get_response_generator
from app.rag.knowledge_base import get_knowledge_base
from app.rag.document_parser import parse_document
from app.intent.recognizer import get_intent_recognizer

# Load config
CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

app = FastAPI(title="AI辅导员系统", description="微信公众号智能客服系统")

# Global response generator
_generator = None
_kb_initialized = False


def get_generator():
    global _generator
    if _generator is None:
        initialize_knowledge_base()  # Ensure KB is initialized
        _generator = get_response_generator()
    return _generator


def initialize_knowledge_base():
    """Initialize knowledge base with default data if empty"""
    global _kb_initialized
    if _kb_initialized:
        return
    
    kb = get_knowledge_base()
    if kb.get_collection_info()["count"] > 0:
        _kb_initialized = True
        return
    
    print("Initializing knowledge base with default data...")
    
    # Scholarship knowledge
    scholarship_docs = [
        {"content": """国家助学金\n申请条件：家庭经济困难、学习良好、无违纪\n奖励标准：3000-5000元/年\n申请流程：9月系统申请→准备材料→辅导员审核→学院公示3天→10月发放""", "metadata": {"category": "scholarship", "source": "学生手册"}},
        {"content": """国家奖学金\n申请条件：全日制本科生、成绩前10%、综合素质突出、无违纪\n奖励标准：8000元/年\n申请流程：9月提交申请→准备材料→学院评审→公示5天""", "metadata": {"category": "scholarship", "source": "学生手册"}},
        {"content": """国家励志奖学金\n申请条件：家庭困难、成绩前30%、品德优良\n奖励标准：5000元/年\n申请流程：9月系统申请→提交材料→辅导员初审→学院评审→公示发放""", "metadata": {"category": "scholarship", "source": "学生手册"}}
    ]
    kb.add_documents(scholarship_docs)
    
    # Dormitory knowledge
    dormitory_docs = [
        {"content": """调换宿舍\n申请条件：身体原因需调楼层/朝向、专业调整需换校区、与室友矛盾不可调和\n办理流程：系统提交申请→填表→辅导员签字→提交宿舍管理办→等待3-5工作日审批""", "metadata": {"category": "dormitory", "source": "宿舍管理规定"}},
        {"content": """退宿办理\n毕业退宿流程：领离宿清单→整理打扫→归还钥匙遥控器→管理员检查→如有损坏赔偿→办理押金退还\n注意：6月中旬开始，7个工作日内押金到账""", "metadata": {"category": "dormitory", "source": "宿舍管理规定"}},
        {"content": """住宿申请\n新生：录取通知书链接→规定时间网上申请→选宿舍区房型→缴费→报到入住\n老生：每学期末系统申请→5月申请6月分配→8月底查询结果""", "metadata": {"category": "dormitory", "source": "宿舍管理规定"}}
    ]
    kb.add_documents(dormitory_docs)
    
    # Three ratio knowledge
    three_ratio_docs = [
        {"content": """消三比达标标准\n学业进度比：达到80%以上（应修/已修学分比）\n综合素质比：每学期参加≥10次校院活动\n宿舍卫生比：检查平均分≥80分\n一票否决：作弊、不及格超3门、卫生不合格超5次""", "metadata": {"category": "three_ratio", "source": "学生手册"}},
        {"content": """消三比预警消除流程\n学业预警：登录教务系统查原因→补考或重修→通过后自动消除\n综合素质预警：参加校院活动→系统登记→累计10次后申请消除\n宿舍卫生预警：参加整改→连续3次检查合格→提交申请到辅导员""", "metadata": {"category": "three_ratio", "source": "学生手册"}}
    ]
    kb.add_documents(three_ratio_docs)
    
    # Teacher contacts
    teacher_docs = [
        {"content": """学生工作办公室\n张老师：13800138001，负责奖助学金、助学贷款、勤工俭学\n李老师：13800138002，负责宿舍调整、退宿、住宿申请\n王老师：13800138003，负责消三比、学籍证明、成绩单\n办公时间：周一至周五 8:30-11:30，14:00-17:00""", "metadata": {"category": "general", "source": "学校官网"}}
    ]
    kb.add_documents(teacher_docs)
    
    _kb_initialized = True
    print(f"Knowledge base initialized with {kb.get_collection_info()['count']} documents")


@app.get("/api/knowledge/init")
async def init_knowledge():
    """Manually initialize knowledge base"""
    initialize_knowledge_base()
    kb = get_knowledge_base()
    return {"status": "initialized", "stats": kb.get_collection_info()}


# ==================== WeChat Endpoint ====================

@app.get("/wechat")
async def wechat_verify(signature: str, timestamp: str, nonce: str, echostr: str):
    """WeChat server verification endpoint (GET)"""
    if WeChatValidator.validate_get(signature, timestamp, nonce, echostr):
        return PlainTextResponse(content=echostr)
    raise HTTPException(status_code=403, detail="Invalid signature")


@app.post("/wechat")
async def wechat_message(request: Request):
    """WeChat message handling endpoint (POST)"""
    try:
        body = await request.body()
        xml_string = body.decode("utf-8")
        
        message = WeChatValidator.parse_xml_message(xml_string)
        msg_type = message.get("MsgType", "")
        from_user = message.get("FromUserName", "")
        to_user = message.get("ToUserName", "")
        content = message.get("Content", "").strip()
        
        if msg_type == "text" and content:
            # Process message through AI
            generator = get_generator()
            response_text, intent = await generator.generate_response(content)
            
            # Build and return response
            response_xml = WeChatMessageBuilder.build_text_response(
                to_user, from_user, response_text
            )
            return PlainTextResponse(content=response_xml)
        
        elif msg_type == "event":
            # Handle event messages (subscribe, click, etc.)
            event = message.get("Event", "")
            if event == "subscribe":
                welcome = (
                    "👋 欢迎关注学院AI辅导员！\n\n"
                    "我是智能客服，可以帮你解答：\n"
                    "🎓 奖助学金申请\n"
                    "🏠 宿舍相关办理\n"
                    "✅ 消三比相关\n"
                    "📄 其他校园事务\n\n"
                    "请输入您想咨询的问题~"
                )
                response_xml = WeChatMessageBuilder.build_text_response(
                    to_user, from_user, welcome
                )
                return PlainTextResponse(content=response_xml)
        
        # Return empty for unsupported message types
        return ""
    
    except Exception as e:
        print(f"Error handling WeChat message: {e}")
        return ""


# ==================== Knowledge Base Management ====================

@app.get("/api/knowledge/stats")
async def get_knowledge_stats():
    """Get knowledge base statistics"""
    kb = get_knowledge_base()
    info = kb.get_collection_info()
    return info


@app.delete("/api/knowledge/documents/{doc_id}")
async def delete_document(doc_id: str):
    """Delete a document from knowledge base"""
    kb = get_knowledge_base()
    success = kb.delete_document(doc_id)
    if success:
        return {"status": "success", "message": f"Document {doc_id} deleted"}
    raise HTTPException(status_code=404, detail="Document not found")


@app.delete("/api/knowledge/all")
async def clear_knowledge_base():
    """Clear all documents from knowledge base"""
    kb = get_knowledge_base()
    success = kb.clear_all()
    if success:
        return {"status": "success", "message": "Knowledge base cleared"}
    raise HTTPException(status_code=500, detail="Failed to clear knowledge base")


# ==================== Document Upload & Processing ====================

@app.post("/api/knowledge/upload")
async def upload_document(file: UploadFile = File(...)):
    """Upload and process a document (PDF/Word/TXT)"""
    kb = get_knowledge_base()
    
    # Save uploaded file temporarily
    upload_dir = Path(__file__).parent.parent / "knowledge" / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = upload_dir / file.filename
    
    try:
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        # Parse document
        docs = parse_document(str(file_path))
        
        # Add to knowledge base
        doc_ids = kb.add_documents(docs)
        
        return {
            "status": "success",
            "file_name": file.filename,
            "chunks_added": len(docs),
            "doc_ids": doc_ids[:5]  # Return first 5 IDs
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process document: {str(e)}")
    
    finally:
        # Clean up temp file
        if file_path.exists():
            file_path.unlink()


@app.post("/api/knowledge/text")
async def add_text_content(
    content: str = Form(...),
    category: str = Form("general"),
    source: str = Form("manual")
):
    """Add text content directly to knowledge base"""
    kb = get_knowledge_base()
    
    doc = {
        "content": content,
        "metadata": {
            "type": "text",
            "category": category,
            "source": source
        }
    }
    
    doc_id = kb.add_document(content, doc["metadata"])
    
    return {
        "status": "success",
        "doc_id": doc_id
    }


# ==================== RAG Query Interface ====================

@app.get("/api/query")
async def query_knowledge(query: str, top_k: int = 5):
    """Query the knowledge base directly"""
    kb = get_knowledge_base()
    results = kb.search(query, top_k=top_k)
    return {"query": query, "results": results}


@app.post("/api/chat")
async def chat_message(message: dict):
    """Chat interface for testing"""
    generator = get_generator()
    query = message.get("query", "")
    
    if not query:
        raise HTTPException(status_code=400, detail="Query is required")
    
    response_text, intent = await generator.generate_response(query)
    
    return {
        "query": query,
        "response": response_text,
        "intent": intent
    }


# ==================== Intent Recognition ====================

@app.get("/api/intent/recognize")
async def recognize_intent(query: str):
    """Recognize intent of a query"""
    recognizer = get_intent_recognizer()
    intent = recognizer.recognize(query)
    teacher = recognizer.get_teacher_for_intent(intent)
    
    return {
        "query": query,
        "intent": intent.value,
        "intent_name": intent.name,
        "teacher": teacher
    }


# ==================== Teacher Contacts ====================

@app.get("/api/teachers")
async def get_teachers():
    """Get all teacher contacts"""
    teachers = config.get("teacher", {}).get("contacts", [])
    return {"teachers": teachers}


# ==================== Health Check ====================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "AI辅导员系统"}


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "AI辅导员系统",
        "version": "1.0.0",
        "endpoints": {
            "wechat": "/wechat (GET for verify, POST for messages)",
            "chat": "/api/chat",
            "query": "/api/query",
            "knowledge": "/api/knowledge",
            "intent": "/api/intent/recognize",
            "teachers": "/api/teachers"
        }
    }


if __name__ == "__main__":
    host = config["server"]["host"]
    port = config["server"]["port"]
    uvicorn.run(app, host=host, port=port)

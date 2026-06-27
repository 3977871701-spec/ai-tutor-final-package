#!/usr/bin/env python3
"""
知识导入HTTP API服务
提供RESTful接口，方便直接导入知识
"""

import os
import sys
import json
import asyncio
from pathlib import Path
from typing import Optional
from datetime import datetime

import uvicorn
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse

# Setup path
sys.path.insert(0, str(Path(__file__).parent))
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

# Import the manager
from import_manager import KnowledgeImporter

app = FastAPI(title="知识导入API", description="统一知识导入管理接口")

_importer: Optional[KnowledgeImporter] = None


def get_importer() -> KnowledgeImporter:
    global _importer
    if _importer is None:
        _importer = KnowledgeImporter()
    return _importer


# ============ URL/网站导入 ============

@app.get("/api/import/url")
async def import_url(url: str, category: str = None, title: str = None):
    """从URL导入知识"""
    importer = get_importer()
    result = importer.import_from_url(url, category, title)
    return JSONResponse(content=result)


@app.get("/api/import/rss")
async def import_rss(rss_url: str, category: str = None):
    """从RSS导入"""
    importer = get_importer()
    result = importer.import_from_rss(rss_url, category)
    return JSONResponse(content=result)


# ============ 文件导入 ============

@app.post("/api/import/file")
async def import_file(
    file: UploadFile = File(...),
    category: str = Form(None)
):
    """上传文件导入"""
    importer = get_importer()
    
    # 保存临时文件
    temp_dir = Path("data/temp")
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    temp_path = temp_dir / f"upload_{datetime.now().timestamp()}_{file.filename}"
    
    try:
        content = await file.read()
        temp_path.write_bytes(content)
        
        result = importer.import_file(str(temp_path), category)
        
    finally:
        # 清理临时文件
        if temp_path.exists():
            temp_path.unlink()
    
    return JSONResponse(content=result)


@app.post("/api/import/batch")
async def import_batch(
    files: list[UploadFile] = File(...),
    category: str = Form(None)
):
    """批量上传文件"""
    importer = get_importer()
    
    temp_dir = Path("data/temp")
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    imported = []
    failed = []
    
    for file in files:
        temp_path = temp_dir / f"upload_{datetime.now().timestamp()}_{file.filename}"
        
        try:
            content = await file.read()
            temp_path.write_bytes(content)
            
            result = importer.import_file(str(temp_path), category)
            
            if result["success"]:
                imported.append(file.filename)
            else:
                failed.append({"file": file.filename, "error": result.get("error")})
                
        except Exception as e:
            failed.append({"file": file.filename, "error": str(e)})
        
        finally:
            if temp_path.exists():
                temp_path.unlink()
    
    return JSONResponse(content={
        "success": len(failed) == 0,
        "imported": imported,
        "failed": failed,
        "total": len(files)
    })


# ============ 公告导入 ============

@app.post("/api/import/announcements")
async def import_announcements(
    file: UploadFile = File(...),
    format: str = Form("auto")
):
    """导入公告文件"""
    importer = get_importer()
    
    temp_dir = Path("data/temp")
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    temp_path = temp_dir / f"announce_{datetime.now().timestamp()}_{file.filename}"
    
    try:
        content = await file.read()
        temp_path.write_bytes(content)
        
        result = importer.import_announcements(str(temp_path), format)
        
    finally:
        if temp_path.exists():
            temp_path.unlink()
    
    return JSONResponse(content=result)


@app.post("/api/import/announcements/text")
async def import_announcements_text(
    announcements: str = Form(...),  # JSON string
    format: str = Form("json")
):
    """直接发送JSON文本导入公告"""
    importer = get_importer()
    
    temp_dir = Path("data/temp")
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    # 写入临时文件
    temp_path = temp_dir / f"announce_{datetime.now().timestamp()}.json"
    
    try:
        temp_path.write_text(announcements, encoding='utf-8')
        result = importer.import_announcements(str(temp_path), "json")
        
    finally:
        if temp_path.exists():
            temp_path.unlink()
    
    return JSONResponse(content=result)


# ============ 老师信息 ============

@app.post("/api/teachers")
async def update_teachers(teachers: list[dict]):
    """批量更新老师信息"""
    importer = get_importer()
    result = importer.update_teachers(teachers)
    return JSONResponse(content=result)


@app.get("/api/teachers")
async def get_teachers():
    """获取当前老师信息"""
    importer = get_importer()
    config = importer.config
    teachers = config.get('teacher', {}).get('contacts', [])
    return JSONResponse(content={"teachers": teachers})


@app.post("/api/teachers/file")
async def update_teachers_file(
    file: UploadFile = File(...),
    format: str = Form("auto")
):
    """从文件更新老师信息"""
    importer = get_importer()
    
    temp_dir = Path("data/temp")
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    temp_path = temp_dir / f"teacher_{datetime.now().timestamp()}_{file.filename}"
    
    try:
        content = await file.read()
        temp_path.write_bytes(content)
        
        result = importer.update_teachers_from_file(str(temp_path))
        
    finally:
        if temp_path.exists():
            temp_path.unlink()
    
    return JSONResponse(content=result)


# ============ 数据源管理 ============

@app.post("/api/sources")
async def add_source(
    name: str = Form(...),
    url: str = Form(...),
    source_type: str = Form("html"),
    selector: str = Form(None),
    category: str = Form(None)
):
    """添加数据源"""
    importer = get_importer()
    result = importer.add_data_source(name, url, source_type, selector, category)
    return JSONResponse(content=result)


@app.get("/api/sources")
async def get_sources():
    """获取数据源列表"""
    importer = get_importer()
    sources = importer.config.get('data_sources', [])
    return JSONResponse(content={"sources": sources})


@app.post("/api/sources/fetch")
async def fetch_sources():
    """从所有数据源抓取"""
    importer = get_importer()
    result = importer.fetch_from_data_sources()
    return JSONResponse(content=result)


@app.delete("/api/sources/{name}")
async def delete_source(name: str):
    """删除数据源"""
    importer = get_importer()
    
    sources = importer.config.get('data_sources', [])
    original_len = len(sources)
    sources = [s for s in sources if s.get('name') != name]
    
    if len(sources) == original_len:
        raise HTTPException(status_code=404, detail="数据源不存在")
    
    importer.config['data_sources'] = sources
    importer._save_config()
    
    return JSONResponse(content={"success": True, "message": f"已删除数据源: {name}"})


# ============ 知识库管理 ============

@app.get("/api/knowledge/status")
async def get_status():
    """获取知识库状态"""
    importer = get_importer()
    status = importer.status()
    return JSONResponse(content=status)


@app.post("/api/knowledge/clear")
async def clear_knowledge(category: str = None):
    """清空知识库"""
    importer = get_importer()
    kb = importer._get_kb()
    
    if category:
        docs = kb.search(category, top_k=100)
        for doc in docs:
            kb.delete_document(doc.get('id', ''))
        message = f"已清空类别: {category}"
    else:
        kb.clear_all()
        message = "已清空整个知识库"
    
    return JSONResponse(content={"success": True, "message": message})


@app.post("/api/knowledge/rebuild")
async def rebuild_knowledge():
    """重建默认知识库"""
    importer = get_importer()
    kb = importer._get_kb()
    kb.clear_all()
    
    # 重新初始化
    from app.main import initialize_knowledge_base
    initialize_knowledge_base()
    
    return JSONResponse(content={"success": True, "message": "知识库已重建"})


# ============ 主函数 ============

if __name__ == "__main__":
    port = 8001  # 使用不同端口，不与主服务冲突
    uvicorn.run(app, host="0.0.0.0", port=port)

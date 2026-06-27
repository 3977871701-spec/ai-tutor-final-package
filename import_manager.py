#!/usr/bin/env python3
"""
统一知识导入管理器
功能：
1. 从URL/网站自动抓取内容
2. 上传文件（PDF/Word/TXT）自动解析
3. 批量导入公告文件（JSON/CSV/TXT）
4. 更新老师联系方式
5. 管理数据源配置
"""

import os
import sys
import json
import re
import base64
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any

# Setup path
sys.path.insert(0, str(Path(__file__).parent))
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

import yaml
import requests
from bs4 import BeautifulSoup


# ============ 配置 ============

CONFIG_FILE = "config.yaml"
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)


# ============ 核心导入类 ============

class KnowledgeImporter:
    """统一知识导入器"""
    
    def __init__(self):
        self.kb = None
        self.config = self._load_config()
    
    def _load_config(self) -> dict:
        """加载配置"""
        config_path = Path(__file__).parent / CONFIG_FILE
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        return {}
    
    def _save_config(self):
        """保存配置"""
        config_path = Path(__file__).parent / CONFIG_FILE
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(self.config, f, f, allow_unicode=True, default_flow_style=False)
    
    def _get_kb(self):
        """获取知识库实例"""
        if self.kb is None:
            from app.rag.knowledge_base import get_knowledge_base
            self.kb = get_knowledge_base()
        return self.kb
    
    # ============ URL/网站抓取 ============
    
    def import_from_url(self, url: str, category: str = None, title: str = None) -> Dict:
        """
        从URL抓取内容并导入
        """
        result = {
            "success": False,
            "url": url,
            "title": None,
            "content": None,
            "category": category or "general",
            "error": None
        }
        
        try:
            # 抓取网页
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # 移除无关标签
            for tag in soup.find_all(['script', 'style', 'nav', 'footer', 'header']):
                tag.decompose()
            
            # 提取标题
            if not title:
                title_elem = soup.find('h1') or soup.find('title')
                title = title_elem.get_text(strip=True) if title_elem else url
            
            # 提取正文
            content_elem = soup.select_one('article, .article, .content, #content, main')
            if content_elem:
                content = content_elem.get_text(separator='\n', strip=True)
            else:
                # fallback: 获取所有段落
                paragraphs = [p.get_text(strip=True) for p in soup.find_all('p') if p.get_text(strip=True)]
                content = '\n'.join(paragraphs)
            
            # 自动分类
            if not category:
                category = self._auto_classify(title + content)
            
            # 精简内容（保留前2000字）
            content = content[:2000].rsplit('\n', 1)[0] if len(content) > 2000 else content
            
            # 导入知识库
            kb = self._get_kb()
            doc_content = f"{title}\n{content}"
            doc_id = kb.add_document(doc_content, {
                "category": category,
                "source": f"url:{url}",
                "type": "auto",
                "imported_at": datetime.now().isoformat()
            })
            
            result["success"] = True
            result["title"] = title
            result["content"] = content[:200] + "..." if len(content) > 200 else content
            result["doc_id"] = doc_id
            
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    def import_from_rss(self, rss_url: str, category: str = None) -> Dict:
        """
        从RSS订阅源导入
        """
        result = {
            "success": False,
            "url": rss_url,
            "items": [],
            "error": None
        }
        
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            resp = requests.get(rss_url, headers=headers, timeout=15)
            resp.raise_for_status()
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            items = soup.find_all('item') or soup.find_all('entry')
            
            kb = self._get_kb()
            count = 0
            
            for item in items[:20]:  # 最多20条
                title = item.find('title')
                link = item.find('link')
                desc = item.find('description') or item.find('summary')
                
                title_text = title.get_text(strip=True) if title else ""
                link_text = link.get_text(strip=True) if link else ""
                desc_text = desc.get_text(strip=True)[:500] if desc else ""
                
                if title_text:
                    item_cat = category or self._auto_classify(title_text)
                    content = f"{title_text}\n{desc_text}"
                    
                    kb.add_document(content, {
                        "category": item_cat,
                        "source": f"rss:{rss_url}",
                        "title": title_text,
                        "type": "rss",
                        "imported_at": datetime.now().isoformat()
                    })
                    count += 1
            
            result["success"] = True
            result["items"] = items[:20]
            result["count"] = count
            
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    # ============ 文件导入 ============
    
    def import_file(self, file_path: str, category: str = None) -> Dict:
        """
        导入本地文件（支持 PDF, Word, TXT）
        """
        result = {
            "success": False,
            "file": file_path,
            "type": None,
            "content": None,
            "error": None
        }
        
        path = Path(file_path)
        if not path.exists():
            result["error"] = f"文件不存在: {file_path}"
            return result
        
        suffix = path.suffix.lower()
        result["type"] = suffix
        
        try:
            content = ""
            
            if suffix == '.txt':
                content = path.read_text(encoding='utf-8')
            
            elif suffix == '.pdf':
                content = self._extract_pdf(path)
            
            elif suffix in ['.doc', '.docx']:
                content = self._extract_docx(path)
            
            elif suffix in ['.json', '.csv']:
                content = self._parse_structured_file(path)
            
            else:
                result["error"] = f"不支持的文件类型: {suffix}"
                return result
            
            # 自动分类
            if not category:
                category = self._auto_classify(content)
            
            # 导入
            kb = self._get_kb()
            doc_id = kb.add_document(content, {
                "category": category,
                "source": f"file:{path.name}",
                "type": "file",
                "imported_at": datetime.now().isoformat()
            })
            
            result["success"] = True
            result["content"] = content[:200] + "..." if len(content) > 200 else content
            result["doc_id"] = doc_id
            result["category"] = category
            
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    def import_files_batch(self, dir_path: str, pattern: str = "*.*", category: str = None) -> Dict:
        """
        批量导入目录下的文件
        """
        result = {
            "success": True,
            "dir": dir_path,
            "imported": [],
            "failed": []
        }
        
        path = Path(dir_path)
        if not path.is_dir():
            result["success"] = False
            result["error"] = "不是有效的目录"
            return result
        
        for file_path in path.glob(pattern):
            res = self.import_file(str(file_path), category)
            if res["success"]:
                result["imported"].append(file_path.name)
            else:
                result["failed"].append({"file": file_path.name, "error": res["error"]})
        
        return result
    
    # ============ 公告文件导入 ============
    
    def import_announcements(self, file_path: str, format: str = "auto") -> Dict:
        """
        批量导入公告文件
        支持格式：JSON, CSV, TXT(每行一条)
        """
        result = {
            "success": False,
            "file": file_path,
            "count": 0,
            "imported": [],
            "error": None
        }
        
        path = Path(file_path)
        if not path.exists():
            result["error"] = "文件不存在"
            return result
        
        try:
            if format == "auto":
                format = path.suffix.lower()
            
            items = []
            
            if format == '.json':
                items = self._parse_json_announcements(path)
            elif format == '.csv':
                items = self._parse_csv_announcements(path)
            elif format == '.txt':
                items = self._parse_txt_announcements(path)
            else:
                result["error"] = f"不支持的格式: {format}"
                return result
            
            kb = self._get_kb()
            
            for item in items:
                title = item.get('title', '')
                content = item.get('content', item.get('description', ''))
                category = item.get('category') or self._auto_classify(title + content)
                source = item.get('source', f"file:{path.name}")
                
                if title:
                    kb.add_document(f"{title}\n{content}", {
                        "category": category,
                        "source": source,
                        "type": "announcement",
                        "imported_at": datetime.now().isoformat()
                    })
                    result["imported"].append(title)
            
            result["success"] = True
            result["count"] = len(result["imported"])
            
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    # ============ 老师信息 ============
    
    def update_teachers(self, teachers: List[Dict]) -> Dict:
        """
        更新老师联系方式
        teachers: [{"name": "张老师", "phone": "010-123", "department": "学工办", "specialty": "奖学金"}]
        """
        result = {
            "success": False,
            "count": 0,
            "error": None
        }
        
        try:
            # 1. 更新 config.yaml
            self.config.setdefault('teacher', {})['contacts'] = teachers
            self._save_config()
            
            # 2. 更新知识库（清空旧数据，添加新数据）
            kb = self._get_kb()
            
            # 清空 general 类别
            docs = kb.search("general", top_k=100)
            for doc in docs:
                if '老师' in doc.get('content', '') or '联系方式' in doc.get('content', ''):
                    kb.delete_document(doc.get('id', ''))
            
            # 添加新老师信息
            lines = ["老师联系方式"]
            for t in teachers:
                line = f"{t['name']}：{t['phone']}，负责{t.get('specialty', '综合')}"
                if 'department' in t:
                    line += f"，{t['department']}"
                lines.append(line)
            
            content = '\n'.join(lines)
            kb.add_document(content, {
                "category": "general",
                "source": "config:teachers",
                "type": "teacher",
                "imported_at": datetime.now().isoformat()
            })
            
            result["success"] = True
            result["count"] = len(teachers)
            
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    def update_teachers_from_file(self, file_path: str) -> Dict:
        """从文件更新老师信息"""
        path = Path(file_path)
        
        if path.suffix == '.json':
            with open(path, 'r', encoding='utf-8') as f:
                teachers = json.load(f)
        elif path.suffix == '.csv':
            import csv
            teachers = []
            with open(path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    teachers.append(row)
        else:
            # 尝试解析文本格式
            teachers = self._parse_teacher_txt(path)
        
        return self.update_teachers(teachers)
    
    # ============ 数据源管理 ============
    
    def add_data_source(self, name: str, url: str, source_type: str = "html", 
                        selector: str = None, category: str = None) -> Dict:
        """
        添加数据源配置
        """
        result = {
            "success": False,
            "name": name,
            "error": None
        }
        
        try:
            self.config.setdefault('data_sources', [])
            
            # 检查是否已存在
            for src in self.config['data_sources']:
                if src.get('name') == name:
                    src['url'] = url
                    src['type'] = source_type
                    if selector:
                        src['selector'] = selector
                    if category:
                        src['category'] = category
                    break
            else:
                self.config['data_sources'].append({
                    'name': name,
                    'url': url,
                    'type': source_type,
                    'selector': selector or 'a',
                    'category': category
                })
            
            self._save_config()
            result["success"] = True
            
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    def fetch_from_data_sources(self) -> Dict:
        """从所有配置的数据源抓取"""
        result = {
            "success": True,
            "sources": [],
            "total_count": 0
        }
        
        sources = self.config.get('data_sources', [])
        
        for src in sources:
            try:
                if src.get('type') == 'rss':
                    res = self.import_from_rss(src['url'], src.get('category'))
                else:
                    res = self.import_from_url(src['url'], src.get('category'), src.get('title'))
                
                result["sources"].append({
                    "name": src['name'],
                    "result": res
                })
                
                if res.get('success'):
                    result["total_count"] += 1
                    
            except Exception as e:
                result["sources"].append({
                    "name": src['name'],
                    "error": str(e)
                })
        
        return result
    
    # ============ 工具方法 ============
    
    def _auto_classify(self, text: str) -> str:
        """自动分类"""
        text_lower = text.lower()
        
        keywords = {
            "scholarship": ["奖学金", "助学金", "助学贷款", "贫困生", "补贴", "资助", "奖励"],
            "dormitory": ["宿舍", "住宿", "床位", "调宿", "退宿", "寝室"],
            "three_ratio": ["消三比", "三比", "达标", "预警", "学分", "绩点"]
        }
        
        for cat, kws in keywords.items():
            if any(kw in text_lower for kw in kws):
                return cat
        
        return "general"
    
    def _extract_pdf(self, path: Path) -> str:
        """提取PDF文本"""
        try:
            import pypdf
            reader = pypdf.PdfReader(path)
            text = []
            for page in reader.pages[:10]:  # 最多10页
                text.append(page.extract_text())
            return '\n'.join(text)
        except:
            return f"[PDF文件: {path.name}]"
    
    def _extract_docx(self, path: Path) -> str:
        """提取Word文本"""
        try:
            from docx import Document
            doc = Document(path)
            return '\n'.join([p.text for p in doc.paragraphs])
        except:
            return f"[Word文件: {path.name}]"
    
    def _parse_structured_file(self, path: Path) -> str:
        """解析结构化文件"""
        if path.suffix == '.json':
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return json.dumps(data, ensure_ascii=False, indent=2)
        elif path.suffix == '.csv':
            import csv
            lines = []
            with open(path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                lines = [','.join(row) for row in reader]
            return '\n'.join(lines)
        return ""
    
    def _parse_json_announcements(self, path: Path) -> List[Dict]:
        """解析JSON公告"""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        return [data]
    
    def _parse_csv_announcements(self, path: Path) -> List[Dict]:
        """解析CSV公告"""
        import csv
        items = []
        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                items.append(row)
        return items
    
    def _parse_txt_announcements(self, path: Path) -> List[Dict]:
        """解析TXT公告（每行: 标题|内容|分类)"""
        items = []
        for line in path.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split('|')
            items.append({
                'title': parts[0] if len(parts) > 0 else '',
                'content': parts[1] if len(parts) > 1 else '',
                'category': parts[2] if len(parts) > 2 else None
            })
        return items
    
    def _parse_teacher_txt(self, path: Path) -> List[Dict]:
        """解析老师信息文本"""
        teachers = []
        for line in path.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            # 格式: 姓名|电话|部门|负责领域
            parts = line.split('|')
            if len(parts) >= 2:
                teachers.append({
                    'name': parts[0],
                    'phone': parts[1],
                    'department': parts[2] if len(parts) > 2 else '',
                    'specialty': parts[3] if len(parts) > 3 else ''
                })
        return teachers
    
    # ============ 状态查询 ============
    
    def status(self) -> Dict:
        """获取状态"""
        kb = self._get_kb()
        info = kb.get_collection_info()
        
        return {
            "knowledge_count": info['count'],
            "config_sources": len(self.config.get('data_sources', [])),
            "teachers": len(self.config.get('teacher', {}).get('contacts', []))
        }


# ============ CLI 接口 ============

def main():
    parser = argparse.ArgumentParser(description="统一知识导入管理器")
    subparsers = parser.add_subparsers(dest='command', help='子命令')
    
    # URL导入
    p_url = subparsers.add_parser('url', help='从URL导入')
    p_url.add_argument('url', help='网页URL')
    p_url.add_argument('--category', '-c', help='分类 (scholarship/dormitory/three_ratio/general)')
    p_url.add_argument('--title', '-t', help='指定标题')
    
    # RSS导入
    p_rss = subparsers.add_parser('rss', help='从RSS导入')
    p_rss.add_argument('rss_url', help='RSS订阅地址')
    p_rss.add_argument('--category', '-c', help='分类')
    
    # 文件导入
    p_file = subparsers.add_parser('file', help='导入文件')
    p_file.add_argument('file', help='文件路径')
    p_file.add_argument('--category', '-c', help='分类')
    
    # 批量文件导入
    p_batch = subparsers.add_parser('batch', help='批量导入文件')
    p_batch.add_argument('dir', help='目录路径')
    p_batch.add_argument('--pattern', '-p', default='*.*', help='文件匹配模式')
    p_batch.add_argument('--category', '-c', help='分类')
    
    # 公告导入
    p_ann = subparsers.add_parser('announce', help='导入公告文件')
    p_ann.add_argument('file', help='公告文件路径')
    p_ann.add_argument('--format', '-f', default='auto', help='文件格式 (json/csv/txt)')
    
    # 老师更新
    p_teacher = subparsers.add_parser('teacher', help='更新老师信息')
    p_teacher.add_argument('file', nargs='?', help='老师信息文件')
    p_teacher.add_argument('--name', '-n', help='老师姓名')
    p_teacher.add_argument('--phone', '-p', help='电话号码')
    p_teacher.add_argument('--dept', '-d', help='部门')
    p_teacher.add_argument('--specialty', '-s', help='负责领域')
    
    # 数据源管理
    p_source = subparsers.add_parser('source', help='管理数据源')
    p_source.add_argument('--add', help='添加数据源')
    p_source.add_argument('--name', help='数据源名称')
    p_source.add_argument('--url', help='数据源URL')
    p_source.add_argument('--type', default='html', choices=['html', 'rss'], help='类型')
    p_source.add_argument('--selector', help='CSS选择器')
    p_source.add_argument('--category', help='分类')
    p_source.add_argument('--fetch', action='store_true', help='立即抓取')
    
    # 状态
    subparsers.add_parser('status', help='查看状态')
    
    args = parser.parse_args()
    
    importer = KnowledgeImporter()
    result = {"success": False, "message": "未知命令"}
    
    if args.command == 'url':
        result = importer.import_from_url(args.url, args.category, args.title)
        result["message"] = f"URL导入{'成功' if result['success'] else '失败'}"
    
    elif args.command == 'rss':
        result = importer.import_from_rss(args.rss_url, args.category)
        result["message"] = f"RSS导入完成，获取 {result.get('count', 0)} 条"
    
    elif args.command == 'file':
        result = importer.import_file(args.file, args.category)
        result["message"] = f"文件导入{'成功' if result['success'] else '失败'}"
    
    elif args.command == 'batch':
        result = importer.import_files_batch(args.dir, args.pattern, args.category)
        result["message"] = f"批量导入完成，成功 {len(result.get('imported', []))} 个"
    
    elif args.command == 'announce':
        result = importer.import_announcements(args.file, args.format)
        result["message"] = f"公告导入完成，共 {result.get('count', 0)} 条"
    
    elif args.command == 'teacher':
        if args.file:
            result = importer.update_teachers_from_file(args.file)
        else:
            teachers = [{
                "name": args.name,
                "phone": args.phone,
                "department": args.dept,
                "specialty": args.specialty
            }]
            result = importer.update_teachers(teachers)
        result["message"] = f"老师信息更新{'成功' if result['success'] else '失败'}"
    
    elif args.command == 'source':
        if args.add == 'add' and args.name and args.url:
            result = importer.add_data_source(args.name, args.url, args.type, args.selector, args.category)
            result["message"] = f"数据源 {'添加' if result['success'] else '更新'}成功"
        if args.fetch:
            result = importer.fetch_from_data_sources()
            result["message"] = f"抓取完成，共 {result.get('total_count', 0)} 个数据源"
    
    elif args.command == 'status':
        result = importer.status()
        result["message"] = "状态查询"
    
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

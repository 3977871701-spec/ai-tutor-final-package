#!/usr/bin/env python3
"""
学校公告自动抓取与知识库更新工具
功能：
1. 自动抓取学校官网公告
2. 智能分类（奖学金/宿舍/消三比/其他）
3. 与现有知识比对，差异则覆盖更新
4. 定时任务自动执行
"""

import os
import sys
import re
import json
import time
import hashlib
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple

import requests
from bs4 import BeautifulSoup

# Setup
sys.path.insert(0, str(Path(__file__).parent))
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

from app.rag.knowledge_base import get_knowledge_base


# ============ 配置区 ============

# 学校公告RSS/API地址（示例）
SCHOOL_NEWS_SOURCES = [
    {
        "name": "学校官网公告",
        "url": "https://www.example.edu.cn/news/announcements",
        "type": "html",  # html / rss / api
        "selector": "div.news-list a",  # CSS选择器
    },
    {
        "name": "学生处公告",
        "url": "https://www.example.edu.cn/student/news",
        "type": "html",
        "selector": ".article-list a",
    },
    {
        "name": "教务处公告",
        "url": "https://www.example.edu.cn/academic/news",
        "type": "html", 
        "selector": ".notice-list a",
    },
    {
        "name": "研究生院公告",
        "url": "https://www.example.edu.cn/graduate/news",
        "type": "html",
        "selector": "table.news tr a",
    },
]

# 关键词分类规则
CLASSIFY_KEYWORDS = {
    "scholarship": [
        "奖学金", "助学金", "国家奖学金", "励志奖学金", "助学贷款", 
        "补贴", "贫困生", "评定", "奖励", "资助", "勤工俭学",
        "国家助学金", "各类奖助学金", "企业奖学金", "社会奖助学金"
    ],
    "dormitory": [
        "宿舍", "住宿", "床位", "调宿", "退宿", "寝室", "入住",
        "退寝", "宿舍调整", "宿舍申请", "宿舍分配", "毕业生离校"
    ],
    "three_ratio": [
        "消三比", "三比", "达标", "成绩达标", "学分", "绩点",
        "预警", "学业预警", "综合素质", "宿舍卫生", "体质测试"
    ],
    "general": []  # 其他归类为通用
}

# 缓存文件
CACHE_FILE = "data/news_cache.json"


# ============ 工具函数 ============

def load_cache() -> Dict:
    """加载缓存"""
    cache_path = Path(__file__).parent / CACHE_FILE
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    
    if cache_path.exists():
        with open(cache_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"fetched": {}, "last_update": None}


def save_cache(cache: Dict):
    """保存缓存"""
    cache_path = Path(__file__).parent / CACHE_FILE
    cache["last_update"] = datetime.now().isoformat()
    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def compute_hash(content: str) -> str:
    """计算内容哈希"""
    return hashlib.md5(content.encode('utf-8')).hexdigest()[:16]


def classify_intent(text: str) -> str:
    """根据内容分类"""
    text_lower = text.lower()
    
    scores = {}
    for category, keywords in CLASSIFY_KEYWORDS.items():
        if category == "general":
            continue
        score = sum(1 for kw in keywords if kw in text_lower)
        scores[category] = score
    
    if scores:
        best = max(scores, key=scores.get)
        if scores[best] > 0:
            return best
    
    return "general"


def extract_article_content(url: str) -> Optional[str]:
    """抓取文章完整内容"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml',
        }
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # 移除脚本和样式
        for tag in soup.find_all(['script', 'style', 'nav', 'footer', 'header']):
            tag.decompose()
        
        # 尝试多种选择器获取正文
        content = None
        selectors = ['article', '.article-content', '.content', '#content', '.news-content', 'main']
        for sel in selectors:
            elem = soup.select_one(sel)
            if elem:
                content = elem.get_text(separator='\n', strip=True)
                break
        
        if not content:
            # fallback: 获取所有段落
            paragraphs = soup.find_all('p')
            content = '\n'.join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
        
        return content[:5000] if content else None  # 限制长度
    
    except Exception as e:
        print(f"  ⚠️ 抓取失败 {url}: {e}")
        return None


def simplify_content(content: str, category: str) -> str:
    """精简内容为知识库格式（~150字）"""
    lines = content.split('\n')
    useful_lines = []
    
    for line in lines:
        line = line.strip()
        if len(line) > 10 and not line.startswith('#') and '版权' not in line:
            useful_lines.append(line)
    
    # 合并并截断
    full_text = ' '.join(useful_lines)
    if len(full_text) > 400:
        full_text = full_text[:400] + "..."
    
    return full_text


# ============ 抓取功能 ============

def fetch_announcements(source: Dict) -> List[Dict]:
    """抓取单个来源的公告"""
    results = []
    
    try:
        print(f"  📡 抓取: {source['name']}")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        }
        resp = requests.get(source['url'], headers=headers, timeout=15)
        resp.raise_for_status()
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        links = soup.select(source.get('selector', 'a'))
        
        for link in links[:20]:  # 最多20条
            title = link.get_text(strip=True)
            url = link.get('href', '')
            
            # 补全URL
            if url and not url.startswith('http'):
                if url.startswith('/'):
                    from urllib.parse import urljoin
                    url = urljoin(source['url'], url)
                else:
                    continue  # 跳过无效链接
            
            if len(title) < 5:
                continue
            
            results.append({
                'title': title,
                'url': url,
                'source': source['name'],
                'time': datetime.now().isoformat()
            })
        
        print(f"    ✅ 获取 {len(results)} 条")
        
    except Exception as e:
        print(f"    ❌ 失败: {e}")
    
    return results


def fetch_all_announcements() -> List[Dict]:
    """抓取所有来源的公告"""
    all_items = []
    
    for source in SCHOOL_NEWS_SOURCES:
        items = fetch_announcements(source)
        all_items.extend(items)
    
    return all_items


# ============ 知识库更新 ============

def get_existing_knowledge() -> Dict[str, List[Dict]]:
    """获取现有知识库内容"""
    kb = get_knowledge_base()
    existing = {}
    
    for category in ["scholarship", "dormitory", "three_ratio", "general"]:
        docs = kb.search(category, top_k=100)
        existing[category] = docs
    
    return existing


def update_knowledge_from_announcements(announcements: List[Dict], dry_run: bool = False) -> Tuple[int, int]:
    """
    从公告更新知识库
    返回: (新增数, 更新数)
    """
    kb = get_knowledge_base()
    cache = load_cache()
    
    new_count = 0
    update_count = 0
    
    for item in announcements:
        title = item['title']
        url = item.get('url', '')
        source = item.get('source', '')
        
        # 跳过已有缓存的（24小时内已处理）
        item_hash = compute_hash(title)
        if cache['fetched'].get(item_hash):
            continue
        
        # 抓取正文内容
        content = title  # 默认用标题
        if url:
            full_content = extract_article_content(url)
            if full_content:
                content = full_content
            else:
                content = title
        
        # 分类
        category = classify_intent(title + content)
        
        # 精简
        simplified = simplify_content(content, category)
        
        # 构建知识文档
        doc_content = f"{title}\n{simplified}"
        doc_meta = {
            "category": category,
            "source": source,
            "url": url,
            "fetched_at": datetime.now().isoformat(),
            "type": "auto"
        }
        
        if dry_run:
            print(f"  📝 [DRY-RUN] {category}: {title[:40]}...")
        else:
            # 添加到知识库
            kb.add_document(doc_content, doc_meta)
            new_count += 1
            
            # 更新缓存
            cache['fetched'][item_hash] = {
                'title': title,
                'category': category,
                'time': datetime.now().isoformat()
            }
            
            print(f"  ➕ 新增 {category}: {title[:40]}...")
    
    # 清理过期缓存（超过7天）
    if not dry_run:
        save_cache(cache)
    
    return new_count, update_count


def sync_with_school_data(dry_run: bool = False) -> Dict:
    """
    同步学校数据到知识库
    对比现有知识，有变化则覆盖
    """
    print("\n🔄 开始同步学校公告...")
    
    # 1. 抓取最新公告
    print("\n📥 抓取公告:")
    announcements = fetch_all_announcements()
    print(f"   共获取 {len(announcements)} 条公告")
    
    if not announcements:
        print("⚠️  没有获取到新公告")
        return {"fetched": 0, "added": 0, "updated": 0}
    
    # 2. 更新知识库
    print("\n📤 更新知识库:")
    added, updated = update_knowledge_from_announcements(announcements, dry_run)
    
    # 3. 统计
    kb = get_knowledge_base()
    stats = kb.get_collection_info()
    
    result = {
        "fetched": len(announcements),
        "added": added,
        "updated": updated,
        "total_docs": stats['count']
    }
    
    print(f"\n✅ 同步完成!")
    print(f"   抓取: {result['fetched']} 条")
    print(f"   新增: {result['added']} 条")
    print(f"   知识库总量: {result['total_docs']} 条")
    
    return result


# ============ 命令行接口 ============

def main():
    parser = argparse.ArgumentParser(description="学校公告抓取与知识库更新工具")
    parser.add_argument('--dry-run', '-n', action='store_true', help='仅预览不更新')
    parser.add_argument('--source', '-s', help='指定数据源名称')
    parser.add_argument('--url', '-u', help='抓取指定URL')
    parser.add_argument('--test', '-t', action='store_true', help='测试模式')
    
    args = parser.parse_args()
    
    print("=" * 50)
    print("🏫 学校公告自动抓取与知识库更新工具")
    print("=" * 50)
    
    if args.test:
        # 测试模式：打印配置
        print("\n📋 当前配置:")
        print(f"  数据源数量: {len(SCHOOL_NEWS_SOURCES)}")
        for src in SCHOOL_NEWS_SOURCES:
            print(f"    - {src['name']}: {src['url']}")
        print(f"\n📁 缓存文件: {CACHE_FILE}")
        
        cache = load_cache()
        print(f"  缓存记录数: {len(cache.get('fetched', {}))}")
        print(f"  最后更新: {cache.get('last_update', '从未')}")
        return
    
    if args.url:
        # 抓取指定URL
        print(f"\n📡 抓取指定URL: {args.url}")
        content = extract_article_content(args.url)
        if content:
            print(f"\n📄 内容预览 (前500字):")
            print(content[:500])
            print("\n...")
            
            category = classify_intent(content)
            print(f"\n🏷️  自动分类: {category}")
        else:
            print("❌ 抓取失败")
        return
    
    # 正常同步
    result = sync_with_school_data(dry_run=args.dry_run)
    
    print("\n" + "=" * 50)
    print(f"📊 执行结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
    print("=" * 50)


if __name__ == "__main__":
    main()

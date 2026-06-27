#!/usr/bin/env python3
"""
知识库管理工具
用于管理AI辅导员系统的知识库内容
"""

import os
import sys
import json
import argparse
from pathlib import Path

# 设置环境
sys.path.insert(0, str(Path(__file__).parent))
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

from app.rag.knowledge_base import get_knowledge_base
from app.intent.recognizer import Intent
import yaml


def init_kb():
    """初始化知识库"""
    kb = get_knowledge_base()
    return kb


def status():
    """查看知识库状态"""
    kb = init_kb()
    info = kb.get_collection_info()
    print(f"📊 知识库状态:")
    print(f"   集合名称: {info['name']}")
    print(f"   文档数量: {info['count']}")
    
    # 按category统计
    categories = ["scholarship", "dormitory", "three_ratio", "general"]
    for cat in categories:
        docs = kb.search(cat, top_k=100)
        print(f"   - {cat}: {len(docs)} 条")


def add_scholarship(content: str, source: str = "管理员"):
    """添加奖助学金知识"""
    kb = init_kb()
    doc = {
        "content": content,
        "metadata": {"category": "scholarship", "source": source}
    }
    doc_id = kb.add_document(content, doc["metadata"])
    print(f"✅ 添加奖助学金知识成功: {doc_id[:8]}...")
    return doc_id


def add_dormitory(content: str, source: str = "管理员"):
    """添加宿舍知识"""
    kb = init_kb()
    doc = {
        "content": content,
        "metadata": {"category": "dormitory", "source": source}
    }
    doc_id = kb.add_document(content, doc["metadata"])
    print(f"✅ 添加宿舍知识成功: {doc_id[:8]}...")
    return doc_id


def add_three_ratio(content: str, source: str = "管理员"):
    """添加消三比知识"""
    kb = init_kb()
    doc = {
        "content": content,
        "metadata": {"category": "three_ratio", "source": source}
    }
    doc_id = kb.add_document(content, doc["metadata"])
    print(f"✅ 添加消三比知识成功: {doc_id[:8]}...")
    return doc_id


def add_general(content: str, source: str = "管理员"):
    """添加通用知识"""
    kb = init_kb()
    doc = {
        "content": content,
        "metadata": {"category": "general", "source": source}
    }
    doc_id = kb.add_document(content, doc["metadata"])
    print(f"✅ 添加通用知识成功: {doc_id[:8]}...")
    return doc_id


def list_all():
    """列出所有知识"""
    kb = init_kb()
    categories = {
        "scholarship": "🎓 奖助学金",
        "dormitory": "🏠 宿舍",
        "three_ratio": "✅ 消三比",
        "general": "📄 通用"
    }
    
    for cat, name in categories.items():
        docs = kb.search(cat, top_k=100)
        print(f"\n{name} ({len(docs)}条):")
        for i, doc in enumerate(docs, 1):
            content = doc['content'][:60].replace('\n', ' ')
            print(f"  {i}. {content}...")


def clear_category(category: str):
    """清空指定category的知识"""
    kb = init_kb()
    
    # 搜索该category的所有文档
    docs = kb.search(category, top_k=100)
    
    if not docs:
        print(f"ℹ️  没有找到 {category} 类别的知识")
        return
    
    # 删除所有文档
    for doc in docs:
        kb.delete_document(doc.get('id', ''))
    
    print(f"✅ 已清空 {category} 类别 ({len(docs)}条)")


def reset_all():
    """重置整个知识库"""
    kb = init_kb()
    kb.clear_all()
    print("✅ 已清空整个知识库")
    
    # 重新初始化默认知识
    from app.main import initialize_knowledge_base
    initialize_knowledge_base()
    print("✅ 已重新初始化默认知识库")


def export_knowledge(output_file: str = "knowledge_backup.json"):
    """导出知识库到JSON文件"""
    kb = init_kb()
    
    categories = ["scholarship", "dormitory", "three_ratio", "general"]
    all_docs = []
    
    for cat in categories:
        docs = kb.search(cat, top_k=100)
        for doc in docs:
            all_docs.append({
                "category": doc['metadata'].get('category', cat),
                "content": doc['content'],
                "source": doc['metadata'].get('source', '')
            })
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_docs, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 导出完成: {output_file} ({len(all_docs)}条)")


def import_knowledge(input_file: str):
    """从JSON文件导入知识库"""
    with open(input_file, 'r', encoding='utf-8') as f:
        docs = json.load(f)
    
    kb = init_kb()
    count = 0
    
    for doc in docs:
        kb.add_document(
            doc['content'],
            {
                "category": doc.get('category', 'general'),
                "source": doc.get('source', '导入')
            }
        )
        count += 1
    
    print(f"✅ 导入完成: {count}条")


def update_teachers():
    """更新老师联系方式（从config.yaml）"""
    config_path = Path(__file__).parent / "config.yaml"
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    teachers = config.get('teacher', {}).get('contacts', [])
    
    if not teachers:
        print("⚠️  config.yaml 中未找到老师配置")
        return
    
    # 构建老师信息文本
    teacher_texts = []
    for t in teachers:
        text = f"{t['name']}：{t['phone']}，负责{t['specialty']}"
        teacher_texts.append(text)
    
    content = "老师联系方式\n" + "\n".join(teacher_texts)
    
    kb = init_kb()
    
    # 先清空general类别
    clear_category("general")
    
    # 添加新老师信息
    doc = {
        "content": content,
        "metadata": {"category": "general", "source": "config.yaml"}
    }
    kb.add_document(content, doc["metadata"])
    
    print(f"✅ 已更新老师联系方式 ({len(teachers)}位)")


def interactive():
    """交互式管理"""
    print("\n📚 AI辅导员知识库管理")
    print("=" * 40)
    print("1. 查看状态")
    print("2. 添加奖助学金知识")
    print("3. 添加宿舍知识")
    print("4. 添加消三比知识")
    print("5. 添加通用知识")
    print("6. 列出所有知识")
    print("7. 清空知识库")
    print("8. 重置为默认")
    print("9. 导出知识库")
    print("10. 导入知识库")
    print("11. 更新老师信息")
    print("0. 退出")
    print("=" * 40)
    
    while True:
        choice = input("\n请选择操作 [0-11]: ").strip()
        
        if choice == '1':
            status()
        elif choice == '2':
            content = input("请输入奖助学金内容: ").strip()
            if content:
                add_scholarship(content)
        elif choice == '3':
            content = input("请输入宿舍内容: ").strip()
            if content:
                add_dormitory(content)
        elif choice == '4':
            content = input("请输入消三比内容: ").strip()
            if content:
                add_three_ratio(content)
        elif choice == '5':
            content = input("请输入通用内容: ").strip()
            if content:
                add_general(content)
        elif choice == '6':
            list_all()
        elif choice == '7':
            cat = input("请输入要清空的类别: ").strip()
            clear_category(cat)
        elif choice == '8':
            confirm = input("确认重置? (y/n): ").strip().lower()
            if confirm == 'y':
                reset_all()
        elif choice == '9':
            export_knowledge()
        elif choice == '10':
            file = input("请输入导入文件路径: ").strip()
            if file:
                import_knowledge(file)
        elif choice == '11':
            update_teachers()
        elif choice == '0':
            print("再见!")
            break
        else:
            print("无效选择")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="知识库管理工具")
    parser.add_argument('action', nargs='?', choices=[
        'status', 'list', 'add-scholarship', 'add-dormitory', 
        'add-three-ratio', 'add-general', 'clear', 'reset',
        'export', 'import', 'update-teachers', 'interactive'
    ], help='操作类型')
    parser.add_argument('--content', '-c', help='知识内容')
    parser.add_argument('--source', '-s', default='管理员', help='来源')
    parser.add_argument('--file', '-f', help='文件路径')
    
    args = parser.parse_args()
    
    if args.action == 'status':
        status()
    elif args.action == 'list':
        list_all()
    elif args.action == 'add-scholarship':
        content = args.content or input("请输入内容: ")
        add_scholarship(content, args.source)
    elif args.action == 'add-dormitory':
        content = args.content or input("请输入内容: ")
        add_dormitory(content, args.source)
    elif args.action == 'add-three-ratio':
        content = args.content or input("请输入内容: ")
        add_three_ratio(content, args.source)
    elif args.action == 'add-general':
        content = args.content or input("请输入内容: ")
        add_general(content, args.source)
    elif args.action == 'clear':
        category = args.content or 'general'
        clear_category(category)
    elif args.action == 'reset':
        confirm = input("确认重置? (y/n): ")
        if confirm.lower() == 'y':
            reset_all()
    elif args.action == 'export':
        export_knowledge(args.file or "knowledge_backup.json")
    elif args.action == 'import':
        if args.file:
            import_knowledge(args.file)
        else:
            print("请指定导入文件: --file <path>")
    elif args.action == 'update-teachers':
        update_teachers()
    elif args.action == 'interactive':
        interactive()
    else:
        parser.print_help()
        print("\n示例:")
        print("  python manage_knowledge.py status")
        print("  python manage_knowledge.py add-scholarship -c '新奖学金内容'")
        print("  python manage_knowledge.py list")
        print("  python manage_knowledge.py export -f backup.json")
        print("  python manage_knowledge.py interactive")

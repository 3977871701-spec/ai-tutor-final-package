from typing import Dict, List, Optional, Tuple
from app.rag.knowledge_base import get_knowledge_base
from app.intent.recognizer import Intent, get_intent_recognizer
from app.ai.grok_client import get_grok_client
import re


SYSTEM_PROMPT = """你是一个智能AI辅导员，专门帮助学生解答校园事务问题。

你的职责：
1. 回答关于奖助学金、宿舍、消三比等校园事务的问题
2. 根据提供的知识库内容回答问题，如果没有相关信息则如实说明
3. 回复要简洁、专业、易懂，使用emoji和清晰的结构
4. 如需转人工，帮助学生转接对应老师

回复格式要求：
- 使用emoji增加可读性（🎓🏠✅📋💡📞）
- 使用标题和列表结构
- 关键信息用加粗或特殊标记
- 控制在600字以内
"""


class AIResponseGenerator:
    def __init__(self):
        self.kb = get_knowledge_base()
        self.recognizer = get_intent_recognizer()
        self.grok = get_grok_client()
    
    async def generate_response(self, query: str, user_context: Optional[Dict] = None) -> Tuple[str, str]:
        """
        Generate AI response for user query.
        Returns: (response_text, intent_type)
        """
        # Step 1: Recognize intent
        intent = self.recognizer.recognize(query)
        
        # Step 2: Handle special intents
        if intent == Intent.GREETING:
            return self._handle_greeting(), "greeting"
        
        if intent == Intent.TRANSFER_HUMAN:
            return self.recognizer.get_transfer_message(query), "transfer_human"
        
        # Step 3: Search knowledge base
        docs = self.kb.search(query, top_k=5)
        
        # Step 4: Generate response using RAG + LLM
        if docs:
            response = await self._generate_rag_response(query, docs, intent)
        else:
            # No relevant docs, use general knowledge with LLM
            response = await self._generate_general_response(query, intent)
        
        return response, intent.value
    
    def _handle_greeting(self) -> str:
        return (
            "👋 你好！我是AI辅导员！\n\n"
            "🎓 我可以帮你查询以下校园事务：\n\n"
            "   1️⃣ 奖助学金申请\n"
            "      材料清单 | 申请流程 | 时间节点\n\n"
            "   2️⃣ 宿舍相关办理\n"
            "      调换宿舍 | 退宿申请 | 申请住宿\n\n"
            "   3️⃣ 消三比\n"
            "      达标标准 | 申请流程\n\n"
            "   4️⃣ 其他校园事务\n\n"
            "💬 请输入您想咨询的问题~\n"
            "\n─────────────────\n"
            "❓ 如需转人工，请回复【转人工】"
        )
    
    async def _generate_rag_response(self, query: str, docs: List[Dict], intent: Intent) -> str:
        """Generate response based on retrieved documents"""
        
        # Build context from documents
        context = "\n\n".join([
            f"【文档 {i+1}】\n{doc['content']}"
            for i, doc in enumerate(docs)
        ])
        
        # Intent-specific prompt
        intent_prompts = {
            Intent.SCHOLARSHIP: "请根据以下奖学金/助学金相关文档回答学生的问题。回答要包含具体的申请条件、所需材料和流程步骤。",
            Intent.DORMITORY: "请根据以下宿舍相关文档回答学生的问题。回答要包含具体的申请条件、办理流程和注意事项。",
            Intent.THREE_RATIO: "请根据以下消三比相关文档回答学生的问题。回答要包含达标标准和申请流程。",
            Intent.OTHER: "请根据以下文档回答学生的问题。",
            Intent.UNKNOWN: "请根据以下相关文档回答学生的问题。如果文档内容不直接相关，请基于常识回答。",
        }
        
        instruction = intent_prompts.get(intent, intent_prompts[Intent.UNKNOWN])
        
        prompt = f"""学生问题: {query}

{instruction}

---
相关文档：
{context}
---

请用简洁专业的语言回答，包含具体的流程步骤和注意事项。如果文档中没有相关信息，请说明并建议学生联系老师。"""

        messages = [{"role": "user", "content": prompt}]
        
        try:
            response = await self.grok.chat(messages, system_prompt=SYSTEM_PROMPT)
            return response
        except Exception as e:
            # Fallback: 直接使用RAG文档内容回复（当LLM API不可用时）
            return self._generate_fallback_response(query, docs, intent)
    
    def _generate_fallback_response(self, query: str, docs: List[Dict], intent: Intent) -> str:
        """Fallback response when LLM is unavailable - use RAG content directly"""
        if not docs:
            return (
                "😅 抱歉，知识库中暂无相关信息。\n\n"
                "📞 建议您联系相关老师获取准确信息\n"
                "❓ 或回复【转人工】由老师为您解答"
            )
        
        # Map intent to category for filtering
        intent_to_category = {
            Intent.SCHOLARSHIP: "scholarship",
            Intent.DORMITORY: "dormitory",
            Intent.THREE_RATIO: "three_ratio",
        }
        
        target_category = intent_to_category.get(intent)
        
        # Filter documents by matching category
        if target_category:
            filtered_docs = [doc for doc in docs if doc.get('metadata', {}).get('category') == target_category]
            # If no exact match, still use the top results but log warning
            if not filtered_docs:
                filtered_docs = docs[:2]
        else:
            filtered_docs = docs[:2]
        
        # 从文档中提取主要内容（最多2个文档，避免过长）
        content_parts = []
        for doc in filtered_docs[:2]:
            content_parts.append(self._clean_and_truncate_content(doc['content'], max_chars=350))
        
        combined_content = "\n\n".join(content_parts)
        
        # 根据意图添加引导语和emoji
        intent_headers = {
            Intent.SCHOLARSHIP: ("🎓 奖学金申请指南\n", "📋 申请条件\n", "📝 申请流程\n"),
            Intent.DORMITORY: ("🏠 宿舍办理指南\n", "📋 申请条件\n", "📝 办理流程\n"),
            Intent.THREE_RATIO: ("✅ 消三比指南\n", "📋 达标标准\n", "📝 申请流程\n"),
            Intent.OTHER: ("📄 相关信息\n", None, None),
            Intent.UNKNOWN: ("📋 相关信息\n", None, None),
        }
        
        header, cond_label, proc_label = intent_headers.get(intent, ("📋 信息汇总\n", None, None))
        
        # 格式化内容，添加emoji和结构
        formatted_content = self._format_content(combined_content, intent)
        
        footer = (
            "\n─────────────────\n"
            "💡 如需更多帮助，请回复【转人工】联系老师"
        )
        
        return header + formatted_content + footer
    
    def _clean_and_truncate_content(self, content: str, max_chars: int = 350) -> str:
        """Clean and truncate content to fit within max_chars"""
        # Remove excessive whitespace
        content = re.sub(r'\s+', ' ', content)
        content = content.strip()
        
        # Truncate if too long
        if len(content) > max_chars:
            # Try to cut at a sentence boundary
            cut_point = content[:max_chars].rfind('。')
            if cut_point > max_chars * 0.5:
                content = content[:cut_point + 1]
            else:
                content = content[:max_chars] + "..."
        
        return content
    
    def _format_content(self, content: str, intent: Intent) -> str:
        """Format content with better structure and emoji"""
        lines = content.split('\n')
        formatted_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Skip redundant headers
            if any(kw in line for kw in ['申请条件', '申请流程', '办理流程', '达标标准', '奖励标准', '资助标准']):
                # Check if this line is a header (short) or content (long)
                if len(line) < 30:
                    # This is a header line - add formatting
                    formatted_lines.append(f"\n─── {line} ───")
                    continue
            
            # Format numbered lists
            if re.match(r'^\d+[\.、]', line):
                formatted_lines.append(f"   {line}")
            # Format bullet points
            elif line.startswith('-') or line.startswith('•'):
                formatted_lines.append(f"   • {line[1:].strip()}")
            else:
                formatted_lines.append(line)
        
        return '\n'.join(formatted_lines)

    async def _generate_general_response(self, query: str, intent: Intent) -> str:
        """Generate response when no documents found - use LLM's general knowledge"""
        
        intent_contexts = {
            Intent.SCHOLARSHIP: "这个问题涉及奖学金或助学金申请。我没有找到相关的学校文件，请联系学生工作办公室的老师获取准确信息。",
            Intent.DORMITORY: "这个问题涉及宿舍相关办理。我没有找到相关的学校文件，请联系宿舍管理办公室的老师获取准确信息。",
            Intent.THREE_RATIO: "这个问题涉及消三比。我没有找到相关的学校文件，请联系教务办公室的老师获取准确信息。",
            Intent.UNKNOWN: "这个问题涉及校园事务。我没有找到相关的学校文件。",
        }
        
        context = intent_contexts.get(intent, intent_contexts[Intent.UNKNOWN])
        
        prompt = f"""学生问题: {query}

{context}

请用友好、专业的语气回复，可以：
1. 建议学生访问相关部门的网站或联系老师
2. 提供一般性的校园事务咨询建议
3. 如果确定无法回答，明确建议转人工"""

        messages = [{"role": "user", "content": prompt}]
        
        try:
            response = await self.grok.chat(messages, system_prompt=SYSTEM_PROMPT)
            return response
        except Exception as e:
            # Fallback: 提供友好的回复，引导转人工
            return self._generate_general_fallback_response(intent)
    
    def _generate_general_fallback_response(self, intent: Intent) -> str:
        """Fallback response when both RAG and LLM are unavailable"""
        transfer_messages = {
            Intent.SCHOLARSHIP: (
                "😅 抱歉，奖学金相关问题我暂时无法准确回答\n\n"
                "📞 请联系：学生工作办公室 张老师\n"
                "   电话：010-12345678\n\n"
                "❓ 或回复【转人工】由老师为您解答"
            ),
            Intent.DORMITORY: (
                "😅 抱歉，宿舍相关问题我暂时无法准确回答\n\n"
                "📞 请联系：宿舍管理办公室 李老师\n"
                "   电话：010-23456789\n\n"
                "❓ 或回复【转人工】由老师为您解答"
            ),
            Intent.THREE_RATIO: (
                "😅 抱歉，消三比相关问题我暂时无法准确回答\n\n"
                "📞 请联系：教务办公室 王老师\n"
                "   电话：010-34567890\n\n"
                "❓ 或回复【转人工】由老师为您解答"
            ),
            Intent.OTHER: (
                "😅 抱歉，我暂时无法回答该问题\n\n"
                "❓ 请回复【转人工】联系老师获取准确信息"
            ),
            Intent.UNKNOWN: (
                "😅 抱歉，系统暂时无法处理您的请求\n\n"
                "❓ 请回复【转人工】联系老师"
            ),
            Intent.GREETING: "",
            Intent.TRANSFER_HUMAN: "",
        }
        msg = transfer_messages.get(intent)
        return msg if msg else ("😅 抱歉，暂无法回答该问题\n❓ 请回复【转人工】联系老师")


# Singleton
_generator: Optional[AIResponseGenerator] = None

def get_response_generator() -> AIResponseGenerator:
    global _generator
    if _generator is None:
        _generator = AIResponseGenerator()
    return _generator

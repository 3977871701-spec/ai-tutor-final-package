from enum import Enum
from typing import Dict, List, Optional
import yaml
from pathlib import Path

# Intent categories
class Intent(Enum):
    SCHOLARSHIP = "scholarship"        # 奖助学金
    DORMITORY = "dormitory"           # 宿舍相关
    THREE_RATIO = "three_ratio"        # 消三比
    OTHER = "other"                   # 其他校园事务
    TRANSFER_HUMAN = "transfer_human" # 转人工
    GREETING = "greeting"              # 问候/闲聊
    UNKNOWN = "unknown"                # 未知

# Keywords for each intent
INTENT_KEYWORDS = {
    Intent.SCHOLARSHIP: [
        "奖学金", "助学金", "国家助学金", "助学贷款", "贫困生", 
        "补贴", "评定", "奖学金申请", "助学金申请", "材料清单",
        "申请流程", "时间节点", "国家奖学金", "励志奖学金"
    ],
    Intent.DORMITORY: [
        "宿舍", "床位", "住宿", "调换宿舍", "换宿舍", "退宿", 
        "退房", "寝室", "入住", "退寝", "住宿费", "押金",
        "申请住宿", "宿舍调整", "宿舍申请"
    ],
    Intent.THREE_RATIO: [
        "消三比", "三比", "达标", "成绩达标", "学分", "绩点",
        "消三比申请", "三比达标", "申请消三比"
    ],
    Intent.TRANSFER_HUMAN: [
        "转人工", "找老师", "老师电话", "联系老师", "投诉",
        "紧急", "人工客服", "真人", "要问老师", "老师在哪"
    ],
    Intent.GREETING: [
        "你好", "您好", "hi", "hello", "hey", "在吗", "在嘛",
        "早上好", "下午好", "晚上好", "嗨", "嘿"
    ]
}

# Load teacher contacts
CONFIG_PATH = Path(__file__).parent.parent.parent / "config.yaml"
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

TEACHER_CONTACTS = config.get("teacher", {}).get("contacts", [])


class IntentRecognizer:
    def __init__(self):
        self.intent_keywords = INTENT_KEYWORDS
    
    def recognize(self, query: str) -> Intent:
        query_lower = query.lower()
        
        # Check greeting first
        if self._check_intent(query_lower, Intent.GREETING):
            return Intent.GREETING
        
        # Check transfer human
        if self._check_intent(query_lower, Intent.TRANSFER_HUMAN):
            return Intent.TRANSFER_HUMAN
        
        # Check specific intents
        if self._check_intent(query_lower, Intent.SCHOLARSHIP):
            return Intent.SCHOLARSHIP
        
        if self._check_intent(query_lower, Intent.DORMITORY):
            return Intent.DORMITORY
        
        if self._check_intent(query_lower, Intent.THREE_RATIO):
            return Intent.THREE_RATIO
        
        return Intent.UNKNOWN

    def _check_intent(self, query: str, intent: Intent) -> bool:
        keywords = self.intent_keywords.get(intent, [])
        for keyword in keywords:
            if keyword.lower() in query:
                return True
        return False

    def get_teacher_for_intent(self, intent: Intent) -> Optional[Dict]:
        """Get the appropriate teacher contact for a given intent"""
        if intent == Intent.TRANSFER_HUMAN:
            # Return general contact for transfer human
            return TEACHER_CONTACTS[0] if TEACHER_CONTACTS else None
        
        # Map intent to specialty teacher
        intent_to_specialty = {
            Intent.SCHOLARSHIP: "奖助学金",
            Intent.DORMITORY: "宿舍",
            Intent.THREE_RATIO: "消三比"
        }
        
        specialty = intent_to_specialty.get(intent)
        if specialty:
            for teacher in TEACHER_CONTACTS:
                if specialty in teacher.get("specialty", ""):
                    return teacher
        
        return TEACHER_CONTACTS[0] if TEACHER_CONTACTS else None

    def get_transfer_message(self, query: str) -> str:
        """Generate transfer human message with teacher contact"""
        teacher = self.get_teacher_for_intent(Intent.TRANSFER_HUMAN)
        if teacher:
            return (
                f"您的问题比较复杂，我来帮您转接专业老师。\n\n"
                f"📞 {teacher['name']}\n"
                f"📍 {teacher['department']}\n"
                f"🗂 负责: {teacher['specialty']}\n"
                f"📱 电话: {teacher['phone']}\n\n"
                f"工作时间可致电咨询，或前往 {teacher['department']} 办理。\n"
                f"如需帮助创建工单，请回复「工单」+您的详细问题。"
            )
        return "您的问题已转接给我们的人工客服团队，请稍等，老师会尽快回复您。"

    def explain_intent(self, query: str) -> str:
        """Explain what intent was recognized"""
        intent = self.recognize(query)
        intent_names = {
            Intent.SCHOLARSHIP: "奖助学金相关",
            Intent.DORMITORY: "宿舍相关",
            Intent.THREE_RATIO: "消三比相关",
            Intent.TRANSFER_HUMAN: "转人工",
            Intent.GREETING: "问候",
            Intent.OTHER: "其他校园事务",
            Intent.UNKNOWN: "未知"
        }
        return intent_names.get(intent, "未知")


# Singleton
_recognizer: Optional[IntentRecognizer] = None

def get_intent_recognizer() -> IntentRecognizer:
    global _recognizer
    if _recognizer is None:
        _recognizer = IntentRecognizer()
    return _recognizer

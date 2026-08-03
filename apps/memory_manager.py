import re
import json
from typing import Dict, List


class MemoryManager:
    """用户画像记忆管理器"""

    def __init__(self):
        # 预设的记忆槽位
        self.slots = {
            "user_name": None,
            "user_profession": None,
            "user_interests": [],
            "user_goal": None,
            "last_topic": None,
            "user_preferences": {}
        }

    def extract_info(self, user_input: str, ai_response: str = "") -> Dict:
        """从对话中提取关键信息"""
        extracted = {}

        # 提取姓名（匹配"我叫xxx"、"我是xxx"）
        name_patterns = [
            r"我[叫是][\s]*([\u4e00-\u9fa5a-zA-Z]{2,4})",
            r"(?:大家好|你们好|你好)[，,]*我[叫是][\s]*([\u4e00-\u9fa5a-zA-Z]{2,4})"
        ]
        for pattern in name_patterns:
            match = re.search(pattern, user_input)
            if match:
                extracted["user_name"] = match.group(1)
                break

        # 提取职业（匹配"我是xx师/xx员/xx工"）
        profession_patterns = [
            r"我[是][\s]*(?:一名?|一个)?([\u4e00-\u9fa5a-zA-Z]{2,6}?[师员工研])",
            r"我[做干][\s]*(?:的?是)?([\u4e00-\u9fa5a-zA-Z]{2,6}?[师员工研])"
        ]
        for pattern in profession_patterns:
            match = re.search(pattern, user_input)
            if match:
                extracted["user_profession"] = match.group(1)
                break

        # 提取兴趣（匹配"我喜欢xx"）
        interest_match = re.search(r"我[喜欢热爱][\s]*([\u4e00-\u9fa5a-zA-Z]{2,8})", user_input)
        if interest_match:
            extracted["user_interests"] = [interest_match.group(1)]

        # 提取目标（匹配"我想xx"、"我要xx"）
        goal_match = re.search(r"我[想要][\s]*(.*?)[。，,\.]", user_input)
        if goal_match:
            extracted["user_goal"] = goal_match.group(1).strip()

        return extracted

    def update_profile(self, profile: Dict, new_info: Dict) -> Dict:
        """更新用户画像"""
        for key, value in new_info.items():
            if value:
                if key == "user_interests":
                    # 合并兴趣列表（去重）
                    if isinstance(profile.get(key), list):
                        profile[key] = list(set(profile[key] + value))
                    else:
                        profile[key] = value
                else:
                    profile[key] = value
        return profile

    def get_context_prompt(self, profile: Dict) -> str:
        """生成用户画像的描述文本，注入到系统提示词中"""
        parts = []

        if profile.get("user_name"):
            parts.append(f"你正在和 {profile['user_name']} 对话")

        if profile.get("user_profession"):
            parts.append(f"ta 是一名 {profile['user_profession']}")

        if profile.get("user_interests"):
            interests = "、".join(profile["user_interests"])
            parts.append(f"ta 对 {interests} 感兴趣")

        if profile.get("user_goal"):
            parts.append(f"ta 当前的目标是：{profile['user_goal']}")

        if parts:
            return "【用户画像】" + "；".join(parts) + "。请基于这些信息，提供更个性化的回复。"
        return ""
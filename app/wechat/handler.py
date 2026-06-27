import hashlib
import time
import xml.etree.ElementTree as ET
from typing import Optional, Dict, Any
from fastapi import Request, HTTPException
import yaml
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent.parent / "config.yaml"
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

WECHAT_TOKEN = config["wechat"]["token"]
WECHAT_APP_ID = config["wechat"]["app_id"]
WECHAT_APP_SECRET = config["wechat"]["app_secret"]


class WeChatValidator:
    """Validates WeChat server verification requests"""
    
    @staticmethod
    def validate_get(signature: str, timestamp: str, nonce: str, echostr: str) -> bool:
        """Validate GET request from WeChat (server verification)"""
        token = WECHAT_TOKEN
        tmp_list = sorted([token, timestamp, nonce])
        tmp_str = "".join(tmp_list)
        expected_signature = hashlib.sha1(tmp_str.encode()).hexdigest()
        
        return signature == expected_signature

    @staticmethod
    def parse_xml_message(xml_string: str) -> Dict[str, Any]:
        """Parse WeChat XML message into dict"""
        root = ET.fromstring(xml_string)
        message = {}
        for child in root:
            message[child.tag] = child.text
        return message


class WeChatMessageBuilder:
    """Builds WeChat XML responses"""
    
    TEXT_TEMPLATE = """<xml>
<ToUserName><![CDATA[{to_user}]]></ToUserName>
<FromUserName><![CDATA[{from_user}]]></FromUserName>
<CreateTime>{create_time}</CreateTime>
<MsgType><![CDATA[text]]></MsgType>
<Content><![CDATA[{content}]]></Content>
</xml>"""

    @staticmethod
    def build_text_response(to_user: str, from_user: str, content: str) -> str:
        return WeChatMessageBuilder.TEXT_TEMPLATE.format(
            to_user=from_user,  # Swap - response goes to sender
            from_user=to_user,
            create_time=int(time.time()),
            content=content
        )


class WeChatAccessToken:
    """Manages WeChat access token"""
    _token: Optional[str] = None
    _expires_at: float = 0
    
    @classmethod
    async def get_access_token(cls) -> str:
        """Get valid access token, refreshing if needed"""
        import httpx
        
        # Check if current token is still valid
        if cls._token and time.time() < cls._expires_at:
            return cls._token
        
        url = f"https://api.weixin.qq.com/cgi-bin/token"
        params = {
            "grant_type": "client_credential",
            "appid": WECHAT_APP_ID,
            "secret": WECHAT_APP_SECRET
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params)
            result = response.json()
            
            if "access_token" in result:
                cls._token = result["access_token"]
                cls._expires_at = time.time() + result.get("expires_in", 7200) - 300
                return cls._token
            else:
                raise Exception(f"Failed to get access token: {result}")
    
    @classmethod
    def clear_token(cls):
        cls._token = None
        cls._expires_at = 0

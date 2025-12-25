"""AI 总结服务，支持 OpenAI 兼容的 API（如 DeepSeek）"""
import os
import httpx
from typing import Optional
from loguru import logger


class AISummaryService:
    """AI 总结服务"""

    def __init__(self):
        self._last_token = None
        self._reload_config(log=True)  # 初始化时打印日志

    def _reload_config(self, log: bool = False):
        """重新加载配置（支持运行时更新环境变量）"""
        old_token = self.api_token if hasattr(self, 'api_token') else None
        self.api_token = os.getenv("AI_API_TOKEN")
        self.api_base_url = os.getenv("AI_API_BASE_URL", "https://api.deepseek.com/v1")
        self.model = os.getenv("AI_MODEL", "deepseek-chat")
        self.enabled = bool(self.api_token)

        # 只在初始化或配置变化时输出日志
        token_changed = (old_token != self.api_token)
        if log or token_changed:
            if self.enabled:
                logger.info(f"AI 总结服务已启用: API_URL={self.api_base_url}, MODEL={self.model}")
                if token_changed:
                    logger.info(f"AI_API_TOKEN 已更新 (长度: {len(self.api_token) if self.api_token else 0})")
            else:
                logger.warning("AI 总结服务未启用: AI_API_TOKEN 未设置")

    def get_config(self) -> dict:
        """获取当前配置信息（用于调试）"""
        self._reload_config()
        return {
            "enabled": self.enabled,
            "api_base_url": self.api_base_url,
            "model": self.model,
            "has_token": bool(self.api_token),
            "token_length": len(self.api_token) if self.api_token else 0
        }

    async def summarize(self, title: str, link: str) -> Optional[str]:
        """
        生成 AI 总结

        Args:
            title: 文章标题
            link: 文章链接

        Returns:
            AI 总结文本，如果失败则返回 None
        """
        # 每次调用时重新检查配置（支持运行时更新）
        self._reload_config()

        if not self.enabled:
            return None

        if not link:
            return None

        # 构建提示词，让 AI 自己读取链接内容
        prompt = f"""请访问以下链接并阅读文章内容，然后用简洁的中文总结文章，控制在100字以内：

文章标题：{title}
文章链接：{link}

请直接访问链接并总结文章的主要内容。"""

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {
                    "Authorization": f"Bearer {self.api_token}",
                    "Content-Type": "application/json"
                }

                payload = {
                    "model": self.model,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.7,
                    "max_tokens": 200
                }

                logger.debug(f"发送 AI 总结请求到 {self.api_base_url}/chat/completions (模型: {self.model})")
                response = await client.post(
                    f"{self.api_base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )

                if response.status_code == 200:
                    result = response.json()
                    summary = result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                    if summary:
                        logger.success(f"AI 总结生成成功，长度: {len(summary)} 字符")
                    else:
                        logger.warning(f"AI API 返回空总结，响应: {result}")
                    return summary if summary else None
                else:
                    logger.error(f"AI API 请求失败: HTTP {response.status_code}")
                    logger.error(f"响应内容: {response.text[:500]}")
                    return None

        except httpx.TimeoutException:
            logger.error("AI API 请求超时（30秒）")
            return None
        except httpx.RequestError as e:
            logger.error(f"AI API 请求错误: {str(e)}")
            return None
        except Exception as e:
            logger.exception(f"AI 总结生成失败: {type(e).__name__}: {str(e)}")
            return None


# 全局实例
ai_summary_service = AISummaryService()

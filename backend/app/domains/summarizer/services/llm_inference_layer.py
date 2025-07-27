"""
Simplified OpenAI-only LLM Inference Layer

Direct OpenAI API integration without complex model selection or caching.
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any
import openai
from app.domains.summarizer.core.config import get_openai_api_key

logger = logging.getLogger(__name__)


class SimplifiedLLMClient:
    """Simplified OpenAI client with direct API access."""
    
    def __init__(self):
        """Initialize with fresh API key from settings."""
        api_key = get_openai_api_key()
        logger.info(f"Initializing OpenAI client with API key: {api_key[:20]}...")
        self.client = openai.OpenAI(api_key=api_key)
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-4-turbo",
        max_tokens: int = 700,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """
        Create a chat completion using OpenAI API.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: OpenAI model to use
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            
        Returns:
            Dict with response content and metadata
        """
        try:
            # Use asyncio executor for sync OpenAI call
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature
                )
            )
            
            return {
                "content": response.choices[0].message.content,
                "model": model,
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise


def get_llm_client() -> SimplifiedLLMClient:
    """Get a fresh LLM client instance - no caching."""
    return SimplifiedLLMClient()
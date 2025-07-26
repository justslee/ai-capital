"""
LLM Inference Layer

Intelligent model selection based on task complexity, cost constraints,
and performance requirements. Supports both OpenAI and open-source models.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass
import asyncio

import openai
from anthropic import Anthropic

logger = logging.getLogger(__name__)


class TaskComplexity(Enum):
    """Task complexity levels for model selection."""
    SIMPLE = "simple"        # Basic extraction, simple Q&A
    MEDIUM = "medium"        # Standard summarization, analysis
    COMPLEX = "complex"      # Deep analysis, reasoning, complex RAG
    CRITICAL = "critical"    # High-stakes analysis, regulatory compliance


class ModelProvider(Enum):
    """Supported model providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OPENSOURCE = "opensource"  # Local/hosted open-source models


@dataclass
class ModelConfig:
    """Configuration for an LLM model."""
    name: str
    provider: ModelProvider
    cost_per_1k_tokens_input: float
    cost_per_1k_tokens_output: float
    max_tokens: int
    context_window: int
    quality_score: float  # 1-10 scale
    speed_score: float    # 1-10 scale (10 = fastest)
    endpoint_url: Optional[str] = None
    api_key_env: Optional[str] = None


@dataclass
class InferenceRequest:
    """Request for LLM inference with requirements."""
    messages: List[Dict[str, str]]
    task_type: str
    complexity: TaskComplexity
    max_cost_per_request: Optional[float] = None
    max_response_time_seconds: Optional[float] = None
    require_high_quality: bool = False
    estimated_input_tokens: Optional[int] = None
    estimated_output_tokens: Optional[int] = None
    preferred_provider: Optional[ModelProvider] = None


class LLMInferenceLayer:
    """Intelligent LLM inference layer with cost optimization."""
    
    def __init__(self):
        self.models = self._initialize_models()
        self.usage_stats = {}
        self.model_performance_cache = {}
        
        # Initialize clients
        self.openai_client = openai.OpenAI()
        self.anthropic_client = Anthropic()
        
    def _initialize_models(self) -> Dict[str, ModelConfig]:
        """Initialize available models with their configurations."""
        return {
            # OpenAI Models
            "gpt-4-turbo": ModelConfig(
                name="gpt-4-turbo",
                provider=ModelProvider.OPENAI,
                cost_per_1k_tokens_input=0.01,
                cost_per_1k_tokens_output=0.03,
                max_tokens=4096,
                context_window=128000,
                quality_score=9.5,
                speed_score=7.0,
                api_key_env="OPENAI_API_KEY"
            ),
            "gpt-4": ModelConfig(
                name="gpt-4",
                provider=ModelProvider.OPENAI,
                cost_per_1k_tokens_input=0.03,
                cost_per_1k_tokens_output=0.06,
                max_tokens=4096,
                context_window=8192,
                quality_score=9.0,
                speed_score=6.0,
                api_key_env="OPENAI_API_KEY"
            ),
            "gpt-3.5-turbo": ModelConfig(
                name="gpt-3.5-turbo",
                provider=ModelProvider.OPENAI,
                cost_per_1k_tokens_input=0.0015,
                cost_per_1k_tokens_output=0.002,
                max_tokens=4096,
                context_window=16385,
                quality_score=7.5,
                speed_score=9.0,
                api_key_env="OPENAI_API_KEY"
            ),
            
            # Anthropic Models
            "claude-3-opus": ModelConfig(
                name="claude-3-opus-20240229",
                provider=ModelProvider.ANTHROPIC,
                cost_per_1k_tokens_input=0.015,
                cost_per_1k_tokens_output=0.075,
                max_tokens=4096,
                context_window=200000,
                quality_score=9.5,
                speed_score=6.0,
                api_key_env="ANTHROPIC_API_KEY"
            ),
            "claude-3-sonnet": ModelConfig(
                name="claude-3-sonnet-20240229",
                provider=ModelProvider.ANTHROPIC,
                cost_per_1k_tokens_input=0.003,
                cost_per_1k_tokens_output=0.015,
                max_tokens=4096,
                context_window=200000,
                quality_score=8.5,
                speed_score=8.0,
                api_key_env="ANTHROPIC_API_KEY"
            ),
            "claude-3-haiku": ModelConfig(
                name="claude-3-haiku-20240307",
                provider=ModelProvider.ANTHROPIC,
                cost_per_1k_tokens_input=0.00025,
                cost_per_1k_tokens_output=0.00125,
                max_tokens=4096,
                context_window=200000,
                quality_score=7.0,
                speed_score=9.5,
                api_key_env="ANTHROPIC_API_KEY"
            ),
            
            # Open Source Models (via local inference or API)
            "llama-2-70b": ModelConfig(
                name="llama-2-70b-chat",
                provider=ModelProvider.OPENSOURCE,
                cost_per_1k_tokens_input=0.0001,  # Hosting costs
                cost_per_1k_tokens_output=0.0001,
                max_tokens=4096,
                context_window=4096,
                quality_score=8.0,
                speed_score=5.0,
                endpoint_url="http://localhost:8000/v1/chat/completions"
            ),
            "mixtral-8x7b": ModelConfig(
                name="mixtral-8x7b-instruct",
                provider=ModelProvider.OPENSOURCE,
                cost_per_1k_tokens_input=0.0001,
                cost_per_1k_tokens_output=0.0001,
                max_tokens=4096,
                context_window=32768,
                quality_score=8.2,
                speed_score=7.0,
                endpoint_url="http://localhost:8001/v1/chat/completions"
            )
        }
    
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text (rough approximation)."""
        return len(text.split()) * 1.3  # Rough estimate
    
    def calculate_cost(
        self, 
        model: ModelConfig, 
        input_tokens: int, 
        output_tokens: int
    ) -> float:
        """Calculate estimated cost for a request."""
        input_cost = (input_tokens / 1000) * model.cost_per_1k_tokens_input
        output_cost = (output_tokens / 1000) * model.cost_per_1k_tokens_output
        return input_cost + output_cost
    
    def select_optimal_model(self, request: InferenceRequest) -> Tuple[ModelConfig, str]:
        """
        Select the optimal model based on requirements and constraints.
        
        Returns:
            Tuple of (selected_model_config, selection_reason)
        """
        # Estimate tokens if not provided
        if not request.estimated_input_tokens:
            input_text = " ".join([msg["content"] for msg in request.messages])
            request.estimated_input_tokens = self.estimate_tokens(input_text)
        
        if not request.estimated_output_tokens:
            request.estimated_output_tokens = 500  # Default estimate
        
        # Filter models by constraints
        candidate_models = []
        
        for model_name, model in self.models.items():
            # Check context window
            if request.estimated_input_tokens > model.context_window:
                continue
                
            # Check provider preference
            if request.preferred_provider and model.provider != request.preferred_provider:
                continue
                
            # Check cost constraints
            if request.max_cost_per_request:
                estimated_cost = self.calculate_cost(
                    model, 
                    request.estimated_input_tokens, 
                    request.estimated_output_tokens
                )
                if estimated_cost > request.max_cost_per_request:
                    continue
            
            candidate_models.append((model_name, model))
        
        if not candidate_models:
            # Fallback to cheapest model
            cheapest = min(
                self.models.items(),
                key=lambda x: self.calculate_cost(x[1], request.estimated_input_tokens, request.estimated_output_tokens)
            )
            return cheapest[1], "fallback_cheapest"
        
        # Score models based on requirements
        scored_models = []
        
        for model_name, model in candidate_models:
            score = 0
            reasons = []
            
            # Quality requirements
            if request.complexity == TaskComplexity.CRITICAL:
                score += model.quality_score * 0.6
                reasons.append("quality_critical")
            elif request.complexity == TaskComplexity.COMPLEX:
                score += model.quality_score * 0.4
                reasons.append("quality_important")
            elif request.require_high_quality:
                score += model.quality_score * 0.5
                reasons.append("quality_required")
            else:
                score += model.quality_score * 0.2
            
            # Speed requirements
            if request.max_response_time_seconds and request.max_response_time_seconds < 10:
                score += model.speed_score * 0.4
                reasons.append("speed_required")
            else:
                score += model.speed_score * 0.1
            
            # Cost optimization (inverse - lower cost = higher score)
            estimated_cost = self.calculate_cost(
                model, request.estimated_input_tokens, request.estimated_output_tokens
            )
            cost_score = max(0, 10 - (estimated_cost * 100))  # Normalize cost to 0-10 scale
            score += cost_score * 0.3
            reasons.append("cost_optimized")
            
            # Task-specific bonuses
            if request.task_type == "summarization" and model.name in ["gpt-3.5-turbo", "claude-3-haiku"]:
                score += 1
                reasons.append("task_optimized")
            elif request.task_type == "analysis" and model.quality_score >= 8.5:
                score += 1
                reasons.append("task_optimized")
            
            scored_models.append((model_name, model, score, reasons))
        
        # Select best model
        best_model = max(scored_models, key=lambda x: x[2])
        selection_reason = f"score_{best_model[2]:.1f}_" + "_".join(best_model[3])
        
        return best_model[1], selection_reason
    
    async def invoke_model(
        self, 
        model: ModelConfig, 
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """Invoke the selected model."""
        start_time = time.time()
        
        try:
            if model.provider == ModelProvider.OPENAI:
                response = await self._invoke_openai(model, messages, max_tokens)
            elif model.provider == ModelProvider.ANTHROPIC:
                response = await self._invoke_anthropic(model, messages, max_tokens)
            elif model.provider == ModelProvider.OPENSOURCE:
                response = await self._invoke_opensource(model, messages, max_tokens)
            else:
                raise ValueError(f"Unsupported provider: {model.provider}")
            
            end_time = time.time()
            response["inference_time_seconds"] = end_time - start_time
            response["model_used"] = model.name
            response["provider"] = model.provider.value
            
            # Track usage stats
            self._track_usage(model, response)
            
            return response
            
        except Exception as e:
            logger.error(f"Error invoking model {model.name}: {e}")
            raise
    
    async def _invoke_openai(
        self, 
        model: ModelConfig, 
        messages: List[Dict[str, str]],
        max_tokens: Optional[int]
    ) -> Dict[str, Any]:
        """Invoke OpenAI model."""
        response = await self.openai_client.chat.completions.create(
            model=model.name,
            messages=messages,
            max_tokens=max_tokens or model.max_tokens,
            temperature=0.7
        )
        
        return {
            "content": response.choices[0].message.content,
            "input_tokens": response.usage.prompt_tokens,
            "output_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
            "cost": self.calculate_cost(
                model, 
                response.usage.prompt_tokens, 
                response.usage.completion_tokens
            )
        }
    
    async def _invoke_anthropic(
        self, 
        model: ModelConfig, 
        messages: List[Dict[str, str]],
        max_tokens: Optional[int]
    ) -> Dict[str, Any]:
        """Invoke Anthropic model."""
        # Convert messages format for Anthropic
        anthropic_messages = []
        system_message = None
        
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                anthropic_messages.append(msg)
        
        response = await self.anthropic_client.messages.create(
            model=model.name,
            max_tokens=max_tokens or model.max_tokens,
            system=system_message,
            messages=anthropic_messages
        )
        
        # Estimate tokens (Anthropic doesn't return exact counts)
        input_tokens = self.estimate_tokens(" ".join([m["content"] for m in messages]))
        output_tokens = self.estimate_tokens(response.content[0].text)
        
        return {
            "content": response.content[0].text,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "cost": self.calculate_cost(model, input_tokens, output_tokens)
        }
    
    async def _invoke_opensource(
        self, 
        model: ModelConfig, 
        messages: List[Dict[str, str]],
        max_tokens: Optional[int]
    ) -> Dict[str, Any]:
        """Invoke open-source model via API."""
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            payload = {
                "model": model.name,
                "messages": messages,
                "max_tokens": max_tokens or model.max_tokens,
                "temperature": 0.7
            }
            
            async with session.post(model.endpoint_url, json=payload) as response:
                result = await response.json()
                
                content = result["choices"][0]["message"]["content"]
                input_tokens = self.estimate_tokens(" ".join([m["content"] for m in messages]))
                output_tokens = self.estimate_tokens(content)
                
                return {
                    "content": content,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": input_tokens + output_tokens,
                    "cost": self.calculate_cost(model, input_tokens, output_tokens)
                }
    
    def _track_usage(self, model: ModelConfig, response: Dict[str, Any]):
        """Track model usage statistics."""
        if model.name not in self.usage_stats:
            self.usage_stats[model.name] = {
                "total_requests": 0,
                "total_tokens": 0,
                "total_cost": 0.0,
                "avg_response_time": 0.0,
                "last_used": datetime.utcnow()
            }
        
        stats = self.usage_stats[model.name]
        stats["total_requests"] += 1
        stats["total_tokens"] += response.get("total_tokens", 0)
        stats["total_cost"] += response.get("cost", 0)
        
        # Update average response time
        current_avg = stats["avg_response_time"]
        new_time = response.get("inference_time_seconds", 0)
        stats["avg_response_time"] = (current_avg * (stats["total_requests"] - 1) + new_time) / stats["total_requests"]
        stats["last_used"] = datetime.utcnow()
    
    async def smart_inference(self, request: InferenceRequest) -> Dict[str, Any]:
        """
        Perform intelligent inference with automatic model selection.
        
        This is the main entry point for the inference layer.
        """
        # Select optimal model
        selected_model, selection_reason = self.select_optimal_model(request)
        
        logger.info(f"Selected model: {selected_model.name} (reason: {selection_reason})")
        
        # Perform inference
        result = await self.invoke_model(
            selected_model, 
            request.messages,
            selected_model.max_tokens
        )
        
        # Add selection metadata
        result["model_selection"] = {
            "selected_model": selected_model.name,
            "selection_reason": selection_reason,
            "task_complexity": request.complexity.value,
            "estimated_cost": result.get("cost", 0)
        }
        
        return result
    
    def get_usage_report(self) -> Dict[str, Any]:
        """Get usage statistics report."""
        total_cost = sum(stats["total_cost"] for stats in self.usage_stats.values())
        total_requests = sum(stats["total_requests"] for stats in self.usage_stats.values())
        
        return {
            "total_cost": total_cost,
            "total_requests": total_requests,
            "models": self.usage_stats,
            "cost_per_request": total_cost / max(total_requests, 1),
            "generated_at": datetime.utcnow().isoformat()
        }


# Singleton instance
_inference_layer = None

def get_llm_inference_layer() -> LLMInferenceLayer:
    """Get singleton instance of LLM inference layer."""
    global _inference_layer
    if _inference_layer is None:
        _inference_layer = LLMInferenceLayer()
    return _inference_layer 
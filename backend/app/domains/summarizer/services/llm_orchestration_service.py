import logging
from typing import List, Optional, Dict

from ..models.metadata import ChunkMetadata
from .llm_inference_layer import get_llm_client
from .prompt_constructor import PromptConstructor, get_prompt_constructor

logger = logging.getLogger(__name__)

class LLMOrchestrationService:
    """
    Service to orchestrate the summarization of text chunks using an LLM.
    Manages the map-reduce process for generating summaries.
    """
    def __init__(self):
        self.llm_client = get_llm_client()
        self.prompt_constructor: PromptConstructor = get_prompt_constructor()

    async def summarize_chunk(self, chunk_text: str, section: str) -> str:
        """
        Summarizes a single text chunk (Map step).

        :param chunk_text: The text of the chunk to summarize.
        :param section: The section the chunk belongs to.
        :return: The summary of the chunk.
        """
        logger.info(f"Summarizing chunk of {len(chunk_text)} characters from section '{section}'.")
        
        prompt = self.prompt_constructor.construct_chunk_summary_prompt(chunk_text, section)
        
        # Use simplified OpenAI client
        result = await self.llm_client.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            model="gpt-3.5-turbo",
            max_tokens=500,
            temperature=0.7
        )
        summary = result.get('content', '') if result else ''
        
        if not summary:
            logger.error(f"Failed to summarize chunk from section '{section}'.")
            return "" # Return empty string on failure

        return summary

    async def synthesize_section_summary(self, chunk_summaries: List[str], section: str) -> str:
        """
        Synthesizes a collection of chunk summaries into a single section summary (Reduce step).

        :param chunk_summaries: A list of summaries for chunks within a section.
        :param section: The name of the section.
        :return: A synthesized summary for the entire section.
        """
        if not chunk_summaries:
            logger.warning(f"No chunk summaries provided for section '{section}' to synthesize.")
            return ""

        logger.info(f"Syntesizing {len(chunk_summaries)} chunk summaries for section '{section}'.")
        
        prompt = self.prompt_constructor.construct_section_synthesis_prompt(chunk_summaries, section)
        
        # Use simplified OpenAI client
        result = await self.llm_client.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            model="gpt-3.5-turbo",
            max_tokens=800,
            temperature=0.7
        )
        summary = result.get('content', '') if result else ''
        
        if not summary:
            logger.error(f"Failed to synthesize section summary for '{section}'.")
            return ""

        return summary

    async def generate_comprehensive_summary(self, section_summaries: Dict[str, str], ticker: str, form_type: str) -> str:
        """
        Generates a comprehensive, top-level summary from a dictionary of section summaries.

        :param section_summaries: A dictionary where keys are section names and values are their summaries.
        :param ticker: The stock ticker for context.
        :param form_type: The form type (e.g., '10-K') for context.
        :return: A final, comprehensive summary document.
        """
        if not section_summaries:
            logger.warning("No section summaries provided to generate a comprehensive report.")
            return ""

        logger.info(f"Generating comprehensive summary from {len(section_summaries)} section summaries for {ticker}.")
        
        prompt = self.prompt_constructor.construct_comprehensive_report_prompt(section_summaries, ticker, form_type)
        
        # Use simplified OpenAI client with higher-quality model for comprehensive summary
        result = await self.llm_client.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            model="gpt-4-turbo",
            max_tokens=4000,
            temperature=0.7
        )
        summary = result.get('content', '') if result else ''
        
        if not summary:
            logger.error(f"Failed to generate comprehensive summary for {ticker}.")
            return ""

        return summary

    async def answer_question_with_context(self, query: str, context: str) -> str:
        """
        Answers a question using the provided context.

        :param query: The user's question.
        :param context: The context retrieved from the document chunks.
        :return: The answer to the question.
        """
        logger.info(f"Answering question '{query}' with context of {len(context)} characters.")
        
        prompt = self.prompt_constructor.construct_rag_qa_prompt(query, context)
        
        result = await self.llm_client.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            model="gpt-4-turbo",
            max_tokens=500,
            temperature=0.2
        )
        answer = result.get('content', '') if result else ''
        
        if not answer:
            logger.error(f"Failed to answer question '{query}'.")
            return "Could not generate an answer based on the provided context."

        return answer


def get_llm_orchestration_service() -> "LLMOrchestrationService":
    """
    Get a fresh instance of LLMOrchestrationService - no caching to avoid stale API keys.
    """
    return LLMOrchestrationService() 
from typing import List, Dict, Any, Optional

class PromptConstructor:
    """
    Service responsible for constructing specific prompts for the LLM.
    """
    
    _SYSTEM_PROMPT_ANALYST = "You are an expert financial analyst AI. Your task is to provide clear, concise, and insightful analysis of SEC filings for investment professionals."

    def construct_chunk_summary_prompt(self, text: str, section: str) -> str:
        """Constructs the prompt for summarizing a single text chunk."""
        template = SUMMARIZATION_PROMPTS.get("chunk_summary", "")
        return template.format(text=text, section=section)
        
    def construct_section_synthesis_prompt(self, chunk_summaries: List[str], section: str) -> str:
        """Constructs the prompt for synthesizing a section summary from chunk summaries."""
        template = SUMMARIZATION_PROMPTS.get("section_synthesis", "")
        combined_summaries = "\n---\n".join(chunk_summaries)
        return template.format(chunk_summaries=combined_summaries, section=section)
        
    def construct_comprehensive_report_prompt(self, section_summaries: Dict[str, str], ticker: str, form_type: str) -> str:
        """Constructs the prompt for generating the final comprehensive report."""
        template = SUMMARIZATION_PROMPTS.get("top_level_summary", "")
        
        # Prepare a dictionary with keys like '{Section_Name}_summary'
        prompt_kwargs = {f"{key.replace(' ', '_')}_summary": value for key, value in section_summaries.items()}
        prompt_kwargs['ticker'] = ticker
        prompt_kwargs['form_type'] = form_type
        
        return template.format(**prompt_kwargs)

# Singleton instance
_prompt_constructor: Optional[PromptConstructor] = None

def get_prompt_constructor() -> "PromptConstructor":
    """
    Provides a singleton instance of the PromptConstructor.
    """
    global _prompt_constructor
    if _prompt_constructor is None:
        _prompt_constructor = PromptConstructor()
    return _prompt_constructor 
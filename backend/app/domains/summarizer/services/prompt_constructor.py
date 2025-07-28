from typing import List, Dict, Any, Optional

SUMMARIZATION_PROMPTS = {
    "chunk_summary": """Analyze the following text from the '{section}' section of an SEC filing and extract the most important information. Focus on material facts, key metrics, significant changes, strategic initiatives, and quantitative data.

    Instructions:
    - Preserve ALL important numerical data (revenue, expenses, percentages, dates, etc.)
    - Highlight key business developments, strategic changes, or operational updates
    - Include material risks, opportunities, or competitive factors mentioned
    - Maintain context about what metrics relate to (e.g., "Q3 2023 revenue increased 15%")
    - Be comprehensive but concise - capture the essence without losing critical details
    
    Text from {section}:
    {text}
    
    Key Information Summary:""",
    
    "section_synthesis": """Combine the following chunk summaries from the '{section}' section into a comprehensive, well-organized section summary.

    Instructions:
    - Organize information logically and remove redundancy
    - Preserve all important quantitative data and key metrics
    - Group related concepts together
    - Maintain the materiality and context of the information
    - Create a flowing narrative that captures the complete picture of this section
    
    Chunk Summaries from {section}:
    {chunk_summaries}
    
    Comprehensive Section Summary:""",
    
    "comprehensive_report": """
You are an expert financial analyst creating a comprehensive summary of {ticker}'s {form_type} filing. Focus on extracting and organizing the most material information for institutional investors who need to understand the company's current state, performance, and key factors affecting its business.

Use the following section summaries from the filing:

--- FILING SECTION SUMMARIES ---
{sections_text}
--- END SECTIONS ---

Create a well-structured, comprehensive summary with the following sections:

**Executive Summary**
- High-level overview of the company's current performance and position
- Most significant developments or changes since the last filing
- Key takeaways that matter most to investors

**Business Overview**
- Core business model and primary revenue streams
- Key segments, products, or services driving performance
- Any material changes to business operations or strategy

**Financial Performance**
- Revenue, profitability, and cash flow trends
- Balance sheet health and capital structure
- Key financial metrics and their year-over-year changes
- Notable financial developments or concerns

**Strategic Initiatives & Outlook**
- Management's key strategic priorities and initiatives
- Investment in growth areas, R&D, or new markets
- Future outlook and guidance provided by management

**Risk Factors & Challenges**
- Most material risks facing the business
- Regulatory, competitive, or operational challenges
- Market or industry headwinds affecting performance

**Key Operational Metrics**
- Industry-specific metrics relevant to the business
- Performance indicators beyond traditional financials
- Trends in customer base, market share, or operational efficiency

Instructions:
- Be comprehensive but focused on material information
- Preserve important quantitative data with proper context
- Organize information logically within each section
- Avoid investment recommendations - focus on factual summary
- Length should adapt based on the amount of material information available
""",

    "rag_qa": """
You are a financial analyst AI. Your task is to answer a specific question based *only* on the provided context from an SEC filing. Do not use any external knowledge or make assumptions beyond the text provided.

If the answer is not contained within the context, state that explicitly.

**Question:**
{query}

**Context from SEC Filing:**
---
{context}
---

**Answer:**
""",
}

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
        template = SUMMARIZATION_PROMPTS.get("comprehensive_report", "")
        
        # Dynamically build the sections text
        sections_text = ""
        for title, summary in section_summaries.items():
            # Replace underscores with spaces for a more readable title
            readable_title = title.replace('_', ' ')
            sections_text += f"## {readable_title}\n\n{summary}\n\n"
            
        return template.format(
            ticker=ticker,
            form_type=form_type,
            sections_text=sections_text.strip()
        )

    def construct_rag_qa_prompt(self, query: str, context: str) -> str:
        """Constructs the prompt for the RAG Q&A."""
        template = SUMMARIZATION_PROMPTS["rag_qa"]
        return template.format(query=query, context=context)

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
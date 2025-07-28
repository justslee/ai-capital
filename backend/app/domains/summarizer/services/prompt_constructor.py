from typing import List, Dict, Any, Optional

SUMMARIZATION_PROMPTS = {
    "chunk_summary": """Summarize the following text from the '{section}' section of an SEC filing. Focus on the key facts and figures.
    
    Text:
    {text}
    
    Summary:""",
    
    "section_synthesis": """Synthesize the following chunk summaries from the '{section}' section into a coherent summary of the entire section.
    
    Chunk Summaries:
    {chunk_summaries}
    
    Synthesized Section Summary:""",
    
    "comprehensive_report": """
As an expert senior analyst at a top-tier hedge fund, your task is to produce a comprehensive investment analysis report for {ticker} based on its latest {form_type} filing. The report must be clear, concise, and structured for a portfolio manager to make a quick, informed investment decision.

Use the following section summaries extracted directly from the filing as your primary source of information:

--- BEGIN FILING SECTION SUMMARIES ---
{sections_text}
--- END FILING SECTION SUMMARIES ---

Based on the information above, generate a report with the following structure. Be thorough and insightful in each section.

**1. Executive Summary:**
   - Provide a concise, high-level overview of the company's performance, strategic position, and the key investment thesis.
   - Should be a short paragraph.

**2. Company Overview:**
   - Briefly describe the business model, primary segments, and key products/services.

**3. Investment Thesis (Bull & Bear Case):**
   - **Bull Case:** Articulate the primary reasons to be bullish on the stock. What are the key growth drivers, competitive advantages, and market opportunities?
   - **Bear Case:** Articulate the primary counter-arguments. What are the significant headwinds, competitive threats, and execution risks?

**4. Financial Analysis:**
   - Analyze the key financial metrics reported. Comment on revenue trends, profitability (margins), and cash flow.
   - Discuss the health of the balance sheet (debt, cash position).
   - Highlight any standout financial figures or trends.

**5. Competitive Landscape:**
   - Identify the main competitors mentioned or implied in the filing.
   - Briefly assess {ticker}'s competitive positioning within its industry.

**6. Risk Factor Analysis:**
   - Synthesize the most critical risks disclosed in the filing. Do not just list them; explain their potential impact on the business.
   - Categorize them if possible (e.g., market risks, operational risks, regulatory risks).

**7. Management & Strategy:**
   - Briefly comment on management's discussion of their strategy, operational focus, and outlook for the future based on the provided text.

**8. Final Recommendation:**
   - Based *only* on the provided text, provide a concluding thought on the investment profile of the company. Is it more compelling or more cautionary? Do not use external information.
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
        template = SUMMARIZATION_PROMPTS.get("rag_qa", "")
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
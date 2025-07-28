"""
API endpoint for handling user queries.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Dict

from ..services.query_service import get_query_service, QueryService

router = APIRouter()

@router.get("/query/{ticker}", response_model=Dict)
async def answer_query(
    ticker: str,
    q: str = Query(..., description="The question to ask about the company's filings.")
):
    """
    Answers a question about a company's SEC filings using a RAG pipeline.
    """
    try:
        query_service: QueryService = get_query_service()
        response = await query_service.answer_question(ticker.upper(), q)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 
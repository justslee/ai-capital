from pydantic import BaseModel, Field
from typing import List, Optional

class TickerSentiment(BaseModel):
    ticker: str
    relevance_score: str
    ticker_sentiment_score: str
    ticker_sentiment_label: str

class Sentiment(BaseModel):
    title: str
    url: str
    time_published: str
    authors: List[str]
    summary: str
    banner_image: Optional[str] = None
    source: str
    category_within_source: str
    source_domain: str
    topics: List[dict]
    overall_sentiment_score: float
    overall_sentiment_label: str
    ticker_sentiment: List[TickerSentiment]

class SentimentFeed(BaseModel):
    feed: List[Sentiment] 
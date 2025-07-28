AI Capital: GenAI SEC Filing Analysis & Price Prediction
=====================================================

AI Capital democratizes sophisticated financial analysis by providing institutional-grade SEC filing analysis and AI-powered price predictions through simple APIs.

**Core Features:**
- **In-depth SEC filing summarization** - Key insights from 10-K/10-Q filings
- **AI-powered Q&A** - Ask questions about filings and get answers from the source
- **Advanced price predictions** - Time-series forecasting for any ticker

## 🚀 API Endpoints

### 📝 Summarization & Q&A

**Get Comprehensive Summary**
`GET /api/v1/summarizer/summary/{ticker}`

**Ask a Question**
`GET /api/v1/summarizer/query/{ticker}?q={question}`

### 📈 Price Prediction

**Get Price Forecast**
`GET /api/v1/predict/price/{ticker}`

## 🛠️ System Architecture

Our platform is built on a modern, scalable microservices architecture designed for performance and reliability.

- **FastAPI Backend** - High-performance Python framework for building APIs
- **S3 & DynamoDB** - Scalable, durable storage for SEC filings, summaries, and metadata
- **Pinecone** - Vector database for lightning-fast similarity search in our RAG pipeline
- **OpenAI** - State-of-the-art language models for summarization and Q&A
- **Docker & Kubernetes** - Containerization and orchestration for production deployments

## 💻 Local Development

### Setup

1.  **Clone the repository:**
    `git clone https://github.com/your-repo/ai-capital.git`
2.  **Navigate to the backend directory:**
    `cd ai-capital/backend`
3.  **Create and activate a virtual environment:**
    `python -m venv .venv`
    `source .venv/bin/activate`
4.  **Install dependencies:**
    `pip install -r requirements.txt`
5.  **Set up environment variables:**
    - Create a `.env` file in the `backend` directory
    - Add your API keys and other configurations (see `.env.example`)
6.  **Start the application:**
    `uvicorn app.main:app --reload --port 8000`

### Example Usage

# Get comprehensive summary for Apple
curl http://localhost:8000/api/v1/summarizer/summary/AAPL

# Ask a question about Apple's risks
curl "http://localhost:8000/api/v1/summarizer/query/AAPL?q=What%20are%20the%20main%20risks"
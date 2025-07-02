# AI Capital 🚀

**Empowering retail investors with hedge fund-level analytical tools, personalized and accessible.**

AI Capital democratizes sophisticated financial analysis by providing institutional-grade SEC filing analysis, DCF valuations, and AI-powered price predictions through simple APIs.

## 🎯 Mission

Transform how individual investors analyze markets by providing:
- **Professional SEC filing analysis** - Extract key insights from 10-K/10-Q filings instantly
- **Institutional-grade valuations** - DCF models used by top investment firms  
- **AI-powered predictions** - Machine learning forecasts trained on decades of market data
- **Personalized insights** - Tailored analysis based on your investment profile

## 🌐 Public API

Three core endpoints power intelligent investment decisions:

### 📋 SEC Filing Analysis
```http
GET /api/v1/summary/{ticker}/{year}/{form_type}
```
**Example**: `GET /api/v1/summary/AAPL/2023/10-K`

Get AI-powered summaries of SEC filings with key business insights, risk factors, and management analysis.

### 💰 Company Valuation  
```http
GET /api/v1/valuation/dcf/{ticker}
```
**Example**: `GET /api/v1/valuation/dcf/AAPL`

Institutional-grade DCF (Discounted Cash Flow) valuations with intrinsic value calculations.

### 🔮 Price Prediction
```http
POST /api/v1/predict/{ticker}
```
**Example**: `POST /api/v1/predict/AAPL?days_ahead=30&model_type=lstm`

AI-powered stock price forecasting with confidence intervals *(coming Q2 2024)*.

## 🏗️ Architecture

The platform uses domain-driven architecture with clear separation between public client APIs and internal operational systems:

- **🌐 Public API** (`/api/v1`) - Three core endpoints for retail investors
- **🔒 Internal API** (`/internal`) - Administrative and data management operations  
- **📊 Domain Services** - Modular business logic (Summarization, Valuation, Modeling)
- **☁️ Cloud Infrastructure** - AWS S3 storage with DuckDB analytics engine

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r backend/requirements.txt
```

### 2. Configure Environment
```bash
# Set required API keys in .env file
OPENAI_API_KEY=your_openai_key
FMP_API_KEY=your_fmp_key
TIINGO_API_KEY=your_tiingo_key
```

### 3. Start the Server
```bash
cd backend
uvicorn app.main:app --reload --port 8001
```

### 4. Test the API
```bash
# Get Apple's latest 10-K summary
curl http://localhost:8001/api/v1/summary/AAPL/2023/10-K

# Get DCF valuation for Apple
curl http://localhost:8001/api/v1/valuation/dcf/AAPL
```

## 📈 Example Response

```json
{
  "status": "success",
  "message": "DCF valuation calculated successfully",
  "data": {
    "intrinsic_value_per_share": 185.42,
    "total_intrinsic_value": 2891849280000,
    "shares_outstanding": 15599800000,
    "valuation_methodology": "Discounted Cash Flow (DCF)"
  },
  "ticker": "AAPL"
}
```

## 🛠️ Requirements

- **Python 3.8+**
- **API Keys** (free tiers available):
  - OpenAI API (for SEC analysis)
  - Financial Modeling Prep (for financial data)
  - Tiingo API (for price data)

---

**AI Capital: Democratizing institutional-grade financial analysis for everyone.** 📈
</code_block_to_apply_changes_from>
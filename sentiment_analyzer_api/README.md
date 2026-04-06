# Sentiment Analyzer API

A lightweight REST API serving a pre-trained Natural Language Processing (NLP) model for sentiment analysis. Built with FastAPI and HuggingFace Transformers.

## Features
- **FastAPI**: Blazing fast API framework with automatic Swagger `(/docs)` interactive documentation.
- **HuggingFace Pipeline**: Uses a default `distilbert-base-uncased-finetuned-sst-2-english` model for text classification.
- **RESTful**: Simple `/analyze` endpoint accepting JSON.

## Quick Start

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the development server:
   ```bash
   uvicorn main:app --reload
   ```

3. Visit your browser to test the API visually via the interactive docs:
   [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

## Example API Call

```bash
curl -X 'POST' \
  'http://127.0.0.1:8000/analyze' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "text": "I love learning about Machine Learning!"
}'
```

**Response:**
```json
{
  "label": "POSITIVE",
  "score": 0.9998,
  "text": "I love learning about Machine Learning!"
}
```

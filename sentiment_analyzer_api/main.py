from fastapi import FastAPI
from pydantic import BaseModel
from transformers import pipeline

app = FastAPI(title="Sentiment Analyzer API", description="A simple API for NLP sentiment analysis", version="1.0.0")

# Load HuggingFace pipeline (downloads the first time it is run)
sentiment_pipeline = pipeline("sentiment-analysis")

class TextRequest(BaseModel):
    text: str

class SentimentResponse(BaseModel):
    label: str
    score: float
    text: str

@app.post("/analyze", response_model=SentimentResponse)
async def analyze_sentiment(request: TextRequest):
    # Perform analysis
    result = sentiment_pipeline(request.text)[0]
    
    return SentimentResponse(
        label=result["label"],
        score=result["score"],
        text=request.text
    )

@app.get("/")
def read_root():
    return {"message": "Welcome to the Sentiment Analyzer API. Try the /docs endpoint."}

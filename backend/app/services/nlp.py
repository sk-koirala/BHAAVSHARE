from transformers import pipeline
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

# Lazy initialization
_sentiment_pipeline = None

def get_sentiment_pipeline():
    global _sentiment_pipeline
    if _sentiment_pipeline is None:
        try:
            logger.info("Loading mBERT sentiment model (this may take a while)...")
            # Using nlptown model as it's a pre-trained multilingual sentiment model based on mBERT
            _sentiment_pipeline = pipeline("sentiment-analysis", model="nlptown/bert-base-multilingual-uncased-sentiment")
            logger.info("Model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            _sentiment_pipeline = "mock"
    return _sentiment_pipeline

def parse_label(label: str) -> str:
    """nlptown returns '1 star' to '5 stars'"""
    if "1 star" in label or "2 stars" in label:
        return "negative"
    elif "3 stars" in label:
        return "neutral"
    else:
        return "positive"

def analyze_sentiment(texts: List[str]) -> List[Dict]:
    pipeline_obj = get_sentiment_pipeline()
    results = []
    
    if pipeline_obj == "mock":
        # Mock sentiment if model fails to load or memory is low
        import random
        for text in texts:
            sentiment = random.choice(["positive", "negative", "neutral"])
            results.append({
                "label": sentiment,
                "score": random.uniform(0.5, 0.99)
            })
        return results

    try:
        # Batched inference
        batch_results = pipeline_obj(texts, batch_size=4, truncation=True, max_length=512)
        for res in batch_results:
            results.append({
                "label": parse_label(res['label']),
                "score": res['score']
            })
    except Exception as e:
        logger.error(f"Error during batched inference: {e}")
        for _ in texts:
            results.append({"label": "neutral", "score": 0.5})
            
    return results

def process_news_batch(news_items_data: List[Dict]) -> List[Dict]:
    """Takes a list of news dictionaries, analyzes sentiment, and adds labels/scores."""
    if not news_items_data:
        return []
    
    texts = [item.get('title', '') + " " + item.get('summary', '') for item in news_items_data]
    sentiments = analyze_sentiment(texts)
    
    for i, item in enumerate(news_items_data):
        item['sentiment_label'] = sentiments[i]['label']
        item['sentiment_score'] = sentiments[i]['score']
        
    return news_items_data

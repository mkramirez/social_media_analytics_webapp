"""Sentiment analyzer using Hugging Face transformers for social media text."""

import hashlib
from typing import List, Dict, Optional
from pathlib import Path

try:
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    print("Warning: transformers library not available. Sentiment analysis will use fallback method.")


class SentimentAnalyzer:
    """Sentiment analysis engine using transformer models."""

    def __init__(self, model_name: str = "cardiffnlp/twitter-roberta-base-sentiment-latest",
                 cache_dir: str = None):
        """Initialize sentiment analyzer.

        Args:
            model_name: Hugging Face model name
            cache_dir: Directory to cache model files
        """
        self.model_name = model_name
        self.cache_dir = cache_dir or str(Path.home() / ".cache" / "transformers")
        self.model = None
        self.tokenizer = None
        self.device = None

        if TRANSFORMERS_AVAILABLE:
            self._load_model()
        else:
            print("Transformers not available. Install with: pip install transformers torch")

    def _load_model(self):
        """Load the transformer model and tokenizer."""
        try:
            print(f"Loading sentiment model: {self.model_name}")
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                cache_dir=self.cache_dir
            )
            self.model = AutoModelForSequenceClassification.from_pretrained(
                self.model_name,
                cache_dir=self.cache_dir
            )

            # Detect device (GPU if available, else CPU)
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            self.model.to(self.device)
            self.model.eval()  # Set to evaluation mode

            print(f"Model loaded successfully on {self.device}")
        except Exception as e:
            print(f"Error loading model: {e}")
            self.model = None
            self.tokenizer = None

    def analyze_text(self, text: str) -> Dict[str, float]:
        """Analyze sentiment of a single text.

        Args:
            text: Text to analyze

        Returns:
            Dict with sentiment scores: {negative, neutral, positive, compound}
        """
        if not text or not text.strip():
            return {
                'negative': 0.0,
                'neutral': 1.0,
                'positive': 0.0,
                'compound': 0.0
            }

        if not TRANSFORMERS_AVAILABLE or self.model is None:
            return self._fallback_sentiment(text)

        try:
            # Tokenize and prepare input
            inputs = self.tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                max_length=512,
                padding=True
            )
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            # Get predictions
            with torch.no_grad():
                outputs = self.model(**inputs)
                scores = torch.nn.functional.softmax(outputs.logits, dim=-1)

            # Extract scores (model typically outputs: negative, neutral, positive)
            neg_score = scores[0][0].item()
            neu_score = scores[0][1].item()
            pos_score = scores[0][2].item()

            return {
                'negative': neg_score,
                'neutral': neu_score,
                'positive': pos_score,
                'compound': pos_score - neg_score  # Range: -1 to 1
            }
        except Exception as e:
            print(f"Error analyzing text: {e}")
            return self._fallback_sentiment(text)

    def analyze_batch(self, texts: List[str], batch_size: int = 32) -> List[Dict[str, float]]:
        """Analyze sentiment of multiple texts in batches.

        Args:
            texts: List of texts to analyze
            batch_size: Number of texts to process at once

        Returns:
            List of sentiment score dictionaries
        """
        if not texts:
            return []

        if not TRANSFORMERS_AVAILABLE or self.model is None:
            return [self._fallback_sentiment(text) for text in texts]

        results = []

        try:
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]

                # Tokenize batch
                inputs = self.tokenizer(
                    batch,
                    return_tensors="pt",
                    truncation=True,
                    padding=True,
                    max_length=512
                )
                inputs = {k: v.to(self.device) for k, v in inputs.items()}

                # Get predictions
                with torch.no_grad():
                    outputs = self.model(**inputs)
                    scores = torch.nn.functional.softmax(outputs.logits, dim=-1)

                # Extract scores for each text in batch
                for j in range(len(batch)):
                    neg_score = scores[j][0].item()
                    neu_score = scores[j][1].item()
                    pos_score = scores[j][2].item()

                    results.append({
                        'negative': neg_score,
                        'neutral': neu_score,
                        'positive': pos_score,
                        'compound': pos_score - neg_score
                    })

        except Exception as e:
            print(f"Error in batch analysis: {e}")
            # Fallback to individual analysis
            results = [self._fallback_sentiment(text) for text in texts]

        return results

    def _fallback_sentiment(self, text: str) -> Dict[str, float]:
        """Simple keyword-based sentiment analysis fallback.

        Args:
            text: Text to analyze

        Returns:
            Dict with sentiment scores
        """
        if not text or not text.strip():
            return {
                'negative': 0.0,
                'neutral': 1.0,
                'positive': 0.0,
                'compound': 0.0
            }

        text_lower = text.lower()

        # Simple positive/negative keyword lists
        positive_keywords = [
            'good', 'great', 'excellent', 'amazing', 'wonderful', 'fantastic',
            'love', 'like', 'best', 'awesome', 'perfect', 'happy', 'glad',
            'thanks', 'thank', 'appreciate', 'beautiful', 'brilliant', 'nice'
        ]

        negative_keywords = [
            'bad', 'terrible', 'awful', 'horrible', 'worst', 'hate', 'dislike',
            'poor', 'disappointing', 'sad', 'angry', 'annoying', 'frustrating',
            'useless', 'broken', 'fail', 'failed', 'wrong', 'problem'
        ]

        # Count keyword occurrences
        pos_count = sum(1 for word in positive_keywords if word in text_lower)
        neg_count = sum(1 for word in negative_keywords if word in text_lower)
        total_count = pos_count + neg_count

        if total_count == 0:
            # No sentiment keywords found
            return {
                'negative': 0.0,
                'neutral': 1.0,
                'positive': 0.0,
                'compound': 0.0
            }

        # Calculate scores
        pos_score = pos_count / total_count
        neg_score = neg_count / total_count
        neu_score = max(0.0, 1.0 - (pos_score + neg_score))

        return {
            'negative': neg_score,
            'neutral': neu_score,
            'positive': pos_score,
            'compound': pos_score - neg_score
        }

    @staticmethod
    def hash_text(text: str) -> str:
        """Create MD5 hash of text for deduplication.

        Args:
            text: Text to hash

        Returns:
            MD5 hash string
        """
        return hashlib.md5(text.encode('utf-8')).hexdigest()

    @staticmethod
    def get_sentiment_label(compound_score: float) -> str:
        """Get sentiment label from compound score.

        Args:
            compound_score: Compound sentiment score (-1 to 1)

        Returns:
            Label: 'Positive', 'Negative', or 'Neutral'
        """
        if compound_score >= 0.05:
            return 'Positive'
        elif compound_score <= -0.05:
            return 'Negative'
        else:
            return 'Neutral'

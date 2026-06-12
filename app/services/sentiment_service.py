import os
import joblib
from app.services.model_service import ModelService
from app.services.nlp_service import preprocess_texts_batch

class SentimentService:
    """Service to evaluate text sentiment score, emotion maps, and psychological manipulation index"""
    
    def __init__(self):
        self.model_service = ModelService()
        self.model_version = "emotion_v1"
        self._model = None
        self._tfidf = None

    def _load_model(self):
        """Loads model and vectorizer on demand, or uses cached references"""
        if self._model is None or self._tfidf is None:
            # This raises FileNotFoundError if model/vectorizer are missing
            self._model, self._tfidf = self.model_service.load_model_and_vectorizer("emotion")
        return self._model, self._tfidf

    def analyze_texts_batch(self, texts):
        """
        Runs batch predictions on a list of texts.
        Optimized to use preprocess_texts_batch and matrix transformations.
        Returns:
            List of dicts, each with keys:
            - dominant_emotion: str
            - confidence: float
            - distribution: dict of emotion -> float (0.0 - 100.0)
            - risk_level: str ('LOW', 'MEDIUM', 'HIGH')
            - model_version: str
        """
        model, tfidf = self._load_model()
        
        # 1. Batch preprocess
        cleaned_texts = preprocess_texts_batch(texts)
        
        classes = list(model.classes_) # E.g., ['Anger', 'Fear', 'Joy', 'Love', 'Sadness', 'Surprise']
        
        # We need to compute prediction and probabilities.
        non_empty_indices = []
        non_empty_texts = []
        for i, text in enumerate(cleaned_texts):
            if text.strip():
                non_empty_indices.append(i)
                non_empty_texts.append(text)
                
        # Default/fallback result template
        default_distribution = {c: 0.0 for c in ["Joy", "Fear", "Anger", "Sadness", "Love", "Surprise"]}
        
        # Prepare outputs list of size len(texts) with placeholders
        outputs = [None] * len(texts)
        
        if non_empty_texts:
            X = tfidf.transform(non_empty_texts)
            # Predict probabilities if supported, otherwise predict class label
            if hasattr(model, "predict_proba"):
                probs_matrix = model.predict_proba(X)
                for idx, clean_idx in enumerate(non_empty_indices):
                    probs = probs_matrix[idx]
                    
                    # Convert to percentages (0-100%)
                    distribution = {}
                    for cls_name in ["Joy", "Fear", "Anger", "Sadness", "Love", "Surprise"]:
                        if cls_name in classes:
                            cls_idx = classes.index(cls_name)
                            distribution[cls_name] = round(float(probs[cls_idx]) * 100.0, 2)
                        else:
                            distribution[cls_name] = 0.0
                            
                    # Dominant emotion is the class with highest probability
                    dominant_idx = probs.argmax()
                    dominant_emotion = classes[dominant_idx]
                    confidence = round(float(probs[dominant_idx]), 4)
                    
                    # Apply risk level rules on normalized percentages (0-100%)
                    risk_level = self.calculate_risk_level(distribution)
                    
                    outputs[clean_idx] = {
                        "dominant_emotion": dominant_emotion,
                        "confidence": confidence,
                        "distribution": distribution,
                        "risk_level": risk_level,
                        "model_version": self.model_version
                    }
            else:
                preds = model.predict(X)
                for idx, clean_idx in enumerate(non_empty_indices):
                    pred_label = str(preds[idx])
                    # Fallback distribution
                    distribution = {c: 100.0 if c == pred_label else 0.0 for c in ["Joy", "Fear", "Anger", "Sadness", "Love", "Surprise"]}
                    risk_level = self.calculate_risk_level(distribution)
                    outputs[clean_idx] = {
                        "dominant_emotion": pred_label,
                        "confidence": 1.0,
                        "distribution": distribution,
                        "risk_level": risk_level,
                        "model_version": self.model_version
                    }
                    
        # Fill in empty text fallbacks
        for i in range(len(texts)):
            if outputs[i] is None:
                outputs[i] = {
                    "dominant_emotion": "Joy",
                    "confidence": 0.0,
                    "distribution": default_distribution.copy(),
                    "risk_level": "LOW",
                    "model_version": self.model_version
                }
                
        return outputs

    def calculate_risk_level(self, distribution):
        """
        Calculates emotional manipulation risk level based on normalized percentage values:
        - HIGH: Fear > 40% OR Fear + Anger > 60%
        - MEDIUM: Not HIGH, but Fear > 20% OR Fear + Anger > 30%
        - LOW: Otherwise
        """
        fear = distribution.get("Fear", 0.0)
        anger = distribution.get("Anger", 0.0)
        
        if fear > 40.0 or (fear + anger) > 60.0:
            return "HIGH"
        elif fear > 20.0 or (fear + anger) > 30.0:
            return "MEDIUM"
        else:
            return "LOW"

    def aggregate_results(self, distributions):
        """
        Averages emotion percentages across a list of article distributions.
        Determines overall dominant emotion and overall risk level.
        Input:
            distributions: List of dicts representing emotion distributions (percentages)
        Returns:
            dict: {
                "overall_emotion": str,
                "emotion_distribution": dict,
                "overall_risk_level": str
            }
        """
        if not distributions:
            return {
                "overall_emotion": "Joy",
                "emotion_distribution": {c: 0.0 for c in ["Joy", "Fear", "Anger", "Sadness", "Love", "Surprise"]},
                "overall_risk_level": "LOW"
            }
            
        N = len(distributions)
        avg_distribution = {c: 0.0 for c in ["Joy", "Fear", "Anger", "Sadness", "Love", "Surprise"]}
        
        for dist in distributions:
            for c in avg_distribution:
                avg_distribution[c] += dist.get(c, 0.0)
                
        for c in avg_distribution:
            avg_distribution[c] = round(avg_distribution[c] / N, 2)
            
        # Overall emotion is the highest average percentage
        overall_emotion = max(avg_distribution, key=avg_distribution.get)
        
        # Calculate overall risk level from the aggregated averages
        overall_risk_level = self.calculate_risk_level(avg_distribution)
        
        return {
            "overall_emotion": overall_emotion,
            "emotion_distribution": avg_distribution,
            "overall_risk_level": overall_risk_level
        }

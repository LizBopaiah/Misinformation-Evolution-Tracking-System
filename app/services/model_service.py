import os
import json
import joblib
from app.services.nlp_service import preprocess_text

class ModelService:
    """Service class for managing model saving, loading, validation, and inference"""
    
    def __init__(self, root_dir=None):
        if root_dir is None:
            self.root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        else:
            self.root_dir = root_dir
            
        self.models_dir = os.path.join(self.root_dir, "models")
        os.makedirs(self.models_dir, exist_ok=True)
        
        # Tasks config
        self.tasks = ["fake_news", "liar", "emotion"]
        
    def get_task_dir(self, task):
        """Returns directory path for a task's models and vectorizers"""
        path = os.path.join(self.models_dir, task)
        os.makedirs(path, exist_ok=True)
        return path

    def save_model_and_vectorizers(self, task, model, tfidf_vec, count_vec, metrics=None):
        """
        Saves the trained model and both fitted vectorizers for a given task.
        """
        task_dir = self.get_task_dir(task)
        
        # Save model
        joblib.dump(model, os.path.join(task_dir, "model.joblib"))
        
        # Save vectorizers separately (as requested by refinements)
        joblib.dump(tfidf_vec, os.path.join(task_dir, "tfidf_vectorizer.joblib"))
        joblib.dump(count_vec, os.path.join(task_dir, "count_vectorizer.joblib"))
        
        # Update performance metrics cache if provided
        if metrics:
            self.update_performance_metrics(task, metrics)

    def update_performance_metrics(self, task, metrics):
        """Updates performance metrics JSON file with model metrics"""
        metrics_path = os.path.join(self.models_dir, "performance_metrics.json")
        data = {}
        if os.path.exists(metrics_path):
            try:
                with open(metrics_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except Exception:
                pass
        data[task] = metrics
        try:
            with open(metrics_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
        except Exception:
            pass

    def check_models_status(self):
        """Checks if required models and vectorizers exist for all tasks"""
        status = {}
        all_online = True
        
        for task in self.tasks:
            task_dir = os.path.join(self.models_dir, task)
            model_exists = os.path.exists(os.path.join(task_dir, "model.joblib"))
            tfidf_exists = os.path.exists(os.path.join(task_dir, "tfidf_vectorizer.joblib"))
            count_exists = os.path.exists(os.path.join(task_dir, "count_vectorizer.joblib"))
            
            task_status = model_exists and tfidf_exists and count_exists
            status[task] = {
                "status": "Online" if task_status else "Offline",
                "model_exists": model_exists,
                "tfidf_exists": tfidf_exists,
                "count_exists": count_exists
            }
            if not task_status:
                all_online = False
                
        status["all_online"] = all_online
        return status

    def load_model_and_vectorizer(self, task):
        """Loads and returns (model, tfidf_vectorizer) for a given task"""
        task_dir = os.path.join(self.models_dir, task)
        model_path = os.path.join(task_dir, "model.joblib")
        tfidf_path = os.path.join(task_dir, "tfidf_vectorizer.joblib")
        
        if not os.path.exists(model_path) or not os.path.exists(tfidf_path):
            raise FileNotFoundError(f"Model or vectorizer for task '{task}' not found. Please train models first.")
            
        model = joblib.load(model_path)
        tfidf = joblib.load(tfidf_path)
        return model, tfidf

    def predict_fake_news(self, text):
        """
        Predicts whether a text is Fake or Real.
        Returns dictionary with class prediction and confidence score.
        """
        cleaned = preprocess_text(text)
        if not cleaned:
            return {"prediction": "Fake", "confidence": 0.5, "processed_text": ""}
            
        model, tfidf = self.load_model_and_vectorizer("fake_news")
        X = tfidf.transform([cleaned])
        pred_idx = int(model.predict(X)[0])
        
        # 1 = Fake, 0 = Real
        label = "Fake" if pred_idx == 1 else "Real"
        
        confidence = 1.0
        if hasattr(model, "predict_proba"):
            probs = model.predict_proba(X)[0]
            confidence = float(probs[pred_idx])
            
        return {
            "prediction": label,
            "confidence": round(confidence, 4),
            "processed_text": cleaned
        }

    def predict_claim_credibility(self, text):
        """
        Predicts claim credibility (LIAR task).
        Labels: True, Partially True, False.
        """
        cleaned = preprocess_text(text)
        if not cleaned:
            return {"prediction": "Partially True", "confidence": 0.33, "processed_text": ""}
            
        model, tfidf = self.load_model_and_vectorizer("liar")
        X = tfidf.transform([cleaned])
        pred_label = str(model.predict(X)[0])
        
        confidence = 1.0
        if hasattr(model, "predict_proba"):
            probs = model.predict_proba(X)[0]
            classes = list(model.classes_)
            if pred_label in classes:
                pred_idx = classes.index(pred_label)
                confidence = float(probs[pred_idx])
                
        return {
            "prediction": pred_label,
            "confidence": round(confidence, 4),
            "processed_text": cleaned
        }

    def predict_emotion(self, text):
        """
        Predicts Emotion of a text.
        Preserves original capitalization (e.g. Joy, Sadness, Anger, Fear, Surprise, Love).
        """
        cleaned = preprocess_text(text)
        if not cleaned:
            return {"prediction": "Neutral", "confidence": 1.0, "processed_text": ""}
            
        model, tfidf = self.load_model_and_vectorizer("emotion")
        X = tfidf.transform([cleaned])
        pred_label = str(model.predict(X)[0])
        
        confidence = 1.0
        if hasattr(model, "predict_proba"):
            probs = model.predict_proba(X)[0]
            classes = list(model.classes_)
            if pred_label in classes:
                pred_idx = classes.index(pred_label)
                confidence = float(probs[pred_idx])
                
        return {
            "prediction": pred_label,
            "confidence": round(confidence, 4),
            "processed_text": cleaned
        }

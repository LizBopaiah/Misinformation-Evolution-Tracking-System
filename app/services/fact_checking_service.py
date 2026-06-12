import os
from flask import current_app
from app.services.model_service import ModelService

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

class FactCheckingService:
    """Service to handle claim verification using a hybrid model-based and Gemini verification approach"""
    
    def __init__(self, gemini_api_key=None):
        self.gemini_api_key = gemini_api_key or os.getenv('GEMINI_API_KEY', '')
        self.model_service = ModelService()
        if GEMINI_AVAILABLE and self.gemini_api_key and not self.gemini_api_key.startswith('AQ.'):
            try:
                genai.configure(api_key=self.gemini_api_key)
            except Exception as e:
                current_app.logger.error(f"Failed to configure Gemini for Fact Checking: {str(e)}")

    def verify_claim(self, claim_text, articles=None):
        """
        Verifies a claim using a hybrid approach:
        1. Primary: Fake News ML model trained in Module 3.
        2. Secondary: Gemini narrative verification against the scraped articles.
        Returns 'MISINFORMATION DETECTED' or 'CORRECT'.
        """
        current_app.logger.info(f"Fact checking claim: '{claim_text}'")
        
        # 1. Primary: Model prediction
        model_verdict = "Real"
        try:
            pred = self.model_service.predict_fake_news(claim_text)
            model_verdict = pred.get("prediction", "Real") # "Fake" or "Real"
            current_app.logger.info(f"Model primary prediction: {model_verdict}")
        except Exception as e:
            current_app.logger.error(f"Primary model verification failed: {str(e)}")
            # Fallback based on keywords if model file fails to load
            model_verdict = "Fake" if any(w in claim_text.lower() for w in ["infertility", "hoax", "conspiracy", "fake"]) else "Real"

        # 2. Secondary: Gemini verification if articles are available
        gemini_verdict = None
        if articles and GEMINI_AVAILABLE and self.gemini_api_key and not self.gemini_api_key.startswith('AQ.'):
            try:
                current_app.logger.info("Attempting secondary verification via Gemini API...")
                combined_articles = "\n\n".join([f"Title: {a.get('title')}\nContent: {a.get('content')}" for a in articles[:3]])
                
                model = genai.GenerativeModel('gemini-1.5-flash')
                prompt = (
                    "Analyze the validity of the following claim based ONLY on the provided articles. "
                    "Determine if the claim is CORRECT (supported or scientifically verified) or "
                    "MISINFORMATION DETECTED (false, misleading, debunked, or medically unfounded). "
                    "Respond with ONLY the verdict, followed by a colon and a brief reason.\n\n"
                    f"Claim: {claim_text}\n\n"
                    f"Articles:\n{combined_articles}"
                )
                response = model.generate_content(prompt)
                if response and response.text:
                    response_text = response.text.strip().upper()
                    current_app.logger.info(f"Gemini secondary response: {response_text}")
                    if "MISINFORMATION DETECTED" in response_text:
                        gemini_verdict = "Fake"
                    elif "CORRECT" in response_text:
                        gemini_verdict = "Real"
            except Exception as e:
                current_app.logger.warning(f"Secondary Gemini verification failed: {str(e)}")

        # 3. Combine Verdicts (hybrid conservative approach: if either flags as Fake/Misinformation, mark it)
        final_verdict = "CORRECT"
        if model_verdict == "Fake" or gemini_verdict == "Fake":
            final_verdict = "MISINFORMATION DETECTED"
        elif model_verdict == "Real" or gemini_verdict == "Real":
            # If both are Real, or one is Real and the other is unavailable
            final_verdict = "CORRECT"

        current_app.logger.info(f"Combined hybrid verification verdict: {final_verdict}")
        return final_verdict

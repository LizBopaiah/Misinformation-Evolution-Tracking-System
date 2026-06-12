import os
import nltk
from flask import current_app

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

class SummarizationService:
    """Service to generate a unified narrative summary of articles using Gemini or local extractive fallbacks"""

    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv('GEMINI_API_KEY', '')
        if GEMINI_AVAILABLE and self.api_key and not self.api_key.startswith('AQ.'):
            try:
                genai.configure(api_key=self.api_key)
            except Exception as e:
                current_app.logger.error(f"Failed to configure Gemini API: {str(e)}")

    def generate_summary(self, articles, max_sentences=4):
        """
        Generates a summary of list of articles.
        Tries Gemini API first. Falls back to local extractive summarizer if unconfigured or fails.
        """
        if not articles:
            return "No articles collected to summarize."

        # Combine text of all articles
        combined_text = "\n\n".join([f"Title: {a.get('title')}\nContent: {a.get('content')}" for a in articles])

        # 1. Try Gemini API
        if GEMINI_AVAILABLE and self.api_key and not self.api_key.startswith('AQ.'):
            try:
                current_app.logger.info("Attempting summarization via Gemini API...")
                model = genai.GenerativeModel('gemini-1.5-flash')
                prompt = (
                    "You are a professional misinformation researcher. Review the following articles "
                    "collected on a search topic. Write a unified, objective narrative summary "
                    "identifying the core claims, common themes, and discrepancies found across these sources. "
                    "Keep the summary concise, objective, and under 150 words.\n\n"
                    f"{combined_text}"
                )
                response = model.generate_content(prompt)
                if response and response.text:
                    current_app.logger.info("Successfully summarized via Gemini API")
                    return response.text.strip()
            except Exception as e:
                current_app.logger.warning(f"Gemini API summarization failed: {str(e)}. Falling back to local summarizer.")

        # 2. Local Fallback Extractive Summarization
        current_app.logger.info("Using local extractive summarizer fallback...")
        return self._local_extractive_summary(combined_text, max_sentences)

    def _local_extractive_summary(self, text, max_sentences=4):
        """
        Generates a summary using a native word-frequency sentence ranking algorithm.
        """
        if not text:
            return ""

        try:
            # Auto-download tokenizer files if missing (handles newer NLTK and Python versions)
            for resource in ['tokenizers/punkt', 'tokenizers/punkt_tab']:
                try:
                    nltk.data.find(resource)
                except LookupError:
                    try:
                        nltk.download(resource.split('/')[-1], quiet=True)
                    except Exception:
                        pass

            # Tokenize into sentences
            sentences = nltk.sent_tokenize(text)
            if len(sentences) <= max_sentences:
                return text

            # Tokenize into words, remove punctuation, lowercase
            words = nltk.word_tokenize(text.lower())
            
            # Load stopwords from nltk
            try:
                from nltk.corpus import stopwords
                stop_words = set(stopwords.words('english'))
            except Exception:
                # Fallback if stopwords resource is missing
                stop_words = {'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you', "you're", "you've", "you'll", "you'd", 'your', 'yours', 'yourself', 'yourselves', 'he', 'him', 'his', 'himself', 'she', "she's", 'her', 'hers', 'herself', 'it', "it's", 'its', 'itself', 'they', 'them', 'their', 'theirs', 'themselves', 'what', 'which', 'who', 'whom', 'this', 'that', "that'll", 'these', 'those', 'am', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'having', 'do', 'does', 'did', 'doing', 'a', 'an', 'the', 'and', 'but', 'if', 'or', 'because', 'as', 'until', 'while', 'of', 'at', 'by', 'for', 'with', 'about', 'against', 'between', 'into', 'through', 'during', 'before', 'after', 'above', 'below', 'to', 'from', 'up', 'down', 'in', 'out', 'on', 'off', 'over', 'under', 'again', 'further', 'then', 'once', 'here', 'there', 'when', 'where', 'why', 'how', 'all', 'any', 'both', 'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 's', 't', 'can', 'will', 'just', 'don', "don't", 'should', "should've", 'now', 'd', 'll', 'm', 'o', 're', 've', 'y', 'ain', 'aren', "aren't", 'couldn', "couldn't", 'didn', "didn't", 'doesn', "doesn't", 'hadn', "hadn't", 'hasn', "hasn't", 'haven', "haven't", 'isn', "isn't", 'ma', 'mightn', "mightn't", 'mustn', "mustn't", 'needn', "needn't", 'shan', "shan't", 'shouldn', "shouldn't", 'wasn', "wasn't", 'weren', "weren't", 'won', "won't", 'wouldn', "wouldn't"}

            # Filter out non-alphabetic tokens and stopwords
            word_frequencies = {}
            for word in words:
                if word.isalpha() and word not in stop_words:
                    word_frequencies[word] = word_frequencies.get(word, 0) + 1

            if not word_frequencies:
                # If no words counted, just return the first few sentences
                return " ".join(sentences[:max_sentences])

            # Normalize word frequencies by maximum frequency
            max_freq = max(word_frequencies.values())
            for word in word_frequencies:
                word_frequencies[word] = word_frequencies[word] / max_freq

            # Score sentences based on word frequencies
            sentence_scores = {}
            for i, sent in enumerate(sentences):
                # Skip header/boilerplate looking sentences
                if len(sent.strip()) < 15 or "title:" in sent.lower() or "content:" in sent.lower():
                    continue
                score = 0
                sent_words = nltk.word_tokenize(sent.lower())
                for word in sent_words:
                    if word in word_frequencies:
                        score += word_frequencies[word]
                sentence_scores[i] = score

            if not sentence_scores:
                return " ".join(sentences[:max_sentences])

            # Get top N sentence indices
            sorted_indices = sorted(sentence_scores, key=sentence_scores.get, reverse=True)[:max_sentences]
            # Sort chronologically to preserve reading flow
            sorted_indices.sort()

            summary_sentences = [sentences[idx].strip() for idx in sorted_indices]
            return " ".join(summary_sentences)
        except Exception as e:
            current_app.logger.error(f"Error in local extractive summarizer: {str(e)}")
            return "Failed to generate local summary fallback."

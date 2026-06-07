import os
import re
import string
import sys
import subprocess
import nltk
import spacy
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer

# Global variables
nlp_model = None
stop_words = set()

def initialize_nlp():
    """Download NLTK resources and load/download spaCy model if missing"""
    global nlp_model, stop_words
    
    # 1. Enforce NLTK downloads
    for resource in ["stopwords", "punkt"]:
        try:
            if resource == "stopwords":
                nltk.data.find("corpora/stopwords")
            else:
                nltk.data.find("tokenizers/punkt")
        except LookupError:
            try:
                nltk.download(resource, quiet=True)
            except Exception:
                pass
            
    try:
        from nltk.corpus import stopwords
        stop_words = set(stopwords.words('english'))
    except Exception:
        stop_words = set()
    
    # 2. Enforce spaCy model download
    try:
        # Load small english model, disable parser and NER for speed
        nlp_model = spacy.load("en_core_web_sm", disable=["parser", "ner"])
    except OSError:
        # Try downloading it
        subprocess.run([sys.executable, "-m", "spacy", "download", "en_core_web_sm"])
        try:
            nlp_model = spacy.load("en_core_web_sm", disable=["parser", "ner"])
        except Exception as e:
            print(f"Failed to load spaCy model: {str(e)}")
            nlp_model = None

# Run initialization immediately on import
initialize_nlp()

def preprocess_text(text):
    """
    Reusable text preprocessing pipeline.
    Steps:
    1. Lowercase conversion
    2. URL removal
    3. HTML tag removal
    4. Punctuation removal
    5. Number normalization/removal
    6. Stopword removal
    7. Lemmatization (via spaCy)
    8. Whitespace cleanup
    """
    if not isinstance(text, str):
        return ""
        
    # 1. Lowercase conversion
    text = text.lower()
    
    # 2. URL removal
    text = re.sub(r'https?://\S+|www\.\S+', '', text)
    
    # 3. HTML removal
    text = re.sub(r'<[^>]*>', '', text)
    
    # 4. Punctuation removal and 5. Number removal
    # Replace punctuation and digits with spaces to keep token boundaries
    translator = str.maketrans(
        string.punctuation + string.digits,
        ' ' * (len(string.punctuation) + len(string.digits))
    )
    text = text.translate(translator)
    
    # 6. Whitespace cleanup before lemma/stopword filter
    text = " ".join(text.split())
    
    if not text:
        return ""
        
    # 7. Lemmatization and 8. Stopword removal (using spaCy if available)
    if nlp_model:
        doc = nlp_model(text)
        cleaned_tokens = [
            token.lemma_ for token in doc 
            if token.text not in stop_words and len(token.lemma_.strip()) > 1
        ]
        return " ".join(cleaned_tokens)
    else:
        # Fallback if spaCy is not loaded: basic split and NLTK stopword filter
        tokens = text.split()
        cleaned = [t for t in tokens if t not in stop_words and len(t) > 1]
        return " ".join(cleaned)

def preprocess_texts_batch(texts):
    """
    Batched version of preprocess_text for processing large lists of texts efficiently.
    Uses nlp_model.pipe() to run lemmatization in batch.
    """
    cleaned_texts = []
    
    # Pre-clean texts using fast regex/translation before feeding to spaCy
    pre_cleaned = []
    for text in texts:
        if not isinstance(text, str):
            pre_cleaned.append("")
            continue
        text = text.lower()
        text = re.sub(r'https?://\S+|www\.\S+', '', text)
        text = re.sub(r'<[^>]*>', '', text)
        translator = str.maketrans(
            string.punctuation + string.digits,
            ' ' * (len(string.punctuation) + len(string.digits))
        )
        text = text.translate(translator)
        text = " ".join(text.split())
        pre_cleaned.append(text)

    if nlp_model:
        docs = nlp_model.pipe(pre_cleaned, batch_size=2000)
        for doc in docs:
            cleaned_tokens = [
                token.lemma_ for token in doc 
                if token.text not in stop_words and len(token.lemma_.strip()) > 1
            ]
            cleaned_texts.append(" ".join(cleaned_tokens))
    else:
        for text in pre_cleaned:
            tokens = text.split()
            cleaned = [t for t in tokens if t not in stop_words and len(t) > 1]
            cleaned_texts.append(" ".join(cleaned))
            
    return cleaned_texts


import os
import sys
import json
import numpy as np
import pandas as pd
import joblib

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import MultinomialNB
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, classification_report, confusion_matrix

from app.services.nlp_service import preprocess_texts_batch
from app.services.dataset_service import DatasetService
from app.services.model_service import ModelService

def plot_confusion_matrix(y_true, y_pred, classes, title, filepath):
    """Generates and saves a confusion matrix heatmap as PNG"""
    cm = confusion_matrix(y_true, y_pred, labels=classes)
    plt.figure(figsize=(8, 6))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', xticklabels=classes, yticklabels=classes)
    plt.title(title)
    plt.ylabel('True Label')
    plt.xlabel('Predicted Label')
    plt.tight_layout()
    plt.savefig(filepath)
    plt.close()

def main():
    print("Starting Model Training Pipeline for MET System...")
    
    # Initialize services
    dataset_service = DatasetService()
    model_service = ModelService()
    
    # Create reports directory
    reports_dir = os.path.join(model_service.root_dir, "reports")
    os.makedirs(reports_dir, exist_ok=True)
    
    # Define tasks to process
    tasks_config = {
        "fake_news": {
            "loader": dataset_service.load_fake_news_df,
            "classes": ["Real", "Fake"], # 0 = Real, 1 = Fake
            "class_mapping": {0: "Real", 1: "Fake"}
        },
        "liar": {
            "loader": dataset_service.load_liar_df,
            "classes": ["True", "Partially True", "False"],
            "class_mapping": None
        },
        "emotion": {
            "loader": dataset_service.load_emotion_df,
            "classes": ["Sadness", "Anger", "Joy", "Fear", "Surprise", "Love"],
            "class_mapping": None
        }
    }
    
    performance_metrics = {}
    
    for task_name, config in tasks_config.items():
        print(f"\n==========================================")
        print(f"Processing Task: {task_name.upper()}")
        print(f"==========================================")
        
        # Load dataset
        print("Loading dataset...")
        df = config["loader"]()
        print(f"Loaded {len(df)} rows.")
        
        # Preprocess text
        print("Preprocessing texts in batch (this may take a minute)...")
        texts_cleaned = preprocess_texts_batch(df['text'].tolist())
        df['cleaned_text'] = texts_cleaned
        
        # Filter out empty or null texts
        df = df[df['cleaned_text'].str.strip() != ""]
        print(f"After cleaning and removing empty rows: {len(df)} rows.")
        
        X = df['cleaned_text']
        y = df['label']
        
        # Stratified train-test split (80% train, 20% test)
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        print(f"Train size: {len(X_train)}, Test size: {len(X_test)}")
        
        # Fit both vectorizers (TF-IDF and CountVectorizer) separately
        print("Fitting TF-IDF Vectorizer and CountVectorizer...")
        tfidf_vec = TfidfVectorizer(max_features=5000, ngram_range=(1, 2))
        count_vec = CountVectorizer(max_features=5000, ngram_range=(1, 2))
        
        X_train_tfidf = tfidf_vec.fit_transform(X_train)
        X_test_tfidf = tfidf_vec.transform(X_test)
        
        count_vec.fit(X_train) # Fit count vectorizer on training text for persistence
        
        # Train & Evaluate models
        models = {
            "logistic_regression": LogisticRegression(max_iter=1000, random_state=42),
            "naive_bayes": MultinomialNB()
        }
        
        task_metrics = {}
        best_model_name = None
        best_f1 = -1
        best_model_obj = None
        best_preds = None
        
        for name, clf in models.items():
            print(f"Training {name}...")
            clf.fit(X_train_tfidf, y_train)
            
            # Predict
            y_pred = clf.predict(X_test_tfidf)
            
            # Compute metrics
            acc = accuracy_score(y_test, y_pred)
            precision, recall, f1, _ = precision_recall_fscore_support(y_test, y_pred, average='weighted')
            
            # Detailed classification report
            report_dict = classification_report(y_test, y_pred, output_dict=True)
            report_text = classification_report(y_test, y_pred)
            
            print(f"[{name}] Acc: {acc:.4f}, Prec: {precision:.4f}, Rec: {recall:.4f}, F1: {f1:.4f}")
            
            task_metrics[name] = {
                "accuracy": round(acc, 4),
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1_score": round(f1, 4),
                "classification_report_dict": report_dict,
                "classification_report_text": report_text
            }
            
            # Compare F1 score to pick best model
            if f1 > best_f1:
                best_f1 = f1
                best_model_name = name
                best_model_obj = clf
                best_preds = y_pred
                
        print(f"Best model for {task_name}: {best_model_name}")
        task_metrics["best_model"] = best_model_name
        performance_metrics[task_name] = task_metrics
        
        # Save best model and vectorizers
        print("Saving best model and vectorizers...")
        model_service.save_model_and_vectorizers(
            task=task_name,
            model=best_model_obj,
            tfidf_vec=tfidf_vec,
            count_vec=count_vec,
            metrics=task_metrics[best_model_name]
        )
        
        # Plot and save confusion matrix for best classifier
        classes = config["classes"]
        y_test_mapped = y_test
        best_preds_mapped = best_preds
        if config["class_mapping"]:
            y_test_mapped = [config["class_mapping"][val] for val in y_test]
            best_preds_mapped = [config["class_mapping"][val] for val in best_preds]
            
        cm_filepath = os.path.join(reports_dir, f"{task_name}_confusion_matrix.png")
        print(f"Saving confusion matrix plot to {cm_filepath}...")
        plot_confusion_matrix(
            y_true=y_test_mapped,
            y_pred=best_preds_mapped,
            classes=classes,
            title=f"{task_name.replace('_', ' ').title()} - {best_model_name.replace('_', ' ').title()} Confusion Matrix",
            filepath=cm_filepath
        )

    # Save overall performance metrics json file
    metrics_path = os.path.join(model_service.models_dir, "performance_metrics.json")
    print(f"Saving detailed performance metrics to {metrics_path}...")
    with open(metrics_path, 'w', encoding='utf-8') as f:
        json.dump(performance_metrics, f, indent=4)
        
    print("\nTraining completed successfully!")

if __name__ == "__main__":
    main()

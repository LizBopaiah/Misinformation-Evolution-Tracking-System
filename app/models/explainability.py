from app.extensions import db
import json
from datetime import datetime, timezone

class ExplainabilityResult(db.Model):
    """Immutable Explainable AI (XAI) and Model Governance snapshot records"""
    __tablename__ = 'explainability_results'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    search_id = db.Column(db.Integer, db.ForeignKey('search_history.id', ondelete='CASCADE'), nullable=True, index=True)
    article_id = db.Column(db.Integer, db.ForeignKey('articles.id', ondelete='CASCADE'), nullable=True, index=True)
    
    explanation_type = db.Column(db.String(64), nullable=False) # fact_audit, sentiment, evolution, comparison, credibility, search, report
    prediction = db.Column(db.Text, nullable=True)
    confidence = db.Column(db.Float, nullable=True)
    confidence_level = db.Column(db.String(32), nullable=True) # Very Low, Low, Medium, High, Very High
    
    explanation_json = db.Column(db.Text, nullable=True)
    evidence_for_json = db.Column(db.Text, nullable=True)
    evidence_against_json = db.Column(db.Text, nullable=True)
    feature_importance_json = db.Column(db.Text, nullable=True)
    
    model_name = db.Column(db.String(128), nullable=True)
    model_version = db.Column(db.String(64), nullable=True)
    vectorizer_version = db.Column(db.String(64), nullable=True)
    pipeline_version = db.Column(db.String(64), nullable=True)
    inference_method = db.Column(db.String(64), nullable=True) # model, fallback
    fallback_used = db.Column(db.Boolean, default=False, nullable=False)
    processing_time_ms = db.Column(db.Integer, nullable=True)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), nullable=False)

    @property
    def explanation(self):
        if self.explanation_json:
            try:
                return json.loads(self.explanation_json)
            except ValueError:
                return {}
        return {}

    @explanation.setter
    def explanation(self, val):
        self.explanation_json = json.dumps(val)

    @property
    def evidence_for(self):
        if self.evidence_for_json:
            try:
                return json.loads(self.evidence_for_json)
            except ValueError:
                return []
        return []

    @evidence_for.setter
    def evidence_for(self, val):
        self.evidence_for_json = json.dumps(val)

    @property
    def evidence_against(self):
        if self.evidence_against_json:
            try:
                return json.loads(self.evidence_against_json)
            except ValueError:
                return []
        return []

    @evidence_against.setter
    def evidence_against(self, val):
        self.evidence_against_json = json.dumps(val)

    @property
    def feature_importance(self):
        if self.feature_importance_json:
            try:
                return json.loads(self.feature_importance_json)
            except ValueError:
                return []
        return []

    @feature_importance.setter
    def feature_importance(self, val):
        self.feature_importance_json = json.dumps(val)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'search_id': self.search_id,
            'article_id': self.article_id,
            'explanation_type': self.explanation_type,
            'prediction': self.prediction,
            'confidence': self.confidence,
            'confidence_level': self.confidence_level,
            'explanation': self.explanation,
            'evidence_for': self.evidence_for,
            'evidence_against': self.evidence_against,
            'feature_importance': self.feature_importance,
            'model_name': self.model_name,
            'model_version': self.model_version,
            'vectorizer_version': self.vectorizer_version,
            'pipeline_version': self.pipeline_version,
            'inference_method': self.inference_method,
            'fallback_used': self.fallback_used,
            'processing_time_ms': self.processing_time_ms,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

from app.extensions import db
import json

class SentimentResult(db.Model):
    """Sentiment Analysis Results table associated with articles"""
    __tablename__ = 'sentiment_results'

    id = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(db.Integer, db.ForeignKey('articles.id', ondelete='CASCADE'), nullable=False, index=True)
    search_id = db.Column(db.Integer, db.ForeignKey('search_history.id', ondelete='CASCADE'), nullable=True, index=True)
    dominant_emotion = db.Column(db.String(64), nullable=True)
    confidence = db.Column(db.Float, nullable=True)
    risk_level = db.Column(db.String(32), nullable=True)
    model_version = db.Column(db.String(32), nullable=True)
    
    # Deprecated/Legacy columns preserved for database integrity
    score = db.Column(db.Float, nullable=True)  # Legacy Sentiment score
    sentiment_label = db.Column(db.String(64), nullable=True)  # Legacy label
    
    emotions_json = db.Column(db.Text, nullable=True)  # JSON-serialized emotional breakdown
    analyzed_at = db.Column(db.DateTime, default=db.func.now(), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.now(), nullable=False)
    updated_at = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now(), nullable=False)

    @property
    def emotions(self):
        """Legacy getter for emotions dict"""
        if self.emotions_json:
            try:
                return json.loads(self.emotions_json)
            except ValueError:
                return {}
        return {}

    @emotions.setter
    def emotions(self, val):
        """Legacy setter for emotions dict serializing to JSON"""
        self.emotions_json = json.dumps(val)

    @property
    def emotion_distribution(self):
        """Getter for deserialized emotions distribution dict"""
        return self.emotions

    @emotion_distribution.setter
    def emotion_distribution(self, val):
        """Setter for emotions distribution dict serializing to JSON"""
        self.emotions = val

    def to_dict(self):
        """Serialize sentiment result object"""
        return {
            'id': self.id,
            'article_id': self.article_id,
            'search_id': self.search_id,
            'dominant_emotion': self.dominant_emotion,
            'confidence': self.confidence,
            'emotion_distribution': self.emotion_distribution,
            'risk_level': self.risk_level,
            'model_version': self.model_version,
            'score': self.score,
            'sentiment_label': self.sentiment_label,
            'analyzed_at': self.analyzed_at.isoformat() if self.analyzed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


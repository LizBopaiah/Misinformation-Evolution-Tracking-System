from app.extensions import db
import json

class SentimentResult(db.Model):
    """Sentiment Analysis Results table associated with articles"""
    __tablename__ = 'sentiment_results'

    id = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(db.Integer, db.ForeignKey('articles.id', ondelete='CASCADE'), nullable=False, index=True)
    score = db.Column(db.Float, nullable=False)  # Sentiment score (-1.0 to 1.0)
    sentiment_label = db.Column(db.String(64), nullable=False)  # e.g., 'Positive', 'Negative', 'Neutral'
    emotions_json = db.Column(db.Text, nullable=True)  # JSON-serialized emotional breakdown (e.g., anger, joy, fear)
    analyzed_at = db.Column(db.DateTime, default=db.func.now(), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.now(), nullable=False)
    updated_at = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now(), nullable=False)

    @property
    def emotions(self):
        """Getter for deserialized emotions dict"""
        if self.emotions_json:
            try:
                return json.loads(self.emotions_json)
            except ValueError:
                return {}
        return {}

    @emotions.setter
    def emotions(self, val):
        """Setter for emotions dict serializing to JSON"""
        self.emotions_json = json.dumps(val)

    def to_dict(self):
        """Serialize sentiment result object"""
        return {
            'id': self.id,
            'article_id': self.article_id,
            'score': self.score,
            'sentiment_label': self.sentiment_label,
            'emotions': self.emotions,
            'analyzed_at': self.analyzed_at.isoformat() if self.analyzed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

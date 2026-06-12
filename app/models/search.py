from app.extensions import db
import json

class SearchHistory(db.Model):
    """Tracks search queries and processing states per user"""
    __tablename__ = 'search_history'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    query = db.Column(db.String(256), nullable=False)
    summary = db.Column(db.Text, nullable=True)
    search_type = db.Column(db.String(50), nullable=True)  # e.g., 'claim', 'article', 'general'
    status = db.Column(db.String(50), nullable=True)       # e.g., 'completed', 'failed', 'pending'
    fact_check_result = db.Column(db.String(64), nullable=True)
    articles_collected = db.Column(db.Integer, default=0, nullable=True)
    processing_time = db.Column(db.Float, nullable=True)
    search_status = db.Column(db.String(50), nullable=True)  # e.g., 'completed', 'failed', 'pending'
    
    # Module 5A Aggregate Sentiment Cache fields
    overall_emotion = db.Column(db.String(64), nullable=True)
    overall_risk_level = db.Column(db.String(32), nullable=True)
    aggregated_sentiment_json = db.Column(db.Text, nullable=True)
    sentiment_analyzed_at = db.Column(db.DateTime, nullable=True)
    
    created_at = db.Column(db.DateTime, default=db.func.now(), nullable=False)
    updated_at = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now(), nullable=False)

    @property
    def aggregated_emotion_distribution(self):
        """Getter for deserialized aggregate emotion distribution dict"""
        if self.aggregated_sentiment_json:
            try:
                return json.loads(self.aggregated_sentiment_json)
            except ValueError:
                return {}
        return {}

    @aggregated_emotion_distribution.setter
    def aggregated_emotion_distribution(self, val):
        """Setter for aggregate emotion distribution dict serializing to JSON"""
        self.aggregated_sentiment_json = json.dumps(val)

    def to_dict(self):
        """Serialize search history object"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'query': self.query,
            'summary': self.summary,
            'search_type': self.search_type,
            'status': self.status,
            'fact_check_result': self.fact_check_result,
            'articles_collected': self.articles_collected,
            'processing_time': self.processing_time,
            'search_status': self.search_status,
            'overall_emotion': self.overall_emotion,
            'overall_risk_level': self.overall_risk_level,
            'aggregated_emotion_distribution': self.aggregated_emotion_distribution,
            'sentiment_analyzed_at': self.sentiment_analyzed_at.isoformat() if self.sentiment_analyzed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }



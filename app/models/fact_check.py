from app.extensions import db

class FactCheckResult(db.Model):
    """Fact Check Results table associated with claims made in articles"""
    __tablename__ = 'fact_check_results'

    id = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(db.Integer, db.ForeignKey('articles.id', ondelete='CASCADE'), nullable=False, index=True)
    claim = db.Column(db.Text, nullable=False)
    truth_rating = db.Column(db.String(64), nullable=False)  # e.g., 'True', 'False', 'Misleading'
    confidence_score = db.Column(db.Float, nullable=False)
    source = db.Column(db.String(120), nullable=True)  # e.g., 'PolitiFact', 'Snopes'
    checked_at = db.Column(db.DateTime, default=db.func.now(), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.now(), nullable=False)
    updated_at = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now(), nullable=False)

    def to_dict(self):
        """Serialize fact check result object"""
        return {
            'id': self.id,
            'article_id': self.article_id,
            'claim': self.claim,
            'truth_rating': self.truth_rating,
            'confidence_score': self.confidence_score,
            'source': self.source,
            'checked_at': self.checked_at.isoformat() if self.checked_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

from app.extensions import db

class SearchHistory(db.Model):
    """Tracks search queries and processing states per user"""
    __tablename__ = 'search_history'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    query = db.Column(db.String(256), nullable=False)
    summary = db.Column(db.Text, nullable=True)
    search_type = db.Column(db.String(50), nullable=True)  # e.g., 'claim', 'article', 'general'
    status = db.Column(db.String(50), nullable=True)       # e.g., 'completed', 'failed', 'pending'
    created_at = db.Column(db.DateTime, default=db.func.now(), nullable=False)
    updated_at = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now(), nullable=False)

    def to_dict(self):
        """Serialize search history object"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'query': self.query,
            'summary': self.summary,
            'search_type': self.search_type,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

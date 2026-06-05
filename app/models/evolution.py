from app.extensions import db

class EvolutionResult(db.Model):
    """Tracks lineage, similarity changes, and text mutations over time"""
    __tablename__ = 'evolution_results'

    id = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(db.Integer, db.ForeignKey('articles.id', ondelete='CASCADE'), nullable=False, index=True)
    lineage_id = db.Column(db.String(64), nullable=False, index=True)  # Links articles belonging to same chain
    parent_id = db.Column(db.Integer, db.ForeignKey('articles.id', ondelete='SET NULL'), nullable=True)  # Parent node in mutation tree
    mutation_type = db.Column(db.String(64), nullable=True)  # e.g., 'rephrase', 'add_context', 'exaggeration'
    similarity_score = db.Column(db.Float, nullable=False)
    tracked_at = db.Column(db.DateTime, default=db.func.now(), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.now(), nullable=False)
    updated_at = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now(), nullable=False)

    def to_dict(self):
        """Serialize evolution result object"""
        return {
            'id': self.id,
            'article_id': self.article_id,
            'lineage_id': self.lineage_id,
            'parent_id': self.parent_id,
            'mutation_type': self.mutation_type,
            'similarity_score': self.similarity_score,
            'tracked_at': self.tracked_at.isoformat() if self.tracked_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

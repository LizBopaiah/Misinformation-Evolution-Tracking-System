from app.extensions import db
import json

class EvolutionResult(db.Model):
    """Stores the aggregated temporal evolution analysis for a completed search query"""
    __tablename__ = 'evolution_results'

    id = db.Column(db.Integer, primary_key=True)
    search_id = db.Column(db.Integer, db.ForeignKey('search_history.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    baseline_article_id = db.Column(db.Integer, db.ForeignKey('articles.id', ondelete='CASCADE'), nullable=False, index=True)
    narrative_drift_score = db.Column(db.Float, nullable=False)
    total_variants_detected = db.Column(db.Integer, nullable=False)
    dominant_narrative = db.Column(db.String(256), nullable=True)
    evolution_summary = db.Column(db.Text, nullable=True)
    mutation_points_json = db.Column(db.Text, nullable=True)
    timeline_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=db.func.now(), nullable=False)

    # Define relationships with explicit backref/foreign keys matching Article
    search_history = db.relationship('SearchHistory', backref=db.backref('evolution_results', lazy=True, cascade="all, delete-orphan"))
    user = db.relationship('User', backref=db.backref('evolution_results', lazy=True, cascade="all, delete-orphan"))
    baseline_article = db.relationship('Article', backref=db.backref('baseline_evolutions', lazy=True, overlaps="article,evolutions"), foreign_keys=[baseline_article_id], overlaps="article,evolutions")

    @property
    def mutation_points(self):
        """Getter for deserialized mutation points JSON list"""
        if self.mutation_points_json:
            try:
                return json.loads(self.mutation_points_json)
            except ValueError:
                return []
        return []

    @mutation_points.setter
    def mutation_points(self, val):
        """Setter for mutation points JSON serialization"""
        self.mutation_points_json = json.dumps(val)

    @property
    def timeline(self):
        """Getter for deserialized timeline JSON list"""
        if self.timeline_json:
            try:
                return json.loads(self.timeline_json)
            except ValueError:
                return []
        return []

    @timeline.setter
    def timeline(self, val):
        """Setter for timeline JSON serialization"""
        self.timeline_json = json.dumps(val)

    def to_dict(self):
        """Serialize evolution result object"""
        return {
            'id': self.id,
            'search_id': self.search_id,
            'user_id': self.user_id,
            'baseline_article_id': self.baseline_article_id,
            'narrative_drift_score': self.narrative_drift_score,
            'total_variants_detected': self.total_variants_detected,
            'dominant_narrative': self.dominant_narrative,
            'evolution_summary': self.evolution_summary,
            'mutation_points': self.mutation_points,
            'timeline': self.timeline,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


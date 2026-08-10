from app.extensions import db

class SourceCredibility(db.Model):
    """Stores the aggregated source credibility and safety scores per domain"""
    __tablename__ = 'source_credibility'

    id = db.Column(db.Integer, primary_key=True)
    domain = db.Column(db.String(120), unique=True, nullable=False, index=True)
    credibility_score = db.Column(db.Float, nullable=False, default=70.0)
    letter_grade = db.Column(db.String(10), nullable=False, default='C')
    historical_misinformation_rate = db.Column(db.Float, default=0.0, nullable=False)
    fact_check_agreement_rate = db.Column(db.Float, default=0.0, nullable=False)
    source_consistency_score = db.Column(db.Float, default=100.0, nullable=False)
    domain_reputation_score = db.Column(db.Float, default=70.0, nullable=False)
    security_score = db.Column(db.Float, default=100.0, nullable=False)
    freshness_score = db.Column(db.Float, default=100.0, nullable=False)
    citation_score = db.Column(db.Float, default=100.0, nullable=False)
    analysis_count = db.Column(db.Integer, default=0, nullable=False)
    
    created_at = db.Column(db.DateTime, default=db.func.now(), nullable=False)
    updated_at = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now(), nullable=False)

    # Relationships
    history = db.relationship('SourceCredibilityHistory', backref='source_credibility', lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        """Serialize source credibility object"""
        return {
            'id': self.id,
            'domain': self.domain,
            'credibility_score': self.credibility_score,
            'letter_grade': self.letter_grade,
            'historical_misinformation_rate': self.historical_misinformation_rate,
            'fact_check_agreement_rate': self.fact_check_agreement_rate,
            'source_consistency_score': self.source_consistency_score,
            'domain_reputation_score': self.domain_reputation_score,
            'security_score': self.security_score,
            'freshness_score': self.freshness_score,
            'citation_score': self.citation_score,
            'analysis_count': self.analysis_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class SourceCredibilityHistory(db.Model):
    """Tracks historical progression of credibility audits for a domain"""
    __tablename__ = 'source_credibility_history'

    id = db.Column(db.Integer, primary_key=True)
    source_credibility_id = db.Column(db.Integer, db.ForeignKey('source_credibility.id', ondelete='CASCADE'), nullable=False, index=True)
    score = db.Column(db.Float, nullable=False)
    letter_grade = db.Column(db.String(10), nullable=False)
    misinformation_rate = db.Column(db.Float, nullable=False)
    fact_check_agreement = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.now(), nullable=False)

    def to_dict(self):
        """Serialize history entry"""
        return {
            'id': self.id,
            'source_credibility_id': self.source_credibility_id,
            'score': self.score,
            'letter_grade': self.letter_grade,
            'misinformation_rate': self.misinformation_rate,
            'fact_check_agreement': self.fact_check_agreement,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

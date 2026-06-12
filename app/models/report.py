from app.extensions import db
import json
import hashlib

class ResearchReport(db.Model):
    """Stores a finalized historical comparison snapshot of multiple searches"""
    __tablename__ = 'research_reports'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    report_name = db.Column(db.String(256), nullable=False)
    search_ids_json = db.Column(db.Text, nullable=False)
    
    # MD5/SHA256 hash of sorted search IDs to cache comparison outputs uniquely
    comparison_hash = db.Column(db.String(64), unique=True, nullable=False, index=True)
    summary = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=db.func.now(), nullable=False)

    # Relationships
    user = db.relationship('User', backref=db.backref('research_reports', lazy=True, cascade="all, delete-orphan"))
    comparison_results = db.relationship('ComparisonResult', backref='report', lazy=True, cascade="all, delete-orphan")

    @property
    def search_ids(self):
        """Getter for deserialized search IDs list"""
        if self.search_ids_json:
            try:
                return json.loads(self.search_ids_json)
            except ValueError:
                return []
        return []

    @search_ids.setter
    def search_ids(self, val):
        """Setter for search IDs list serializing to JSON"""
        sorted_val = sorted(list(set(val)))
        self.search_ids_json = json.dumps(sorted_val)
        
        # Automatically generate unique comparison hash based on sorted IDs
        ids_str = ",".join(map(str, sorted_val))
        self.comparison_hash = hashlib.sha256(ids_str.encode()).hexdigest()

    def to_dict(self):
        """Serialize ResearchReport object"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'report_name': self.report_name,
            'search_ids': self.search_ids,
            'comparison_hash': self.comparison_hash,
            'summary': self.summary,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class ComparisonResult(db.Model):
    """Stores detailed statistical metrics comparing research topics"""
    __tablename__ = 'comparison_results'

    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey('research_reports.id', ondelete='CASCADE'), nullable=False, index=True)
    shared_themes_json = db.Column(db.Text, nullable=True)
    shared_emotions_json = db.Column(db.Text, nullable=True)
    shared_claims_json = db.Column(db.Text, nullable=True)
    similarity_score = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.now(), nullable=False)

    @property
    def shared_themes(self):
        """Getter for deserialized themes list"""
        if self.shared_themes_json:
            try:
                return json.loads(self.shared_themes_json)
            except ValueError:
                return []
        return []

    @shared_themes.setter
    def shared_themes(self, val):
        """Setter for themes list serializing to JSON"""
        self.shared_themes_json = json.dumps(val)

    @property
    def shared_emotions(self):
        """Getter for deserialized emotions dict"""
        if self.shared_emotions_json:
            try:
                return json.loads(self.shared_emotions_json)
            except ValueError:
                return {}
        return {}

    @shared_emotions.setter
    def shared_emotions(self, val):
        """Setter for emotions dict serializing to JSON"""
        self.shared_emotions_json = json.dumps(val)

    @property
    def shared_claims(self):
        """Getter for deserialized article narrative pairs list"""
        if self.shared_claims_json:
            try:
                return json.loads(self.shared_claims_json)
            except ValueError:
                return []
        return []

    @shared_claims.setter
    def shared_claims(self, val):
        """Setter for article narrative pairs list serializing to JSON"""
        self.shared_claims_json = json.dumps(val)

    def to_dict(self):
        """Serialize ComparisonResult object"""
        return {
            'id': self.id,
            'report_id': self.report_id,
            'shared_themes': self.shared_themes,
            'shared_emotions': self.shared_emotions,
            'shared_claims': self.shared_claims,
            'similarity_score': self.similarity_score,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

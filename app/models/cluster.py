from app.extensions import db
import json

class NarrativeCluster(db.Model):
    """Narrative Cluster table for storing grouped thematic narrative threads"""
    __tablename__ = 'narrative_clusters'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    keywords_json = db.Column(db.Text, nullable=True)  # JSON-serialized array of keywords
    article_ids_json = db.Column(db.Text, nullable=True)  # JSON-serialized array of article IDs in this cluster
    created_at = db.Column(db.DateTime, default=db.func.now(), nullable=False)
    updated_at = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now(), nullable=False)

    @property
    def keywords(self):
        """Getter for deserialized keywords array"""
        if self.keywords_json:
            try:
                return json.loads(self.keywords_json)
            except ValueError:
                return []
        return []

    @keywords.setter
    def keywords(self, val):
        """Setter for keywords array serializing to JSON"""
        self.keywords_json = json.dumps(val)

    @property
    def article_ids(self):
        """Getter for deserialized article IDs array"""
        if self.article_ids_json:
            try:
                return json.loads(self.article_ids_json)
            except ValueError:
                return []
        return []

    @article_ids.setter
    def article_ids(self, val):
        """Setter for article IDs array serializing to JSON"""
        self.article_ids_json = json.dumps(val)

    def to_dict(self):
        """Serialize narrative cluster object"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'keywords': self.keywords,
            'article_ids': self.article_ids,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

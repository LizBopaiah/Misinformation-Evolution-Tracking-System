from app.extensions import db

class Article(db.Model):
    """Article Model containing core metadata and text of analyzed news articles"""
    __tablename__ = 'articles'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(256), nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    source = db.Column(db.String(120), nullable=True)
    url = db.Column(db.String(512), unique=True, nullable=True, index=True)
    published_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=db.func.now(), nullable=False)
    updated_at = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now(), nullable=False)

    # Relationships (defining foreign_keys explicitly for evolution mapping to avoid circular ambiguity)
    fact_checks = db.relationship('FactCheckResult', backref='article', lazy=True, cascade="all, delete-orphan")
    sentiments = db.relationship('SentimentResult', backref='article', lazy=True, cascade="all, delete-orphan")
    
    evolutions = db.relationship(
        'EvolutionResult',
        backref='article',
        lazy=True,
        foreign_keys='EvolutionResult.article_id',
        cascade="all, delete-orphan"
    )
    
    mutations = db.relationship(
        'EvolutionResult',
        backref='parent',
        lazy=True,
        foreign_keys='EvolutionResult.parent_id'
    )

    def to_dict(self):
        """Serialize article object"""
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'source': self.source,
            'url': self.url,
            'published_at': self.published_at.isoformat() if self.published_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

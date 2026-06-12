from app.extensions import db

class ExportRecord(db.Model):
    """Stores metadata, integrity details, and cached snapshots of exported reports/dossiers"""
    __tablename__ = 'export_records'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    export_type = db.Column(db.String(64), nullable=False) # e.g. fact_audit, sentiment, evolution, comparison, dossier
    source_type = db.Column(db.String(64), nullable=False) # e.g. search, report
    source_id = db.Column(db.Integer, nullable=True) # nullable for cascade protection SET NULL behavior
    
    file_name = db.Column(db.String(256), nullable=False)
    file_path = db.Column(db.String(512), nullable=False)
    export_format = db.Column(db.String(16), nullable=False) # pdf, json, html
    status = db.Column(db.String(32), default='pending', nullable=False) # pending, completed, failed
    file_size = db.Column(db.Integer, nullable=True)
    file_hash = db.Column(db.String(64), nullable=True) # SHA-256 integrity hash
    snapshot_json = db.Column(db.Text, nullable=True) # serialized raw data payload
    created_at = db.Column(db.DateTime, default=db.func.now(), nullable=False)

    # Relationships
    user = db.relationship('User', backref=db.backref('export_records', lazy=True, cascade="all, delete-orphan"))

    def to_dict(self):
        """Serialize ExportRecord object"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'export_type': self.export_type,
            'source_type': self.source_type,
            'source_id': self.source_id,
            'file_name': self.file_name,
            'export_format': self.export_format,
            'status': self.status,
            'file_size': self.file_size,
            'file_hash': self.file_hash,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'download_url': f"/api/export/{self.id}"
        }

from app.extensions import db

class InvestigationCase(db.Model):
    """Represents a research case file container for investigations"""
    __tablename__ = 'investigation_cases'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    title = db.Column(db.String(256), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(64), nullable=False, default='OPEN')  # 'OPEN', 'ACTIVE', 'COMPLETED', 'ARCHIVED'
    priority = db.Column(db.String(64), nullable=False, default='MEDIUM')  # 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
    created_at = db.Column(db.DateTime, default=db.func.now(), nullable=False)
    updated_at = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now(), nullable=False)

    # Relationships
    user = db.relationship('User', backref=db.backref('cases', lazy=True, cascade='all, delete-orphan'))
    items = db.relationship('CaseItem', backref='case', lazy=True, cascade='all, delete-orphan')
    activities = db.relationship('CaseActivity', backref='case', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        """Serialize InvestigationCase object"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'description': self.description,
            'status': self.status,
            'priority': self.priority,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class CaseItem(db.Model):
    """Generic polymorphic junction table linking artifacts to cases with snapshot metadata"""
    __tablename__ = 'case_items'

    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey('investigation_cases.id', ondelete='CASCADE'), nullable=False, index=True)
    item_type = db.Column(db.String(64), nullable=False)  # 'search', 'sentiment', 'evolution', 'comparison', 'export'
    item_id = db.Column(db.Integer, nullable=False)
    
    # Snapshot Metadata (de-normalization to prevent joins & preserve history)
    item_title = db.Column(db.String(256), nullable=True)
    item_status = db.Column(db.String(64), nullable=True)
    item_created_at = db.Column(db.DateTime, nullable=True)
    
    created_at = db.Column(db.DateTime, default=db.func.now(), nullable=False)

    # Unique Constraint to prevent duplicate attachments
    __table_args__ = (
        db.UniqueConstraint('case_id', 'item_type', 'item_id', name='uq_case_item'),
    )

    def to_dict(self):
        """Serialize CaseItem object"""
        return {
            'id': self.id,
            'case_id': self.case_id,
            'item_type': self.item_type,
            'item_id': self.item_id,
            'item_title': self.item_title,
            'item_status': self.item_status,
            'item_created_at': self.item_created_at.isoformat() if self.item_created_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class CaseActivity(db.Model):
    """Audit trail activity logger for case operations"""
    __tablename__ = 'case_activities'

    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey('investigation_cases.id', ondelete='CASCADE'), nullable=False, index=True)
    action = db.Column(db.String(64), nullable=False)  # 'CREATED_CASE', 'UPDATED_CASE', 'ARCHIVED_CASE', 'ATTACHED_ITEM', 'DETACHED_ITEM'
    item_type = db.Column(db.String(64), nullable=True)
    item_id = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=db.func.now(), nullable=False)

    def to_dict(self):
        """Serialize CaseActivity object"""
        return {
            'id': self.id,
            'case_id': self.case_id,
            'action': self.action,
            'item_type': self.item_type,
            'item_id': self.item_id,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

from app.extensions import db

class SystemLog(db.Model):
    """Database-backed system logger for tracking important admin/operational events"""
    __tablename__ = 'system_logs'

    id = db.Column(db.Integer, primary_key=True)
    level = db.Column(db.String(24), nullable=False, index=True)  # INFO, WARNING, ERROR, CRITICAL
    message = db.Column(db.Text, nullable=False)
    module = db.Column(db.String(64), nullable=True)
    created_at = db.Column(db.DateTime, default=db.func.now(), nullable=False)

    def to_dict(self):
        """Serialize system log object"""
        return {
            'id': self.id,
            'level': self.level,
            'message': self.message,
            'module': self.module,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

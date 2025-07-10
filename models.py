from app import db
from datetime import datetime

class SesameToken(db.Model):
    """Model to store Sesame API token configuration"""
    __tablename__ = 'sesame_tokens'
    
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(255), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    region = db.Column(db.String(10), default='eu1')  # eu1, eu2, eu3, eu4, eu5, br1, br2, mx1, demo1
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<SesameToken {self.id}>'
    
    @classmethod
    def get_active_token(cls):
        """Get the currently active token"""
        return cls.query.filter_by(is_active=True).first()
    
    @classmethod
    def set_active_token(cls, token, description=None, region='eu1'):
        """Set a new active token, deactivating all others"""
        # Deactivate all existing tokens
        cls.query.update({cls.is_active: False})
        
        # Create new active token
        new_token = cls(token=token, description=description, region=region, is_active=True)
        db.session.add(new_token)
        db.session.commit()
        
        return new_token
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


class CheckType(db.Model):
    """Model to store Sesame check types (activity types)"""
    __tablename__ = 'check_types'
    
    id = db.Column(db.String(50), primary_key=True)  # UUID from API
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<CheckType {self.id}: {self.name}>'
    
    @classmethod
    def get_by_id(cls, check_type_id):
        """Get check type by ID"""
        return cls.query.get(check_type_id)
    
    @classmethod
    def get_name_by_id(cls, check_type_id):
        """Get check type name by ID"""
        check_type = cls.query.get(check_type_id)
        return check_type.name if check_type else "Actividad desconocida"
    
    @classmethod
    def bulk_upsert(cls, check_types_data):
        """Bulk insert or update check types"""
        for data in check_types_data:
            check_type = cls.query.get(data['id'])
            if check_type:
                # Update existing
                check_type.name = data['name']
                check_type.description = data.get('description', '')
                check_type.updated_at = datetime.utcnow()
            else:
                # Create new
                check_type = cls(
                    id=data['id'],
                    name=data['name'],
                    description=data.get('description', '')
                )
                db.session.add(check_type)
        
        db.session.commit()
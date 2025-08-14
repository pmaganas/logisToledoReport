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
    
    @classmethod
    def remove_all_tokens(cls):
        """Remove all tokens from the database"""
        cls.query.delete()
        db.session.commit()


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


class BackgroundReport(db.Model):
    """Model to store background report status and progress"""
    __tablename__ = 'background_reports'
    
    id = db.Column(db.String(36), primary_key=True)  # UUID string
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending, processing, completed, error
    filename = db.Column(db.String(255), nullable=True)
    file_path = db.Column(db.String(500), nullable=True)
    error_message = db.Column(db.Text, nullable=True)
    
    # Progress tracking
    current_page = db.Column(db.Integer, default=0)
    total_pages = db.Column(db.Integer, default=0)
    current_records = db.Column(db.Integer, default=0)
    total_records = db.Column(db.Integer, default=0)
    pagination_complete = db.Column(db.Boolean, default=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<BackgroundReport {self.id}: {self.status}>'
    
    @classmethod
    def create_report(cls, report_id):
        """Create a new background report"""
        report = cls(id=report_id, status='pending')
        db.session.add(report)
        db.session.commit()
        return report
    
    @classmethod
    def get_report(cls, report_id):
        """Get a report by ID"""
        return cls.query.get(report_id)
    
    def update_status(self, status, filename=None, file_path=None, error_message=None):
        """Update report status"""
        self.status = status
        if filename:
            self.filename = filename
        if file_path:
            self.file_path = file_path
        if error_message:
            self.error_message = error_message
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    def is_cancelled(self):
        """Check if this report has been cancelled"""
        # Refresh from database to get latest status
        db.session.refresh(self)
        return self.status == 'cancelled'
    
    def should_cancel(self):
        """Check if report should be cancelled - used during processing"""
        return self.is_cancelled()
    
    def update_progress(self, current_page, total_pages, current_records, total_records, pagination_complete=None):
        """Update report progress"""
        self.current_page = current_page
        self.total_pages = total_pages
        self.current_records = current_records
        self.total_records = total_records
        if pagination_complete is not None:
            self.pagination_complete = pagination_complete
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    def to_dict(self):
        """Convert to dictionary for JSON response"""
        return {
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'filename': self.filename or '',
            'error': self.error_message or '',
            'progress': {
                'current_page': self.current_page,
                'total_pages': self.total_pages,
                'current_records': self.current_records,
                'total_records': self.total_records,
                'pagination_complete': self.pagination_complete
            }
        }
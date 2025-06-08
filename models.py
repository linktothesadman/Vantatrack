from datetime import datetime
from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    first_name = db.Column(db.String(50), nullable=True)
    last_name = db.Column(db.String(50), nullable=True)
    company_name = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    timezone = db.Column(db.String(50), default='UTC')
    role = db.Column(db.String(20), default='client')
    active = db.Column(db.Boolean, default=True)
    email_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relationships
    campaigns = db.relationship('Campaign', backref='client', lazy=True)
    notifications = db.relationship('Notification', backref='user', lazy=True)
    settings = db.relationship('UserSetting', backref='user', lazy=True)
    activity_logs = db.relationship('ActivityLog', backref='user', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def get_full_name(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username

class Campaign(db.Model):
    __tablename__ = 'campaigns'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    platform = db.Column(db.String(50), nullable=False)  # Facebook, Google, ShareIT
    status = db.Column(db.String(50), default='Pending')  # Pending, In-Progress, Completed
    budget = db.Column(db.Float, default=0.0)
    spent = db.Column(db.Float, default=0.0)
    impressions = db.Column(db.Integer, default=0)
    clicks = db.Column(db.Integer, default=0)
    reach = db.Column(db.Integer, default=0)
    ctr = db.Column(db.Float, default=0.0)  # Click-through rate
    cpm = db.Column(db.Float, default=0.0)  # Cost per mille
    cpc = db.Column(db.Float, default=0.0)  # Cost per click
    cpv = db.Column(db.Float, default=0.0)  # Cost per view
    cpa = db.Column(db.Float, default=0.0)  # Cost per acquisition
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Foreign key
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    def get_remaining_budget(self):
        return max(0, self.budget - self.spent)
    
    def get_budget_percentage(self):
        if self.budget > 0:
            return min(100, (self.spent / self.budget) * 100)
        return 0
    
    def calculate_metrics(self):
        """Calculate and update all marketing metrics"""
        # CTR (Click-Through Rate)
        if self.impressions > 0:
            self.ctr = (self.clicks / self.impressions) * 100
        else:
            self.ctr = 0.0
        
        # CPC (Cost Per Click)
        if self.clicks > 0:
            self.cpc = self.spent / self.clicks
        else:
            self.cpc = 0.0
        
        # CPM (Cost Per Mille - Cost per 1000 impressions)
        if self.impressions > 0:
            self.cpm = (self.spent / self.impressions) * 1000
        else:
            self.cpm = 0.0
        
        # CPV (Cost Per View) - using reach as views proxy
        if self.reach > 0:
            self.cpv = self.spent / self.reach
        else:
            self.cpv = 0.0
        
        # CPA (Cost Per Acquisition) - using clicks as conversion proxy
        if self.clicks > 0:
            self.cpa = self.spent / self.clicks
        else:
            self.cpa = 0.0
        
        return self.ctr

class CampaignData(db.Model):
    __tablename__ = 'campaign_data'
    
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaigns.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    impressions = db.Column(db.Integer, default=0)
    clicks = db.Column(db.Integer, default=0)
    spent = db.Column(db.Float, default=0.0)
    reach = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    campaign = db.relationship('Campaign', backref='daily_data')

class CSVImport(db.Model):
    __tablename__ = 'csv_imports'
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    status = db.Column(db.String(50), default='Pending')  # Pending, Processing, Completed, Failed
    rows_processed = db.Column(db.Integer, default=0)
    rows_failed = db.Column(db.Integer, default=0)
    error_message = db.Column(db.Text)
    imported_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    # Relationships
    user = db.relationship('User', backref='csv_imports')

class UserSetting(db.Model):
    __tablename__ = 'user_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    setting_key = db.Column(db.String(100), nullable=False)
    setting_value = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('user_id', 'setting_key'),)

class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text)
    type = db.Column(db.String(50), default='info')  # info, success, warning, error
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ActivityLog(db.Model):
    __tablename__ = 'activity_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class SystemSettings(db.Model):
    __tablename__ = 'system_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    setting_key = db.Column(db.String(100), unique=True, nullable=False)
    setting_value = db.Column(db.Text)
    description = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

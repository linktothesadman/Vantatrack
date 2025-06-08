from app import app, db
from models import User, Campaign, CampaignData, UserSetting, Notification, ActivityLog
from datetime import datetime, date
import csv
import logging

def create_sample_users():
    """Create sample users with comprehensive data"""
    users_data = [
        {
            'username': 'john_doe',
            'email': 'john.doe@email.com',
            'first_name': 'John',
            'last_name': 'Doe',
            'company_name': 'Digital Marketing Co',
            'phone': '+1-555-0123',
            'timezone': 'UTC',
            'role': 'client'
        },
        {
            'username': 'jane_smith',
            'email': 'jane.smith@business.com',
            'first_name': 'Jane',
            'last_name': 'Smith',
            'company_name': 'Smith Business Solutions',
            'phone': '+1-555-0456',
            'timezone': 'UTC',
            'role': 'client'
        },
        {
            'username': 'mike_wilson',
            'email': 'mike.wilson@company.com',
            'first_name': 'Mike',
            'last_name': 'Wilson',
            'company_name': 'Wilson Enterprises',
            'phone': '+1-555-0789',
            'timezone': 'UTC',
            'role': 'client'
        }
    ]
    
    for user_data in users_data:
        user = User(**user_data)
        user.set_password('demo123')
        user.email_verified = True
        db.session.add(user)
    
    db.session.commit()
    logging.info(f"Created {len(users_data)} sample users")
    return True

def import_csv_data():
    """Import sample CSV data"""
    try:
        with open('sample_campaigns.csv', 'r') as file:
            reader = csv.DictReader(file)
            
            campaigns_created = {}
            rows_processed = 0
            
            for row in reader:
                # Find user by email
                user = User.query.filter_by(email=row['client_email']).first()
                if not user:
                    continue
                
                # Create or update campaign
                campaign_key = f"{row['campaign_name']}_{user.id}_{row['platform']}"
                if campaign_key not in campaigns_created:
                    campaign = Campaign(
                        name=row['campaign_name'],
                        platform=row['platform'],
                        status=row['status'],
                        budget=float(row['budget']),
                        spent=0.0,
                        impressions=0,
                        clicks=0,
                        reach=0,
                        user_id=user.id
                    )
                    db.session.add(campaign)
                    db.session.flush()
                    campaigns_created[campaign_key] = campaign
                else:
                    campaign = campaigns_created[campaign_key]
                
                # Update campaign totals
                campaign.spent += float(row['spent'])
                campaign.impressions += int(row['impressions'])
                campaign.clicks += int(row['clicks'])
                campaign.reach += int(row['reach'])
                campaign.calculate_metrics()
                
                # Add daily data
                campaign_date = datetime.strptime(row['date'], '%Y-%m-%d').date()
                daily_data = CampaignData(
                    campaign_id=campaign.id,
                    date=campaign_date,
                    impressions=int(row['impressions']),
                    clicks=int(row['clicks']),
                    spent=float(row['spent']),
                    reach=int(row['reach'])
                )
                db.session.add(daily_data)
                rows_processed += 1
            
            db.session.commit()
            logging.info(f"Imported {rows_processed} rows of campaign data")
            return True
            
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error importing CSV data: {e}")
        return False

def create_sample_notifications():
    """Create sample notifications for users"""
    users = User.query.all()
    
    for user in users:
        notifications = [
            {
                'title': 'Welcome to Marketing Hub',
                'message': 'Your account has been set up successfully. Start by uploading your campaign data.',
                'type': 'success'
            },
            {
                'title': 'Campaign Performance Update',
                'message': 'Your campaigns are performing well this week. Check the reports for detailed insights.',
                'type': 'info'
            }
        ]
        
        for notif_data in notifications:
            notification = Notification(
                user_id=user.id,
                title=notif_data['title'],
                message=notif_data['message'],
                type=notif_data['type']
            )
            db.session.add(notification)
    
    db.session.commit()
    logging.info("Created sample notifications")

def create_default_settings():
    """Create default user settings"""
    users = User.query.all()
    
    default_settings = {
        'email_notifications': 'true',
        'dashboard_refresh_rate': '300',
        'default_currency': 'USD',
        'date_format': 'YYYY-MM-DD',
        'timezone': 'UTC'
    }
    
    for user in users:
        for key, value in default_settings.items():
            setting = UserSetting(
                user_id=user.id,
                setting_key=key,
                setting_value=value
            )
            db.session.add(setting)
    
    db.session.commit()
    logging.info("Created default user settings")

def initialize_database():
    """Initialize the complete database with sample data"""
    with app.app_context():
        try:
            # Create all tables
            db.create_all()
            logging.info("Database tables created")
            
            # Check if data already exists
            if User.query.count() > 0:
                logging.info("Database already has data")
                return True
            
            # Create sample data
            create_sample_users()
            import_csv_data()
            create_sample_notifications()
            create_default_settings()
            
            logging.info("Database initialization completed successfully")
            return True
            
        except Exception as e:
            logging.error(f"Database initialization failed: {e}")
            return False

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    initialize_database()
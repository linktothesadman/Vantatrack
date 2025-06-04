import pandas as pd
import os
from datetime import datetime
from app import app, db
from models import User, Campaign, CampaignData, CSVImport

def process_csv_file(file_path):
    """Process uploaded CSV file and import campaign data"""
    try:
        # Read CSV file
        df = pd.read_csv(file_path)
        
        # Required columns
        required_columns = ['client_email', 'campaign_name', 'platform', 'date', 
                          'impressions', 'clicks', 'spent', 'reach', 'budget', 'status']
        
        # Check if all required columns exist
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            return False, f"Missing required columns: {', '.join(missing_columns)}"
        
        rows_processed = 0
        rows_failed = 0
        
        for _, row in df.iterrows():
            try:
                # Find or create user
                user = User.query.filter_by(email=row['client_email']).first()
                if not user:
                    # Create user with email as username
                    username = row['client_email'].split('@')[0]
                    user = User(
                        username=username,
                        email=row['client_email'],
                        password_hash='default_hash'  # They'll need to reset password
                    )
                    user.set_password('temp123')  # Temporary password
                    db.session.add(user)
                    db.session.flush()  # Get user ID
                
                # Find or create campaign
                campaign = Campaign.query.filter_by(
                    name=row['campaign_name'],
                    user_id=user.id,
                    platform=row['platform']
                ).first()
                
                if not campaign:
                    campaign = Campaign(
                        name=row['campaign_name'],
                        platform=row['platform'],
                        status=row['status'],
                        budget=float(row['budget']),
                        user_id=user.id
                    )
                    db.session.add(campaign)
                    db.session.flush()  # Get campaign ID
                
                # Update campaign totals
                campaign.spent = float(row['spent'])
                campaign.impressions = int(row['impressions'])
                campaign.clicks = int(row['clicks'])
                campaign.reach = int(row['reach'])
                campaign.budget = float(row['budget'])
                campaign.status = row['status']
                campaign.updated_at = datetime.utcnow()
                
                # Calculate metrics
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
                
            except Exception as e:
                print(f"Error processing row: {e}")
                rows_failed += 1
                continue
        
        # Commit all changes
        db.session.commit()
        
        return True, f"Successfully processed {rows_processed} rows, {rows_failed} failed"
        
    except Exception as e:
        db.session.rollback()
        return False, f"Error processing CSV: {str(e)}"

def create_sample_data():
    """Create sample users and import the sample CSV"""
    try:
        # Check if we already have data
        if User.query.count() > 0:
            return True, "Sample data already exists"
        
        # Create sample users
        users_data = [
            {'username': 'john_doe', 'email': 'john.doe@email.com', 'first_name': 'John', 'last_name': 'Doe'},
            {'username': 'jane_smith', 'email': 'jane.smith@business.com', 'first_name': 'Jane', 'last_name': 'Smith'},
            {'username': 'mike_wilson', 'email': 'mike.wilson@company.com', 'first_name': 'Mike', 'last_name': 'Wilson'}
        ]
        
        for user_data in users_data:
            user = User(**user_data)
            user.set_password('demo123')
            db.session.add(user)
        
        db.session.commit()
        
        # Process sample CSV
        if os.path.exists('sample_campaigns.csv'):
            success, message = process_csv_file('sample_campaigns.csv')
            return success, f"Sample users created. CSV import: {message}"
        else:
            return True, "Sample users created but no CSV file found"
            
    except Exception as e:
        db.session.rollback()
        return False, f"Error creating sample data: {str(e)}"
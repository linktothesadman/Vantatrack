import pandas as pd
import os
from datetime import datetime
from app import app, db
from models import User, Campaign, CampaignData, CSVImport

import pandas as pd
from datetime import datetime
from app import app, db
from models import User, Campaign, CampaignData

# Define field mappings with synonyms
COLUMN_SYNONYMS = {
    "client_email": ["email", "client", "user_email"],
    "campaign_name": ["campaign", "name", "ad_name"],
    "platform": ["channel", "source"],
    "date": ["day", "reporting_date"],
    "impressions": ["views", "impr"],
    "clicks": ["click", "click_throughs",'ctr'],
    "spent": ["cost", "amount_spent"],
    "reach": ["audience", "outreach"],
    "budget": ["daily_budget", "total_budget"],
    "status": ["state", "campaign_status"]
}

def match_column(df, standard_name):
    """Find the best matching column name in the DataFrame based on synonyms"""
    candidates = [standard_name] + COLUMN_SYNONYMS.get(standard_name, [])
    for candidate in candidates:
        for col in df.columns:
            if col.strip().lower() == candidate.lower():
                return col
    return None

def process_csv_file(file_path):
    """Process uploaded CSV file and import campaign data with fuzzy matching and partial support"""
    try:
        df = pd.read_csv(file_path, encoding='utf-16', sep=None, engine='python')  # auto-detect separator
    except UnicodeDecodeError:
        df = pd.read_csv(file_path, encoding='windows-1252', sep=None, engine='python')

    field_map = {}
    for field in COLUMN_SYNONYMS.keys():
        matched = match_column(df, field)
        if matched:
            field_map[field] = matched

    rows_processed = 0
    rows_failed = 0

    for _, row in df.iterrows():
        try:
            if 'client_email' not in field_map:
                continue  # Cannot associate user
            
            email = row[field_map['client_email']]
            user = User.query.filter_by(email=email).first()
            if not user:
                username = email.split('@')[0]
                user = User(username=username, email=email)
                user.set_password('temp123')
                db.session.add(user)
                db.session.flush()
            
            name = row.get(field_map.get('campaign_name'), 'Unnamed')
            platform = row.get(field_map.get('platform'), 'Unknown')
            campaign = Campaign.query.filter_by(name=name, platform=platform, user_id=user.id).first()
            if not campaign:
                campaign = Campaign(
                    name=name,
                    platform=platform,
                    status=row.get(field_map.get('status'), 'active'),
                    budget=float(row.get(field_map.get('budget'), 0.0)),
                    user_id=user.id
                )
                db.session.add(campaign)
                db.session.flush()

            # Update campaign
            for key in ['spent', 'impressions', 'clicks', 'reach', 'budget', 'status']:
                if key in field_map:
                    val = row.get(field_map[key])
                    if pd.notna(val):
                        setattr(campaign, key, float(val) if key in ['spent', 'budget'] else int(val) if key != 'status' else val)
            campaign.updated_at = datetime.utcnow()
            campaign.calculate_metrics()

            # Daily data
            if 'date' in field_map:
                date_str = row.get(field_map['date'])
                campaign_date = pd.to_datetime(date_str, errors='coerce')
                if pd.notna(campaign_date):
                    daily_data = CampaignData(
                        campaign_id=campaign.id,
                        date=campaign_date.date(),
                        impressions=int(row.get(field_map.get('impressions'), 0)),
                        clicks=int(row.get(field_map.get('clicks'), 0)),
                        spent=float(row.get(field_map.get('spent'), 0.0)),
                        reach=int(row.get(field_map.get('reach'), 0)),
                    )
                    db.session.add(daily_data)

            rows_processed += 1

        except Exception as e:
            print(f"Row error: {e}")
            rows_failed += 1
            continue

    db.session.commit()
    return True, f"Processed {rows_processed} rows, {rows_failed} failed"
       

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
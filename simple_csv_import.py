import csv
import os
from datetime import datetime
from app import app, db
from models import User, Campaign, CampaignData

def import_sample_csv():
    """Import the sample CSV file and create users/campaigns"""
    try:
        with app.app_context():
            # Check if data already exists
            if User.query.count() > 0:
                print("Data already exists")
                return True, "Data already imported"
            
            # Read CSV file
            with open('sample_campaigns.csv', 'r') as file:
                reader = csv.DictReader(file)
                
                users_created = set()
                campaigns_created = {}
                
                for row in reader:
                    # Create user if not exists
                    email = row['client_email']
                    if email not in users_created:
                        username = email.split('@')[0]
                        user = User(
                            username=username,
                            email=email
                        )
                        user.set_password('demo123')
                        db.session.add(user)
                        db.session.flush()
                        users_created.add(email)
                        user_id = user.id
                    else:
                        user = User.query.filter_by(email=email).first()
                        user_id = user.id
                    
                    # Create campaign if not exists
                    campaign_key = f"{row['campaign_name']}_{user_id}_{row['platform']}"
                    if campaign_key not in campaigns_created:
                        campaign = Campaign(
                            name=row['campaign_name'],
                            platform=row['platform'],
                            status=row['status'],
                            budget=float(row['budget']),
                            spent=float(row['spent']),
                            impressions=int(row['impressions']),
                            clicks=int(row['clicks']),
                            reach=int(row['reach']),
                            user_id=user_id
                        )
                        # Calculate metrics
                        campaign.calculate_metrics()
                        db.session.add(campaign)
                        db.session.flush()
                        campaigns_created[campaign_key] = campaign.id
                        campaign_id = campaign.id
                    else:
                        campaign_id = campaigns_created[campaign_key]
                        # Update campaign totals
                        campaign = Campaign.query.get(campaign_id)
                        campaign.spent += float(row['spent'])
                        campaign.impressions += int(row['impressions'])
                        campaign.clicks += int(row['clicks'])
                        campaign.reach += int(row['reach'])
                        campaign.calculate_metrics()
                    
                    # Add daily data
                    campaign_date = datetime.strptime(row['date'], '%Y-%m-%d').date()
                    daily_data = CampaignData(
                        campaign_id=campaign_id,
                        date=campaign_date,
                        impressions=int(row['impressions']),
                        clicks=int(row['clicks']),
                        spent=float(row['spent']),
                        reach=int(row['reach'])
                    )
                    db.session.add(daily_data)
                
                db.session.commit()
                return True, f"Successfully imported data for {len(users_created)} users"
                
    except Exception as e:
        db.session.rollback()
        return False, f"Error importing CSV: {str(e)}"
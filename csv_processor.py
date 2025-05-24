import pandas as pd
import logging
from datetime import datetime, date
from app import db
from models import Campaign, CampaignData, CSVImport

def process_csv_file(file_path, import_id, client_identifier_column='client_email'):
    """
    Process a CSV file from ad platforms containing data for ALL clients
    Expected CSV format:
    client_email,campaign_name,platform,date,impressions,clicks,spent,reach,budget,status
    
    The system will automatically assign campaigns to the correct users based on client_email
    """
    try:
        # Update import status
        csv_import = CSVImport.query.get(import_id)
        csv_import.status = 'Processing'
        db.session.commit()
        
        # Read CSV file
        df = pd.read_csv(file_path)
        
        # Validate required columns
        required_columns = [client_identifier_column, 'campaign_name', 'platform', 'date', 'impressions', 'clicks', 'spent']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")
        
        rows_processed = 0
        rows_failed = 0
        
        for index, row in df.iterrows():
            try:
                # Find the client user based on email or other identifier
                from models import User
                client_identifier = row[client_identifier_column]
                user = User.query.filter_by(email=client_identifier).first()
                
                if not user:
                    # Skip this row if client doesn't exist in the system
                    logging.warning(f"Client not found: {client_identifier}")
                    rows_failed += 1
                    continue
                
                # Get or create campaign for this specific client
                campaign = Campaign.query.filter_by(
                    name=row['campaign_name'],
                    platform=row['platform'],
                    user_id=user.id
                ).first()
                
                if not campaign:
                    campaign = Campaign(
                        name=row['campaign_name'],
                        platform=row['platform'],
                        user_id=user.id,
                        budget=float(row.get('budget', 0)),
                        status=row.get('status', 'In-Progress')
                    )
                    db.session.add(campaign)
                    db.session.flush()  # Get the ID
                
                # Update campaign totals
                campaign.impressions += int(row.get('impressions', 0))
                campaign.clicks += int(row.get('clicks', 0))
                campaign.spent += float(row.get('spent', 0))
                campaign.reach = max(campaign.reach, int(row.get('reach', 0)))
                
                # Calculate CTR
                campaign.calculate_ctr()
                
                # Parse date
                data_date = pd.to_datetime(row['date']).date()
                
                # Get or create daily data record
                daily_data = CampaignData.query.filter_by(
                    campaign_id=campaign.id,
                    date=data_date
                ).first()
                
                if daily_data:
                    # Update existing record
                    daily_data.impressions += int(row.get('impressions', 0))
                    daily_data.clicks += int(row.get('clicks', 0))
                    daily_data.spent += float(row.get('spent', 0))
                    daily_data.reach = max(daily_data.reach, int(row.get('reach', 0)))
                else:
                    # Create new daily data record
                    daily_data = CampaignData(
                        campaign_id=campaign.id,
                        date=data_date,
                        impressions=int(row.get('impressions', 0)),
                        clicks=int(row.get('clicks', 0)),
                        spent=float(row.get('spent', 0)),
                        reach=int(row.get('reach', 0))
                    )
                    db.session.add(daily_data)
                
                rows_processed += 1
                
            except Exception as e:
                logging.error(f"Error processing row {index}: {str(e)}")
                rows_failed += 1
                continue
        
        # Update import record
        csv_import.status = 'Completed'
        csv_import.rows_processed = rows_processed
        csv_import.rows_failed = rows_failed
        csv_import.completed_at = datetime.utcnow()
        
        db.session.commit()
        
        logging.info(f"CSV import completed: {rows_processed} rows processed, {rows_failed} rows failed")
        
        return {
            'success': True,
            'rows_processed': rows_processed,
            'rows_failed': rows_failed
        }
        
    except Exception as e:
        # Update import record with error
        csv_import = CSVImport.query.get(import_id)
        csv_import.status = 'Failed'
        csv_import.error_message = str(e)
        csv_import.completed_at = datetime.utcnow()
        db.session.commit()
        
        logging.error(f"CSV import failed: {str(e)}")
        
        return {
            'success': False,
            'error': str(e)
        }

def create_sample_campaigns(user_id):
    """Create sample campaigns for demonstration (only if no campaigns exist)"""
    existing_campaigns = Campaign.query.filter_by(user_id=user_id).count()
    
    if existing_campaigns == 0:
        sample_campaigns = [
            {
                'name': 'Brand Awareness Campaign',
                'platform': 'Facebook',
                'budget': 34000,
                'spent': 25000,
                'impressions': 150000,
                'clicks': 3500,
                'reach': 45000,
                'status': 'In-Progress'
            },
            {
                'name': 'Product Launch Campaign',
                'platform': 'Google',
                'budget': 25000,
                'spent': 18000,
                'impressions': 95000,
                'clicks': 2100,
                'reach': 32000,
                'status': 'In-Progress'
            },
            {
                'name': 'Retargeting Campaign',
                'platform': 'ShareIT',
                'budget': 15000,
                'spent': 12000,
                'impressions': 65000,
                'clicks': 1800,
                'reach': 22000,
                'status': 'Completed'
            }
        ]
        
        for campaign_data in sample_campaigns:
            campaign = Campaign(
                name=campaign_data['name'],
                platform=campaign_data['platform'],
                user_id=user_id,
                budget=campaign_data['budget'],
                spent=campaign_data['spent'],
                impressions=campaign_data['impressions'],
                clicks=campaign_data['clicks'],
                reach=campaign_data['reach'],
                status=campaign_data['status']
            )
            campaign.calculate_ctr()
            db.session.add(campaign)
        
        db.session.commit()
        logging.info(f"Created sample campaigns for user {user_id}")

def validate_csv_format(file_path):
    """Validate CSV file format before processing"""
    try:
        df = pd.read_csv(file_path, nrows=1)  # Read just the header
        
        required_columns = ['campaign_name', 'platform', 'date', 'impressions', 'clicks', 'spent']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            return False, f"Missing required columns: {', '.join(missing_columns)}"
        
        return True, "CSV format is valid"
        
    except Exception as e:
        return False, f"Error reading CSV: {str(e)}"

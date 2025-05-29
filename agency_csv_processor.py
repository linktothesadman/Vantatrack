"""
Robust CSV processor for agency campaign data
Handles various CSV formats from different ad platforms and automatically maps columns
"""

import pandas as pd
import logging
import os
from datetime import datetime
from app import app, db
from models import Campaign, CampaignData, User

class AgencyCSVProcessor:
    def __init__(self):
        # Common column mappings for different platforms
        self.column_mappings = {
            # Facebook Ads Manager exports
            'facebook': {
                'client_email': ['client_email', 'account_email', 'advertiser_email'],
                'campaign_name': ['campaign_name', 'Campaign Name', 'Campaign', 'campaign'],
                'date': ['date', 'Date', 'reporting_starts', 'day'],
                'impressions': ['impressions', 'Impressions', 'reach', 'Reach'],
                'clicks': ['clicks', 'Clicks', 'link_clicks', 'Link Clicks'],
                'spent': ['spend', 'Spend', 'amount_spent', 'Amount Spent (USD)', 'cost'],
                'reach': ['reach', 'Reach', 'unique_reach'],
                'budget': ['budget', 'Budget', 'lifetime_budget', 'daily_budget']
            },
            # Google Ads exports
            'google': {
                'client_email': ['client_email', 'customer_email', 'account_email'],
                'campaign_name': ['campaign', 'Campaign', 'campaign_name'],
                'date': ['date', 'Date', 'day', 'Day'],
                'impressions': ['impressions', 'Impressions', 'impr'],
                'clicks': ['clicks', 'Clicks'],
                'spent': ['cost', 'Cost', 'spend', 'cost_micros'],
                'reach': ['reach', 'unique_users'],
                'budget': ['budget', 'Budget', 'average_daily_budget']
            },
            # ShareIT or other platforms
            'shareit': {
                'client_email': ['client_email', 'advertiser_email'],
                'campaign_name': ['campaign_name', 'campaign'],
                'date': ['date', 'report_date'],
                'impressions': ['impressions', 'views'],
                'clicks': ['clicks', 'taps'],
                'spent': ['spend', 'cost'],
                'reach': ['reach', 'unique_users'],
                'budget': ['budget', 'campaign_budget']
            }
        }

    def detect_platform(self, df):
        """Detect which platform the CSV is from based on column names"""
        columns = [col.lower() for col in df.columns]
        
        # Facebook indicators
        if any(fb_col in columns for fb_col in ['amount_spent', 'link_clicks', 'campaign_name']):
            return 'facebook'
        
        # Google Ads indicators
        if any(g_col in columns for g_col in ['cost_micros', 'average_daily_budget', 'impr']):
            return 'google'
        
        # Default to generic mapping
        return 'shareit'

    def find_column(self, df, field_name, platform):
        """Find the actual column name for a field based on mappings"""
        possible_names = self.column_mappings.get(platform, {}).get(field_name, [field_name])
        
        for col_name in possible_names:
            # Case-insensitive search
            for actual_col in df.columns:
                if actual_col.lower() == col_name.lower():
                    return actual_col
        
        return None

    def process_csv_file(self, file_path):
        """Process a CSV file with robust column detection"""
        try:
            # Try different encodings
            encodings = ['utf-8', 'latin1', 'cp1252', 'iso-8859-1']
            df = None
            
            for encoding in encodings:
                try:
                    df = pd.read_csv(file_path, encoding=encoding)
                    logging.info(f"Successfully read CSV with {encoding} encoding")
                    break
                except UnicodeDecodeError:
                    continue
            
            if df is None:
                raise ValueError("Could not read CSV file with any supported encoding")

            # Detect platform
            platform = self.detect_platform(df)
            logging.info(f"Detected platform: {platform}")

            # Map columns
            column_map = {}
            required_fields = ['client_email', 'campaign_name', 'date']
            
            for field in required_fields:
                col = self.find_column(df, field, platform)
                if col:
                    column_map[field] = col
                else:
                    logging.warning(f"Required field '{field}' not found in CSV")

            # Optional fields
            optional_fields = ['impressions', 'clicks', 'spent', 'reach', 'budget']
            for field in optional_fields:
                col = self.find_column(df, field, platform)
                if col:
                    column_map[field] = col

            if not all(field in column_map for field in required_fields):
                missing = [f for f in required_fields if f not in column_map]
                raise ValueError(f"Missing required columns: {missing}")

            # Process data
            results = self.process_dataframe(df, column_map, platform)
            return results

        except Exception as e:
            logging.error(f"Error processing CSV: {str(e)}")
            return {'success': False, 'error': str(e)}

    def process_dataframe(self, df, column_map, platform):
        """Process the dataframe with mapped columns"""
        rows_processed = 0
        rows_failed = 0
        clients_updated = set()

        for index, row in df.iterrows():
            try:
                # Get client email
                client_email = str(row[column_map['client_email']]).strip().lower()
                if pd.isna(client_email) or client_email == 'nan':
                    rows_failed += 1
                    continue

                # Find user
                user = User.query.filter_by(email=client_email).first()
                if not user:
                    logging.warning(f"Client not found: {client_email}")
                    rows_failed += 1
                    continue

                clients_updated.add(client_email)

                # Get campaign name
                campaign_name = str(row[column_map['campaign_name']]).strip()
                if pd.isna(campaign_name) or campaign_name == 'nan':
                    rows_failed += 1
                    continue

                # Get or create campaign
                campaign = Campaign.query.filter_by(
                    name=campaign_name,
                    platform=platform.title(),
                    user_id=user.id
                ).first()

                if not campaign:
                    campaign = Campaign(
                        name=campaign_name,
                        platform=platform.title(),
                        user_id=user.id,
                        budget=self.safe_float(row.get(column_map.get('budget'), 0)),
                        status='Active'
                    )
                    db.session.add(campaign)
                    db.session.flush()

                # Extract metrics with safe conversion
                impressions = self.safe_int(row.get(column_map.get('impressions'), 0))
                clicks = self.safe_int(row.get(column_map.get('clicks'), 0))
                spent = self.safe_float(row.get(column_map.get('spent'), 0))
                reach = self.safe_int(row.get(column_map.get('reach'), 0))

                # Update campaign totals
                campaign.impressions += impressions
                campaign.clicks += clicks
                campaign.spent += spent
                campaign.reach = max(campaign.reach, reach)
                campaign.calculate_metrics()

                # Parse date
                try:
                    data_date = pd.to_datetime(row[column_map['date']]).date()
                except:
                    data_date = datetime.now().date()

                # Create or update daily data
                daily_data = CampaignData.query.filter_by(
                    campaign_id=campaign.id,
                    date=data_date
                ).first()

                if daily_data:
                    daily_data.impressions += impressions
                    daily_data.clicks += clicks
                    daily_data.spent += spent
                    daily_data.reach = max(daily_data.reach, reach)
                else:
                    daily_data = CampaignData(
                        campaign_id=campaign.id,
                        date=data_date,
                        impressions=impressions,
                        clicks=clicks,
                        spent=spent,
                        reach=reach
                    )
                    db.session.add(daily_data)

                rows_processed += 1

            except Exception as e:
                logging.error(f"Error processing row {index}: {str(e)}")
                rows_failed += 1
                continue

        db.session.commit()

        return {
            'success': True,
            'rows_processed': rows_processed,
            'rows_failed': rows_failed,
            'clients_updated': len(clients_updated),
            'platform': platform
        }

    def safe_int(self, value):
        """Safely convert value to int"""
        if pd.isna(value):
            return 0
        try:
            return int(float(str(value).replace(',', '')))
        except:
            return 0

    def safe_float(self, value):
        """Safely convert value to float"""
        if pd.isna(value):
            return 0.0
        try:
            return float(str(value).replace(',', '').replace('$', ''))
        except:
            return 0.0

def process_agency_csv_files():
    """Process all CSV files in the agency data directory"""
    processor = AgencyCSVProcessor()
    data_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'agency_data')
    
    if not os.path.exists(data_dir):
        os.makedirs(data_dir, exist_ok=True)
        logging.info(f"Created agency data directory: {data_dir}")
        return

    csv_files = [f for f in os.listdir(data_dir) if f.lower().endswith('.csv')]
    
    if not csv_files:
        logging.info("No CSV files found in agency data directory")
        return

    for csv_file in csv_files:
        file_path = os.path.join(data_dir, csv_file)
        logging.info(f"Processing file: {csv_file}")
        
        try:
            result = processor.process_csv_file(file_path)
            
            if result['success']:
                logging.info(f"Successfully processed {csv_file}: {result['rows_processed']} rows, {result['clients_updated']} clients updated")
                
                # Move processed file to archive
                archive_dir = os.path.join(data_dir, 'processed')
                os.makedirs(archive_dir, exist_ok=True)
                archive_path = os.path.join(archive_dir, f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{csv_file}")
                os.rename(file_path, archive_path)
                
            else:
                logging.error(f"Failed to process {csv_file}: {result['error']}")
                
                # Move failed file to error directory
                error_dir = os.path.join(data_dir, 'errors')
                os.makedirs(error_dir, exist_ok=True)
                error_path = os.path.join(error_dir, f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{csv_file}")
                os.rename(file_path, error_path)
                
        except Exception as e:
            logging.error(f"Unexpected error processing {csv_file}: {str(e)}")
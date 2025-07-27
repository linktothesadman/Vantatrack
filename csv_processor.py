import pandas as pd
import logging
from datetime import datetime
from app import db
from models import Campaign, CampaignData, CSVImport, User

# Synonym mapping for flexible column matching
COLUMN_SYNONYMS = {
    "client_email": ["email", "client", "user_email"],
    "campaign_name": ["campaign", "name", "ad_name"],
    "platform": ["channel", "source"],
    "date": ["day", "reporting_date"],
    "impressions": ["views", "impr"],
    "clicks": ["click", "click_throughs"],
    "spent": ["cost", "amount_spent"],
    "reach": ["audience", "unique_views"],
    "budget": ["daily_budget", "total_budget"],
    "status": ["state", "campaign_status"]
}

def match_column(df, standard_name):
    candidates = [standard_name] + COLUMN_SYNONYMS.get(standard_name, [])
    for candidate in candidates:
        for col in df.columns:
            if col.strip().lower() == candidate.lower():
                return col
    return None

def process_csv_file(file_path, import_id, client_identifier_column='client_email'):
    try:
        csv_import = CSVImport.query.get(import_id)
        csv_import.status = 'Processing'
        db.session.commit()

        try:
            df = pd.read_csv(file_path, encoding='utf-8')
        except UnicodeDecodeError:
            df = pd.read_csv(file_path, encoding='ISO-8859-1')

        field_map = {}
        for field in COLUMN_SYNONYMS.keys():
            matched = match_column(df, field)
            if matched:
                field_map[field] = matched

        required_core = [client_identifier_column, 'campaign_name', 'platform', 'date', 'impressions', 'clicks', 'spent']
        for col in required_core:
            if col not in field_map:
                raise ValueError(f"Missing required column or synonym: {col}")

        rows_processed = 0
        rows_failed = 0

        for index, row in df.iterrows():
            try:
                client_identifier = row.get(field_map.get(client_identifier_column))
                user = User.query.filter_by(email=client_identifier).first()
                if not user:
                    logging.warning(f"Client not found: {client_identifier}")
                    rows_failed += 1
                    continue

                name = row.get(field_map.get('campaign_name'), 'Unnamed')
                platform = row.get(field_map.get('platform'), 'Unknown')
                campaign = Campaign.query.filter_by(name=name, platform=platform, user_id=user.id).first()
                if not campaign:
                    campaign = Campaign(
                        name=name,
                        platform=platform,
                        user_id=user.id,
                        budget=float(row.get(field_map.get('budget'), 0)),
                        status=row.get(field_map.get('status'), 'In-Progress')
                    )
                    db.session.add(campaign)
                    db.session.flush()

                campaign.impressions += int(row.get(field_map.get('impressions'), 0))
                campaign.clicks += int(row.get(field_map.get('clicks'), 0))
                campaign.spent += float(row.get(field_map.get('spent'), 0))
                campaign.reach = max(campaign.reach or 0, int(row.get(field_map.get('reach'), 0)))
                campaign.calculate_ctr()

                data_date = pd.to_datetime(row.get(field_map.get('date')), errors='coerce')
                if pd.isna(data_date):
                    raise ValueError("Invalid date format")
                data_date = data_date.date()

                daily_data = CampaignData.query.filter_by(campaign_id=campaign.id, date=data_date).first()
                if daily_data:
                    daily_data.impressions += int(row.get(field_map.get('impressions'), 0))
                    daily_data.clicks += int(row.get(field_map.get('clicks'), 0))
                    daily_data.spent += float(row.get(field_map.get('spent'), 0))
                    daily_data.reach = max(daily_data.reach or 0, int(row.get(field_map.get('reach'), 0)))
                else:
                    daily_data = CampaignData(
                        campaign_id=campaign.id,
                        date=data_date,
                        impressions=int(row.get(field_map.get('impressions'), 0)),
                        clicks=int(row.get(field_map.get('clicks'), 0)),
                        spent=float(row.get(field_map.get('spent'), 0)),
                        reach=int(row.get(field_map.get('reach'), 0))
                    )
                    db.session.add(daily_data)

                rows_processed += 1

            except Exception as e:
                logging.error(f"Error processing row {index}: {str(e)}")
                rows_failed += 1
                continue

        csv_import.status = 'Completed'
        csv_import.rows_processed = rows_processed
        csv_import.rows_failed = rows_failed
        csv_import.completed_at = datetime.utcnow()
        db.session.commit()

        logging.info(f"CSV import completed: {rows_processed} rows processed, {rows_failed} rows failed")
        return {'success': True, 'rows_processed': rows_processed, 'rows_failed': rows_failed}

    except Exception as e:
        csv_import = CSVImport.query.get(import_id)
        csv_import.status = 'Failed'
        csv_import.error_message = str(e)
        csv_import.completed_at = datetime.utcnow()
        db.session.commit()

        logging.error(f"CSV import failed: {str(e)}")
        return {'success': False, 'error': str(e)}

def create_sample_campaigns(user_id):
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
    try:
        df = pd.read_csv(file_path, nrows=1)
        required_columns = ['campaign_name', 'platform', 'date', 'impressions', 'clicks', 'spent']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            return False, f"Missing required columns: {', '.join(missing_columns)}"
        return True, "CSV format is valid"
    except Exception as e:
        return False, f"Error reading CSV: {str(e)}"

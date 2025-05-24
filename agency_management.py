"""
Agency Management Module
Handles CSV uploads from ad platforms (Facebook, Google, ShareIT)
Contains data for ALL clients that gets filtered per user login
"""

import os
import pandas as pd
import logging
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app import app, db
from models import Campaign, CampaignData, CSVImport, User

agency_bp = Blueprint('agency', __name__, url_prefix='/agency')

@agency_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def agency_upload():
    """Agency upload interface for CSV files from ad platforms"""
    if request.method == 'POST':
        if 'csv_file' not in request.files:
            flash('No file selected', 'error')
            return redirect(request.url)
        
        file = request.files['csv_file']
        platform = request.form.get('platform', 'Unknown')
        
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(request.url)
        
        if file and file.filename.lower().endswith('.csv'):
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
            filename = f"{platform}_{timestamp}{filename}"
            
            # Save to agency uploads directory
            agency_upload_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'agency_uploads')
            os.makedirs(agency_upload_dir, exist_ok=True)
            filepath = os.path.join(agency_upload_dir, filename)
            
            file.save(filepath)
            
            # Create import record
            csv_import = CSVImport(
                filename=filename,
                file_path=filepath,
                imported_by=current_user.id,
                status='Pending'
            )
            db.session.add(csv_import)
            db.session.commit()
            
            # Process the file
            try:
                result = process_agency_csv(filepath, csv_import.id, platform)
                if result['success']:
                    flash(f'CSV imported successfully! Processed {result["rows_processed"]} rows, assigned to {result["clients_updated"]} clients.', 'success')
                else:
                    flash(f'CSV import failed: {result["error"]}', 'error')
            except Exception as e:
                logging.error(f"Error processing agency CSV: {str(e)}")
                flash(f'Error processing CSV: {str(e)}', 'error')
        else:
            flash('Please upload a valid CSV file', 'error')
    
    # Get recent imports
    recent_imports = CSVImport.query.order_by(CSVImport.created_at.desc()).limit(10).all()
    
    return render_template('agency/upload.html', recent_imports=recent_imports)

def process_agency_csv(file_path, import_id, platform):
    """
    Process CSV from ad platforms containing ALL client campaign data
    Expected format: client_email,campaign_name,date,impressions,clicks,spent,reach,budget,status
    """
    try:
        csv_import = CSVImport.query.get(import_id)
        csv_import.status = 'Processing'
        db.session.commit()
        
        # Read CSV
        df = pd.read_csv(file_path)
        
        # Validate required columns
        required_columns = ['client_email', 'campaign_name', 'date', 'impressions', 'clicks', 'spent']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")
        
        rows_processed = 0
        rows_failed = 0
        clients_updated = set()
        
        for index, row in df.iterrows():
            try:
                # Find client by email
                client_email = str(row['client_email']).strip().lower()
                user = User.query.filter_by(email=client_email).first()
                
                if not user:
                    logging.warning(f"Client not found: {client_email}")
                    rows_failed += 1
                    continue
                
                clients_updated.add(client_email)
                
                # Get or create campaign
                campaign = Campaign.query.filter_by(
                    name=str(row['campaign_name']).strip(),
                    platform=platform,
                    user_id=user.id
                ).first()
                
                if not campaign:
                    campaign = Campaign(
                        name=str(row['campaign_name']).strip(),
                        platform=platform,
                        user_id=user.id,
                        budget=float(row.get('budget', 0)) if pd.notna(row.get('budget')) else 0.0,
                        status=str(row.get('status', 'Active')).strip()
                    )
                    db.session.add(campaign)
                    db.session.flush()
                
                # Update campaign totals
                impressions = int(row.get('impressions', 0)) if pd.notna(row.get('impressions')) else 0
                clicks = int(row.get('clicks', 0)) if pd.notna(row.get('clicks')) else 0
                spent = float(row.get('spent', 0)) if pd.notna(row.get('spent')) else 0.0
                reach = int(row.get('reach', 0)) if pd.notna(row.get('reach')) else 0
                
                campaign.impressions += impressions
                campaign.clicks += clicks
                campaign.spent += spent
                campaign.reach = max(campaign.reach, reach)
                campaign.calculate_ctr()
                
                # Parse date
                try:
                    data_date = pd.to_datetime(row['date']).date()
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
        
        # Update import record
        csv_import.status = 'Completed'
        csv_import.rows_processed = rows_processed
        csv_import.rows_failed = rows_failed
        csv_import.completed_at = datetime.utcnow()
        
        db.session.commit()
        
        return {
            'success': True,
            'rows_processed': rows_processed,
            'rows_failed': rows_failed,
            'clients_updated': len(clients_updated)
        }
        
    except Exception as e:
        csv_import = CSVImport.query.get(import_id)
        csv_import.status = 'Failed'
        csv_import.error_message = str(e)
        csv_import.completed_at = datetime.utcnow()
        db.session.commit()
        
        logging.error(f"Agency CSV import failed: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

@agency_bp.route('/clients')
@login_required
def view_clients():
    """View all clients and their campaign summary"""
    clients = User.query.all()
    client_stats = []
    
    for client in clients:
        campaigns = Campaign.query.filter_by(user_id=client.id).all()
        total_budget = sum(c.budget for c in campaigns)
        total_spent = sum(c.spent for c in campaigns)
        total_impressions = sum(c.impressions for c in campaigns)
        total_clicks = sum(c.clicks for c in campaigns)
        
        client_stats.append({
            'client': client,
            'campaign_count': len(campaigns),
            'total_budget': total_budget,
            'total_spent': total_spent,
            'total_impressions': total_impressions,
            'total_clicks': total_clicks,
            'platforms': list(set(c.platform for c in campaigns))
        })
    
    return render_template('agency/clients.html', client_stats=client_stats)

# Register blueprint
app.register_blueprint(agency_bp)
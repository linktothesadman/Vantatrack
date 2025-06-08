import os
from flask import render_template, request, redirect, url_for, flash, jsonify, current_app, abort
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from app import app, db
from models import Campaign, CampaignData, CSVImport, User, UserSetting, Notification, ActivityLog
import logging
import csv
import json

def log_activity(action, description=None):
    """Log user activity"""
    if current_user.is_authenticated:
        log = ActivityLog(
            user_id=current_user.id,
            action=action,
            description=description,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        db.session.add(log)
        db.session.commit()

@app.route('/')
@login_required
def dashboard():
    """Enhanced dashboard with comprehensive metrics"""
    # Update last login
    current_user.last_login = datetime.utcnow()
    db.session.commit()
    
    # Get user's campaigns
    campaigns = Campaign.query.filter_by(user_id=current_user.id).all()
    
    # Calculate comprehensive summary metrics
    total_impressions = sum(c.impressions for c in campaigns)
    total_clicks = sum(c.clicks for c in campaigns)
    total_reach = sum(c.reach for c in campaigns)
    total_budget = sum(c.budget for c in campaigns)
    total_spent = sum(c.spent for c in campaigns)
    
    # Calculate all key metrics
    ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
    cpc = (total_spent / total_clicks) if total_clicks > 0 else 0
    cpm = (total_spent / total_impressions * 1000) if total_impressions > 0 else 0
    cpv = (total_spent / total_reach) if total_reach > 0 else 0
    cpa = cpc  # Using CPC as CPA proxy
    
    # Get recent campaign data for charts (last 30 days)
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=30)
    
    # Get daily data for charts
    daily_data = db.session.query(CampaignData).join(Campaign).filter(
        Campaign.user_id == current_user.id,
        CampaignData.date >= start_date,
        CampaignData.date <= end_date
    ).order_by(CampaignData.date).all()
    
    # Group data by date
    chart_data = {}
    for data in daily_data:
        date_str = data.date.strftime('%Y-%m-%d')
        if date_str not in chart_data:
            chart_data[date_str] = {'impressions': 0, 'clicks': 0, 'spent': 0, 'reach': 0}
        chart_data[date_str]['impressions'] += data.impressions
        chart_data[date_str]['clicks'] += data.clicks
        chart_data[date_str]['spent'] += data.spent
        chart_data[date_str]['reach'] += data.reach
    
    # Platform breakdown
    platform_data = {}
    for campaign in campaigns:
        platform = campaign.platform
        if platform not in platform_data:
            platform_data[platform] = {
                'campaigns': 0, 'spent': 0, 'impressions': 0, 
                'clicks': 0, 'reach': 0
            }
        platform_data[platform]['campaigns'] += 1
        platform_data[platform]['spent'] += campaign.spent
        platform_data[platform]['impressions'] += campaign.impressions
        platform_data[platform]['clicks'] += campaign.clicks
        platform_data[platform]['reach'] += campaign.reach
    
    # Get recent notifications
    notifications = Notification.query.filter_by(
        user_id=current_user.id, is_read=False
    ).order_by(Notification.created_at.desc()).limit(5).all()
    
    log_activity('dashboard_view', 'Viewed dashboard')
    
    return render_template('dashboard/index.html',
                         campaigns=campaigns,
                         total_impressions=total_impressions,
                         total_clicks=total_clicks,
                         total_reach=total_reach,
                         total_budget=total_budget,
                         total_spent=total_spent,
                         ctr=round(ctr, 2),
                         cpc=round(cpc, 2),
                         cpm=round(cpm, 2),
                         cpv=round(cpv, 2),
                         cpa=round(cpa, 2),
                         chart_data=json.dumps(chart_data),
                         platform_data=platform_data,
                         notifications=notifications)

@app.route('/campaigns')
@login_required
def campaigns():
    """Campaign management page"""
    page = request.args.get('page', 1, type=int)
    platform_filter = request.args.get('platform', '')
    status_filter = request.args.get('status', '')
    
    query = Campaign.query.filter_by(user_id=current_user.id)
    
    if platform_filter:
        query = query.filter(Campaign.platform == platform_filter)
    if status_filter:
        query = query.filter(Campaign.status == status_filter)
    
    campaigns = query.order_by(Campaign.updated_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    # Get available platforms and statuses for filters
    platforms = db.session.query(Campaign.platform).filter_by(
        user_id=current_user.id
    ).distinct().all()
    statuses = db.session.query(Campaign.status).filter_by(
        user_id=current_user.id
    ).distinct().all()
    
    log_activity('campaigns_view', 'Viewed campaigns list')
    
    return render_template('campaigns/index.html',
                         campaigns=campaigns,
                         platforms=[p[0] for p in platforms],
                         statuses=[s[0] for s in statuses],
                         current_platform=platform_filter,
                         current_status=status_filter)

@app.route('/campaign/<int:campaign_id>')
@login_required
def campaign_detail(campaign_id):
    """Campaign detail page"""
    campaign = Campaign.query.filter_by(
        id=campaign_id, user_id=current_user.id
    ).first_or_404()
    
    # Get daily data for this campaign
    daily_data = CampaignData.query.filter_by(
        campaign_id=campaign.id
    ).order_by(CampaignData.date.desc()).limit(30).all()
    
    log_activity('campaign_view', f'Viewed campaign: {campaign.name}')
    
    return render_template('campaigns/detail.html',
                         campaign=campaign,
                         daily_data=daily_data)

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_csv():
    """Enhanced CSV upload with robust processing"""
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(request.url)
        
        if file and file.filename.lower().endswith('.csv'):
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{timestamp}_{filename}"
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            # Create CSV import record
            csv_import = CSVImport(
                filename=filename,
                file_path=file_path,
                imported_by=current_user.id
            )
            db.session.add(csv_import)
            db.session.commit()
            
            # Process the CSV file
            success, message = process_enhanced_csv(file_path, csv_import.id)
            
            if success:
                flash(f'CSV uploaded and processed successfully: {message}', 'success')
                log_activity('csv_upload', f'Uploaded CSV: {filename}')
            else:
                flash(f'Error processing CSV: {message}', 'error')
                csv_import.status = 'Failed'
                csv_import.error_message = message
                db.session.commit()
            
            return redirect(url_for('dashboard'))
        else:
            flash('Please upload a CSV file', 'error')
    
    # Get recent imports
    recent_imports = CSVImport.query.filter_by(
        imported_by=current_user.id
    ).order_by(CSVImport.created_at.desc()).limit(10).all()
    
    return render_template('upload/index.html', recent_imports=recent_imports)

def process_enhanced_csv(file_path, import_id):
    """Enhanced CSV processing with better error handling"""
    try:
        csv_import = CSVImport.query.get(import_id)
        csv_import.status = 'Processing'
        db.session.commit()
        
        rows_processed = 0
        rows_failed = 0
        
        with open(file_path, 'r', encoding='utf-8') as file:
            # Try to detect delimiter
            sample = file.read(1024)
            file.seek(0)
            sniffer = csv.Sniffer()
            delimiter = sniffer.sniff(sample).delimiter
            
            reader = csv.DictReader(file, delimiter=delimiter)
            
            # Required columns
            required_columns = ['client_email', 'campaign_name', 'platform', 
                              'date', 'impressions', 'clicks', 'spent', 'reach']
            
            # Check if all required columns exist
            missing_columns = [col for col in required_columns if col not in reader.fieldnames]
            if missing_columns:
                return False, f"Missing required columns: {', '.join(missing_columns)}"
            
            for row in reader:
                try:
                    # Find or create user
                    user = User.query.filter_by(email=row['client_email']).first()
                    if not user:
                        continue  # Skip if user doesn't exist
                    
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
                            status=row.get('status', 'Active'),
                            budget=float(row.get('budget', 0)),
                            user_id=user.id
                        )
                        db.session.add(campaign)
                        db.session.flush()
                    
                    # Update campaign totals
                    campaign.spent = float(row['spent'])
                    campaign.impressions = int(row['impressions'])
                    campaign.clicks = int(row['clicks'])
                    campaign.reach = int(row['reach'])
                    campaign.updated_at = datetime.utcnow()
                    
                    # Calculate metrics
                    campaign.calculate_metrics()
                    
                    # Add daily data
                    campaign_date = datetime.strptime(row['date'], '%Y-%m-%d').date()
                    
                    # Check if daily data already exists
                    existing_data = CampaignData.query.filter_by(
                        campaign_id=campaign.id,
                        date=campaign_date
                    ).first()
                    
                    if existing_data:
                        # Update existing data
                        existing_data.impressions = int(row['impressions'])
                        existing_data.clicks = int(row['clicks'])
                        existing_data.spent = float(row['spent'])
                        existing_data.reach = int(row['reach'])
                    else:
                        # Create new daily data
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
                    logging.error(f"Error processing row: {e}")
                    rows_failed += 1
                    continue
        
        # Update import status
        csv_import.status = 'Completed'
        csv_import.rows_processed = rows_processed
        csv_import.rows_failed = rows_failed
        csv_import.completed_at = datetime.utcnow()
        
        db.session.commit()
        
        return True, f"Processed {rows_processed} rows, {rows_failed} failed"
        
    except Exception as e:
        db.session.rollback()
        csv_import.status = 'Failed'
        csv_import.error_message = str(e)
        db.session.commit()
        return False, f"Error processing CSV: {str(e)}"

@app.route('/settings')
@login_required
def account_settings():
    """Account settings page"""
    user_settings = {
        setting.setting_key: setting.setting_value 
        for setting in current_user.settings
    }
    
    log_activity('settings_view', 'Viewed account settings')
    
    return render_template('settings/index.html', user_settings=user_settings)

@app.route('/settings/update', methods=['POST'])
@login_required
def update_settings():
    """Update user settings"""
    try:
        # Update profile information
        current_user.first_name = request.form.get('first_name')
        current_user.last_name = request.form.get('last_name')
        current_user.company_name = request.form.get('company_name')
        current_user.phone = request.form.get('phone')
        current_user.timezone = request.form.get('timezone', 'UTC')
        current_user.updated_at = datetime.utcnow()
        
        # Update user settings
        settings_to_update = [
            'email_notifications', 'dashboard_refresh_rate', 
            'default_currency', 'date_format'
        ]
        
        for setting_key in settings_to_update:
            value = request.form.get(setting_key)
            if value is not None:
                setting = UserSetting.query.filter_by(
                    user_id=current_user.id, setting_key=setting_key
                ).first()
                
                if setting:
                    setting.setting_value = value
                    setting.updated_at = datetime.utcnow()
                else:
                    setting = UserSetting(
                        user_id=current_user.id,
                        setting_key=setting_key,
                        setting_value=value
                    )
                    db.session.add(setting)
        
        db.session.commit()
        log_activity('settings_update', 'Updated account settings')
        flash('Settings updated successfully', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash('Error updating settings', 'error')
        logging.error(f"Settings update error: {e}")
    
    return redirect(url_for('account_settings'))

@app.route('/notifications')
@login_required
def notifications():
    """Notifications page"""
    page = request.args.get('page', 1, type=int)
    notifications = Notification.query.filter_by(
        user_id=current_user.id
    ).order_by(Notification.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    log_activity('notifications_view', 'Viewed notifications')
    
    return render_template('notifications/index.html', notifications=notifications)

@app.route('/notifications/mark_read/<int:notification_id>')
@login_required
def mark_notification_read(notification_id):
    """Mark notification as read"""
    notification = Notification.query.filter_by(
        id=notification_id, user_id=current_user.id
    ).first_or_404()
    
    notification.is_read = True
    db.session.commit()
    
    return jsonify({'status': 'success'})

@app.route('/reports')
@login_required
def reports():
    """Advanced reports page"""
    # Date range from request or default to last 30 days
    end_date = request.args.get('end_date', datetime.now().strftime('%Y-%m-%d'))
    start_date = request.args.get('start_date', 
                                (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    
    start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # Get campaign data within date range
    campaigns_data = db.session.query(CampaignData).join(Campaign).filter(
        Campaign.user_id == current_user.id,
        CampaignData.date >= start_date,
        CampaignData.date <= end_date
    ).all()
    
    # Generate comprehensive report data
    report_data = generate_report_data(campaigns_data, start_date, end_date)
    
    log_activity('reports_view', f'Viewed reports for {start_date} to {end_date}')
    
    return render_template('reports/index.html',
                         report_data=report_data,
                         start_date=start_date,
                         end_date=end_date)

def generate_report_data(campaigns_data, start_date, end_date):
    """Generate comprehensive report data"""
    daily_metrics = {}
    platform_metrics = {}
    total_metrics = {
        'impressions': 0, 'clicks': 0, 'spent': 0, 'reach': 0
    }
    
    for data in campaigns_data:
        date_str = data.date.strftime('%Y-%m-%d')
        platform = data.campaign.platform
        
        # Daily metrics
        if date_str not in daily_metrics:
            daily_metrics[date_str] = {
                'impressions': 0, 'clicks': 0, 'spent': 0, 'reach': 0
            }
        
        daily_metrics[date_str]['impressions'] += data.impressions
        daily_metrics[date_str]['clicks'] += data.clicks
        daily_metrics[date_str]['spent'] += data.spent
        daily_metrics[date_str]['reach'] += data.reach
        
        # Platform metrics
        if platform not in platform_metrics:
            platform_metrics[platform] = {
                'impressions': 0, 'clicks': 0, 'spent': 0, 'reach': 0
            }
        
        platform_metrics[platform]['impressions'] += data.impressions
        platform_metrics[platform]['clicks'] += data.clicks
        platform_metrics[platform]['spent'] += data.spent
        platform_metrics[platform]['reach'] += data.reach
        
        # Total metrics
        total_metrics['impressions'] += data.impressions
        total_metrics['clicks'] += data.clicks
        total_metrics['spent'] += data.spent
        total_metrics['reach'] += data.reach
    
    # Calculate derived metrics
    for metrics in [total_metrics] + list(platform_metrics.values()):
        metrics['ctr'] = (metrics['clicks'] / metrics['impressions'] * 100) if metrics['impressions'] > 0 else 0
        metrics['cpc'] = (metrics['spent'] / metrics['clicks']) if metrics['clicks'] > 0 else 0
        metrics['cpm'] = (metrics['spent'] / metrics['impressions'] * 1000) if metrics['impressions'] > 0 else 0
        metrics['cpv'] = (metrics['spent'] / metrics['reach']) if metrics['reach'] > 0 else 0
    
    return {
        'daily_metrics': daily_metrics,
        'platform_metrics': platform_metrics,
        'total_metrics': total_metrics
    }

@app.route('/activity')
@login_required
def activity_log():
    """User activity log page"""
    page = request.args.get('page', 1, type=int)
    activities = ActivityLog.query.filter_by(
        user_id=current_user.id
    ).order_by(ActivityLog.created_at.desc()).paginate(
        page=page, per_page=50, error_out=False
    )
    
    return render_template('activity/index.html', activities=activities)

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500

@app.errorhandler(403)
def forbidden_error(error):
    return render_template('errors/403.html'), 403
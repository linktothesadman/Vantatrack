import os
from flask import render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from app import app, db
from models import Campaign, CampaignData, CSVImport, User
from csv_processor import process_csv_file
import logging

@app.route('/')
@login_required
def dashboard():
    """Main dashboard view"""
    # Get user's campaigns
    campaigns = Campaign.query.filter_by(user_id=current_user.id).all()
    
    # Calculate summary metrics
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
    cpa = cpc  # Using CPC as CPA proxy for now
    
    # Get recent campaign data for charts (last month)
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
            chart_data[date_str] = {'impressions': 0, 'clicks': 0}
        chart_data[date_str]['impressions'] += data.impressions
        chart_data[date_str]['clicks'] += data.clicks
    
    # Convert to lists for Chart.js
    dates = sorted(chart_data.keys())
    impressions_data = [chart_data[date]['impressions'] for date in dates]
    clicks_data = [chart_data[date]['clicks'] for date in dates]
    
    # Get platform distribution
    platform_stats = {}
    for campaign in campaigns:
        platform = campaign.platform
        if platform not in platform_stats:
            platform_stats[platform] = {
                'campaigns': 0,
                'budget': 0,
                'spent': 0,
                'impressions': 0,
                'clicks': 0
            }
        platform_stats[platform]['campaigns'] += 1
        platform_stats[platform]['budget'] += campaign.budget
        platform_stats[platform]['spent'] += campaign.spent
        platform_stats[platform]['impressions'] += campaign.impressions
        platform_stats[platform]['clicks'] += campaign.clicks
    
    return render_template('dashboard.html',
                         campaigns=campaigns,
                         total_impressions=total_impressions,
                         total_clicks=total_clicks,
                         total_reach=total_reach,
                         total_budget=total_budget,
                         total_spent=total_spent,
                         ctr=round(ctr, 2),
                         cpc=round(cpc, 2),
                         cpm=round(cpm, 2),
                         cpa=round(cpa, 2),
                         cpv=round(cpv, 2),
                         chart_dates=dates,
                         impressions_data=impressions_data,
                         clicks_data=clicks_data,
                         platform_stats=platform_stats)

@app.route('/reports')
@login_required
def reports():
    """Reports view with detailed campaign data"""
    platform_filter = request.args.get('platform', 'All')
    
    # Base query for user's campaigns
    query = Campaign.query.filter_by(user_id=current_user.id)
    
    # Apply platform filter
    if platform_filter and platform_filter != 'All':
        query = query.filter_by(platform=platform_filter)
    
    campaigns = query.order_by(Campaign.created_at.desc()).all()
    
    # Get available platforms for filter
    platforms = db.session.query(Campaign.platform).filter_by(user_id=current_user.id).distinct().all()
    platforms = [p[0] for p in platforms]
    
    return render_template('reports.html',
                         campaigns=campaigns,
                         platforms=platforms,
                         current_platform=platform_filter)

@app.route('/upload_csv', methods=['POST'])
@login_required
def upload_csv():
    """Handle CSV file upload"""
    if 'file' not in request.files:
        flash('No file selected', 'error')
        return redirect(url_for('dashboard'))
    
    file = request.files['file']
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('dashboard'))
    
    if file and file.filename.lower().endswith('.csv'):
        filename = secure_filename(file.filename)
        # Add timestamp to filename to avoid conflicts
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
        filename = timestamp + filename
        
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        
        # Ensure upload directory exists
        os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)
        
        file.save(filepath)
        
        # Create CSV import record
        csv_import = CSVImport(
            filename=filename,
            file_path=filepath,
            imported_by=current_user.id,
            status='Pending'
        )
        db.session.add(csv_import)
        db.session.commit()
        
        # Process the CSV file
        try:
            result = process_csv_file(filepath, current_user.id, csv_import.id)
            if result['success']:
                flash(f'CSV imported successfully! Processed {result["rows_processed"]} rows.', 'success')
            else:
                flash(f'CSV import failed: {result["error"]}', 'error')
        except Exception as e:
            logging.error(f"Error processing CSV: {str(e)}")
            flash(f'Error processing CSV: {str(e)}', 'error')
    else:
        flash('Please upload a valid CSV file', 'error')
    
    return redirect(url_for('dashboard'))

@app.route('/refresh_data', methods=['POST'])
@login_required
def refresh_data():
    """Manual data refresh endpoint"""
    try:
        # Here you would implement logic to refresh data from APIs
        # For now, we'll just update the updated_at timestamp for user's campaigns
        campaigns = Campaign.query.filter_by(user_id=current_user.id).all()
        for campaign in campaigns:
            campaign.updated_at = datetime.utcnow()
        
        db.session.commit()
        flash('Data refreshed successfully!', 'success')
        
    except Exception as e:
        logging.error(f"Error refreshing data: {str(e)}")
        flash(f'Error refreshing data: {str(e)}', 'error')
    
    return redirect(url_for('dashboard'))

@app.route('/api/campaign/<int:campaign_id>/data')
@login_required
def get_campaign_data(campaign_id):
    """API endpoint to get campaign data for charts"""
    campaign = Campaign.query.filter_by(id=campaign_id, user_id=current_user.id).first_or_404()
    
    # Get last 30 days of data
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=30)
    
    daily_data = CampaignData.query.filter_by(campaign_id=campaign_id).filter(
        CampaignData.date >= start_date,
        CampaignData.date <= end_date
    ).order_by(CampaignData.date).all()
    
    data = {
        'dates': [d.date.strftime('%Y-%m-%d') for d in daily_data],
        'impressions': [d.impressions for d in daily_data],
        'clicks': [d.clicks for d in daily_data],
        'spent': [float(d.spent) for d in daily_data]
    }
    
    return jsonify(data)

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('404.html'), 500

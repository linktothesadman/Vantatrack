import os
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
from app import app, db
from models import CSVImport, SystemSettings
from csv_processor import process_csv_file
import glob

# Global scheduler instance
scheduler = None

def start_scheduler():
    """Start the background scheduler for automatic CSV imports"""
    global scheduler
    
    if scheduler is not None:
        return  # Scheduler already started
    
    scheduler = BackgroundScheduler()
    
    # Add scheduled jobs
    add_scheduled_jobs()
    
    # Start the scheduler
    scheduler.start()
    logging.info("Background scheduler started")

def add_scheduled_jobs():
    """Add scheduled jobs to the scheduler"""
    global scheduler
    
    # Daily CSV import job at 2 AM
    scheduler.add_job(
        func=scheduled_csv_import,
        trigger=CronTrigger(hour=2, minute=0),
        id='daily_csv_import',
        name='Daily CSV Import',
        replace_existing=True
    )
    
    # Hourly data refresh job
    scheduler.add_job(
        func=scheduled_data_refresh,
        trigger=CronTrigger(minute=0),
        id='hourly_data_refresh',
        name='Hourly Data Refresh',
        replace_existing=True
    )
    
    logging.info("Scheduled jobs added")

def scheduled_csv_import():
    """Scheduled function to import CSV files from a designated directory"""
    with app.app_context():
        try:
            # Use the robust agency CSV processor
            from agency_csv_processor import process_agency_csv_files
            process_agency_csv_files()
            
        except Exception as e:
            logging.error(f"Agency CSV import failed: {str(e)}")

def scheduled_data_refresh():
    """Scheduled function to refresh data from APIs"""
    with app.app_context():
        try:
            # Here you would implement API calls to refresh campaign data
            # For now, we'll just update the last refresh timestamp
            
            setting = SystemSettings.query.filter_by(setting_key='last_auto_refresh').first()
            if not setting:
                setting = SystemSettings(
                    setting_key='last_auto_refresh',
                    description='Last automatic data refresh timestamp'
                )
                db.session.add(setting)
            
            setting.setting_value = datetime.utcnow().isoformat()
            db.session.commit()
            
            logging.info("Scheduled data refresh completed")
            
        except Exception as e:
            logging.error(f"Error in scheduled_data_refresh: {str(e)}")

def stop_scheduler():
    """Stop the background scheduler"""
    global scheduler
    
    if scheduler is not None:
        scheduler.shutdown()
        scheduler = None
        logging.info("Background scheduler stopped")

def get_scheduler_status():
    """Get the current status of the scheduler"""
    global scheduler
    
    if scheduler is None:
        return {'running': False, 'jobs': []}
    
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            'id': job.id,
            'name': job.name,
            'next_run': job.next_run_time.isoformat() if job.next_run_time else None
        })
    
    return {
        'running': scheduler.running,
        'jobs': jobs
    }

# Manual trigger functions
def trigger_csv_import():
    """Manually trigger CSV import"""
    with app.app_context():
        scheduled_csv_import()

def trigger_data_refresh():
    """Manually trigger data refresh"""
    with app.app_context():
        scheduled_data_refresh()

from app import app, db
from simple_csv_import import import_sample_csv
import logging

def initialize_application():
    """Initialize the application with sample data"""
    with app.app_context():
        try:
            # Create all database tables
            db.create_all()
            logging.info("Database tables created successfully")
            
            # Import sample CSV data
            success, message = import_sample_csv()
            if success:
                logging.info(f"Sample data imported: {message}")
            else:
                logging.error(f"Failed to import sample data: {message}")
            
            return True
        except Exception as e:
            logging.error(f"Failed to initialize application: {e}")
            return False

if __name__ == "__main__":
    initialize_application()
# VantaTrack Marketing Dashboard

## Overview

VantaTrack is a marketing dashboard application built with Flask that allows agencies to manage campaign data from multiple advertising platforms (Facebook, Google, ShareIT). The system enables agencies to upload CSV files containing campaign data for multiple clients, with automatic user assignment and comprehensive analytics.

## System Architecture

### Backend Architecture
- **Framework**: Flask with Python 3.11
- **Database**: SQLite (development) with planned PostgreSQL support
- **ORM**: SQLAlchemy with Flask-SQLAlchemy
- **Authentication**: Flask-Login with session-based authentication
- **File Processing**: Pandas for CSV data processing
- **Background Jobs**: APScheduler for automated tasks

### Frontend Architecture
- **Template Engine**: Jinja2 templates
- **CSS Framework**: Bootstrap 5.3.0
- **Icons**: Font Awesome 6.4.0
- **Charts**: Chart.js for data visualization
- **UI Pattern**: Server-side rendered pages with progressive enhancement

## Key Components

### Data Models
- **User**: Client accounts with authentication and profile information
- **Campaign**: Marketing campaigns with platform-specific metrics
- **CampaignData**: Time-series data for campaign performance
- **CSVImport**: Import tracking and status management

### Core Modules
- **Authentication System** (`auth.py`): User login/registration with email verification
- **Agency Management** (`agency_management.py`): Multi-client CSV upload system
- **CSV Processing** (`csv_processor.py`, `agency_csv_processor.py`): Automated data parsing and mapping
- **Dashboard Routes** (`routes.py`): Main application endpoints and views
- **Background Scheduler** (`scheduler.py`): Automated import and refresh jobs

### CSV Processing System
The application includes a sophisticated CSV processing system that:
- Automatically maps columns from different advertising platforms
- Supports Facebook Ads Manager, Google Ads, and ShareIT exports
- Handles multi-client data in single CSV files
- Provides flexible column mapping for various export formats

## Data Flow

### CSV Import Process
1. Agency uploads CSV file containing data for multiple clients
2. System validates required columns and data format
3. Background processor assigns campaigns to correct user accounts
4. Campaign data is aggregated and metrics are calculated
5. Dashboard displays updated analytics for each client

### User Access Pattern
1. Clients log in with their email credentials
2. System filters all data to show only campaigns belonging to logged-in user
3. Real-time metrics are calculated from aggregated campaign data
4. Charts and reports are generated dynamically

### Data Aggregation
- Campaign-level metrics: impressions, clicks, spend, reach
- Calculated KPIs: CTR, CPC, CPM, CPV, CPA
- Time-series analysis for trend identification
- Platform-specific performance comparisons

## External Dependencies

### Python Packages
- **flask**: Web framework and routing
- **flask-sqlalchemy**: Database ORM
- **flask-login**: Authentication management
- **pandas**: Data processing and CSV handling
- **apscheduler**: Background job scheduling
- **gunicorn**: Production WSGI server
- **psycopg2-binary**: PostgreSQL adapter (planned)

### Frontend Libraries
- **Bootstrap 5.3.0**: UI components and responsive layout
- **Font Awesome 6.4.0**: Icon library
- **Chart.js**: Data visualization and charts

### Platform Integrations
- Support for Facebook Ads Manager CSV exports
- Google Ads report compatibility
- ShareIT platform data integration
- Extensible column mapping for additional platforms

## Deployment Strategy

### Development Environment
- SQLite database for local development
- Flask development server with debug mode
- File-based uploads with local storage

### Production Environment
- Gunicorn WSGI server with autoscaling deployment
- PostgreSQL database for production data
- Automated CSV processing via scheduled jobs
- ProxyFix middleware for proper header handling

### Configuration Management
- Environment-based configuration
- Session secret management
- Upload folder configuration with size limits
- Database connection string management

## Changelog
- June 18, 2025. Initial setup

## User Preferences

Preferred communication style: Simple, everyday language.
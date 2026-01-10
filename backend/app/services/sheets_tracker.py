import os
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from google.oauth2 import service_account
import pandas as pd
from dotenv import load_dotenv

from app.utils.logger import setup_logger

load_dotenv()
logger = setup_logger(__name__)

class GoogleSheetsTracker:
    """Google Sheets integration for application tracking"""
    
    def __init__(self):
        self.credentials_path = os.getenv("GOOGLE_SHEETS_CREDENTIALS_PATH")
        self.spreadsheet_id = os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID")
        self.client = None
        self.spreadsheet = None
        self.worksheet = None
        
        # Define the column structure
        self.columns = [
            'Application ID',
            'Date Applied',
            'Company',
            'Position',
            'Location',
            'Job URL',
            'Application URL',
            'Status',
            'Response Date',
            'Interview Date',
            'Notes',
            'Salary Range',
            'Contact Person',
            'Contact Email',
            'Follow-up Date',
            'Application Method',
            'Resume Version',
            'Cover Letter',
            'Referral',
            'Score'
        ]
        
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Google Sheets client"""
        try:
            if not self.credentials_path or not os.path.exists(self.credentials_path):
                logger.warning("Google Sheets credentials not found. Sheet tracking will be disabled.")
                return
            
            # Define the scope
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive.file',
                'https://www.googleapis.com/auth/drive'
            ]
            
            # Load credentials
            with open(self.credentials_path, 'r') as f:
                credentials_info = json.load(f)
            
            credentials = service_account.Credentials.from_service_account_info(
                credentials_info,
                scopes=scope
            )
            
            # Initialize client
            self.client = gspread.authorize(credentials)
            
            # Open or create spreadsheet
            if self.spreadsheet_id:
                self.spreadsheet = self.client.open_by_key(self.spreadsheet_id)
            else:
                self._create_spreadsheet()
            
            # Get or create worksheet
            self._setup_worksheet()
            
            logger.info("Google Sheets tracker initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Google Sheets: {e}")
            self.client = None
    
    def _create_spreadsheet(self):
        """Create a new spreadsheet for tracking applications"""
        try:
            self.spreadsheet = self.client.create('ApplyEase Application Tracker')
            
            # Share with user's email (optional)
            # self.spreadsheet.share('user@example.com', perm_type='user', role='owner')
            
            logger.info(f"Created new spreadsheet: {self.spreadsheet.id}")
            # Save the spreadsheet ID for future use
            os.environ['GOOGLE_SHEETS_SPREADSHEET_ID'] = self.spreadsheet.id
            
        except Exception as e:
            logger.error(f"Failed to create spreadsheet: {e}")
            raise
    
    def _setup_worksheet(self):
        """Setup the worksheet with headers"""
        try:
            # Try to get existing worksheet
            worksheets = self.spreadsheet.worksheets()
            if worksheets:
                self.worksheet = worksheets[0]
                
                # Check if headers exist
                if self.worksheet.row_count == 0 or not self.worksheet.get('A1'):
                    self._add_headers()
            else:
                # Create new worksheet
                self.worksheet = self.spreadsheet.add_worksheet(
                    title='Applications',
                    rows=1000,
                    cols=len(self.columns)
                )
                self._add_headers()
            
        except Exception as e:
            logger.error(f"Failed to setup worksheet: {e}")
            raise
    
    def _add_headers(self):
        """Add column headers to the worksheet"""
        try:
            self.worksheet.update('A1:T1', [self.columns])
            
            # Format headers (bold, background color)
            self.worksheet.format('A1:T1', {
                'textFormat': {'bold': True},
                'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}
            })
            
            logger.info("Headers added to worksheet")
            
        except Exception as e:
            logger.error(f"Failed to add headers: {e}")
    
    def add_application(self, application_data: Dict[str, Any]) -> bool:
        """Add a new application to the tracker"""
        if not self.client or not self.worksheet:
            logger.warning("Google Sheets not initialized")
            return False
        
        try:
            # Prepare row data
            row = [
                application_data.get('id', ''),
                application_data.get('date_applied', datetime.utcnow().strftime('%Y-%m-%d')),
                application_data.get('company_name', ''),
                application_data.get('position', ''),
                application_data.get('location', ''),
                application_data.get('job_url', ''),
                application_data.get('application_url', ''),
                application_data.get('status', 'Applied'),
                application_data.get('response_date', ''),
                application_data.get('interview_date', ''),
                application_data.get('notes', ''),
                application_data.get('salary_range', ''),
                application_data.get('contact_person', ''),
                application_data.get('contact_email', ''),
                application_data.get('follow_up_date', ''),
                application_data.get('application_method', 'ApplyEase'),
                application_data.get('resume_version', ''),
                application_data.get('cover_letter', ''),
                application_data.get('referral', ''),
                application_data.get('score', '')
            ]
            
            # Append row to sheet
            self.worksheet.append_row(row)
            
            logger.info(f"Added application to tracker: {application_data.get('company_name')} - {application_data.get('position')}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add application: {e}")
            return False
    
    def update_application(self, application_id: str, updates: Dict[str, Any]) -> bool:
        """Update an existing application in the tracker"""
        if not self.client or not self.worksheet:
            logger.warning("Google Sheets not initialized")
            return False
        
        try:
            # Find the row with the application ID
            cell = self.worksheet.find(str(application_id))
            if not cell:
                logger.warning(f"Application {application_id} not found in tracker")
                return False
            
            row_num = cell.row
            
            # Update specific columns
            for key, value in updates.items():
                if key in ['status', 'response_date', 'interview_date', 'notes', 'follow_up_date']:
                    col_index = self.columns.index(key.replace('_', ' ').title()) + 1
                    self.worksheet.update_cell(row_num, col_index, str(value))
            
            logger.info(f"Updated application {application_id} in tracker")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update application: {e}")
            return False
    
    def get_applications(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Get applications from the tracker with optional filters"""
        if not self.client or not self.worksheet:
            logger.warning("Google Sheets not initialized")
            return []
        
        try:
            # Get all records
            records = self.worksheet.get_all_records()
            
            # Apply filters if provided
            if filters:
                filtered_records = []
                for record in records:
                    match = True
                    for key, value in filters.items():
                        if record.get(key) != value:
                            match = False
                            break
                    if match:
                        filtered_records.append(record)
                records = filtered_records
            
            return records
            
        except Exception as e:
            logger.error(f"Failed to get applications: {e}")
            return []
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get application statistics"""
        if not self.client or not self.worksheet:
            return {}
        
        try:
            records = self.worksheet.get_all_records()
            
            if not records:
                return {'total': 0}
            
            # Calculate statistics
            df = pd.DataFrame(records)
            
            stats = {
                'total': len(df),
                'by_status': df['Status'].value_counts().to_dict() if 'Status' in df else {},
                'by_company': df['Company'].value_counts().head(10).to_dict() if 'Company' in df else {},
                'by_month': {},
                'response_rate': 0,
                'average_response_time': None
            }
            
            # Calculate response rate
            if 'Status' in df:
                responded = df[df['Status'].isin(['Interview', 'Rejected', 'Offer'])]
                stats['response_rate'] = (len(responded) / len(df)) * 100 if len(df) > 0 else 0
            
            # Calculate applications by month
            if 'Date Applied' in df:
                df['Date Applied'] = pd.to_datetime(df['Date Applied'], errors='coerce')
                monthly = df.groupby(df['Date Applied'].dt.to_period('M')).size()
                stats['by_month'] = {str(k): v for k, v in monthly.to_dict().items()}
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {}
    
    def export_to_csv(self, filepath: str) -> bool:
        """Export tracker data to CSV file"""
        if not self.client or not self.worksheet:
            logger.warning("Google Sheets not initialized")
            return False
        
        try:
            records = self.worksheet.get_all_records()
            df = pd.DataFrame(records)
            df.to_csv(filepath, index=False)
            
            logger.info(f"Exported tracker data to {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export to CSV: {e}")
            return False
    
    def create_dashboard(self) -> bool:
        """Create a dashboard worksheet with charts and summary"""
        if not self.client or not self.spreadsheet:
            return False
        
        try:
            # Create or get dashboard worksheet
            try:
                dashboard = self.spreadsheet.worksheet('Dashboard')
            except:
                dashboard = self.spreadsheet.add_worksheet(
                    title='Dashboard',
                    rows=100,
                    cols=10
                )
            
            # Add summary statistics
            stats = self.get_statistics()
            
            summary_data = [
                ['Application Statistics', ''],
                ['Total Applications', stats.get('total', 0)],
                ['Response Rate', f"{stats.get('response_rate', 0):.1f}%"],
                ['', ''],
                ['Status Breakdown', 'Count']
            ]
            
            for status, count in stats.get('by_status', {}).items():
                summary_data.append([status, count])
            
            dashboard.update('A1:B20', summary_data)
            
            logger.info("Dashboard created/updated")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create dashboard: {e}")
            return False

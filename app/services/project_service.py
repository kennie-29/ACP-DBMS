import csv
import os
from ..models import Project
from datetime import datetime

class DataExportError(Exception):
    """Custom exception for data export failures."""
    pass

class ProjectService:
    """
    OOP Service for handling Project-related business logic.
    Demonstrates: OOP, Lambda, File Handling, Error Handling.
    """
    
    def __init__(self, upload_folder):
        self.upload_folder = upload_folder

    def get_all_projects_sorted(self):
        """Fetches all projects and sorts them using a lambda function."""
        projects = Project.query.all()
        # Lambda usage: Sort by given_fund (descending)
        sorted_projects = sorted(projects, key=lambda p: p.given_fund, reverse=True)
        return sorted_projects

    def export_projects_to_csv(self, filename='projects_export.csv'):
        """
        Exports sorted projects to a CSV file.
        Demonstrates: File Stream I/O, Context Managers.
        """
        try:
            projects = self.get_all_projects_sorted()
            filepath = os.path.join(self.upload_folder, filename)
            
            # File Handling with Context Manager
            with open(filepath, mode='w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['Project Title', 'Location', 'Status', 'Fund Allocated', 'Approval Date']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for proj in projects:
                    writer.writerow({
                        'Project Title': proj.request.proj_title,
                        'Location': proj.request.project_site,
                        'Status': proj.current_status,
                        'Fund Allocated': f"{proj.given_fund:.2f}",
                        'Approval Date': proj.approval_date.strftime('%Y-%m-%d')
                    })
            
            return filepath
            
        except IOError as e:
            # Error Handling
            raise DataExportError(f"Failed to write CSV file: {str(e)}")
        except Exception as e:
            raise DataExportError(f"Unexpected error during export: {str(e)}")

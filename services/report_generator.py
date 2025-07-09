import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging
import io
import os
from .sesame_api import SesameAPI

class ReportGenerator:
    def __init__(self):
        self.sesame_api = SesameAPI()
        self.logger = logging.getLogger(__name__)

    def _parse_datetime(self, date_str: str) -> Optional[datetime]:
        """Parse datetime string from API"""
        if not date_str:
            return None
            
        try:
            # Handle different datetime formats
            formats = [
                "%Y-%m-%dT%H:%M:%S%z",
                "%Y-%m-%dT%H:%M:%S.%f%z",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d %H:%M:%S"
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
                    
            return None
        except Exception as e:
            self.logger.error(f"Error parsing datetime {date_str}: {str(e)}")
            return None

    def _calculate_duration(self, start_time: datetime, end_time: datetime) -> timedelta:
        """Calculate duration between two datetime objects"""
        if not start_time or not end_time:
            return timedelta(0)
        return end_time - start_time

    def _format_duration(self, duration: timedelta) -> str:
        """Format duration as HH:MM:SS"""
        total_seconds = int(duration.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def _merge_breakfast_breaks(self, activities: List[Dict], breaks: List[Dict]) -> List[Dict]:
        """Merge breakfast break time with adjacent activities"""
        merged_activities = []
        
        # Sort activities and breaks by start time
        activities.sort(key=lambda x: self._parse_datetime(x.get('startTime', '')) or datetime.min)
        breaks.sort(key=lambda x: self._parse_datetime(x.get('startTime', '')) or datetime.min)
        
        for activity in activities:
            activity_start = self._parse_datetime(activity.get('startTime'))
            activity_end = self._parse_datetime(activity.get('endTime'))
            
            if not activity_start or not activity_end:
                continue
                
            # Find breakfast breaks that occur during or adjacent to this activity
            breakfast_breaks = []
            for break_entry in breaks:
                break_type = break_entry.get('type', '').lower()
                if 'breakfast' in break_type or 'desayuno' in break_type:
                    break_start = self._parse_datetime(break_entry.get('startTime'))
                    break_end = self._parse_datetime(break_entry.get('endTime'))
                    
                    if break_start and break_end:
                        # Check if break is adjacent to or overlaps with activity
                        if (break_start <= activity_end and break_end >= activity_start):
                            breakfast_breaks.append(break_entry)
            
            # Merge breakfast breaks with activity
            merged_activity = activity.copy()
            
            if breakfast_breaks:
                # Calculate total breakfast time
                total_breakfast_time = timedelta(0)
                for break_entry in breakfast_breaks:
                    break_start = self._parse_datetime(break_entry.get('startTime'))
                    break_end = self._parse_datetime(break_entry.get('endTime'))
                    if break_start and break_end:
                        total_breakfast_time += self._calculate_duration(break_start, break_end)
                
                # Add breakfast time to activity duration
                original_duration = self._calculate_duration(activity_start, activity_end)
                merged_activity['totalTime'] = original_duration + total_breakfast_time
                
                # Update activity notes to indicate breakfast break inclusion
                notes = merged_activity.get('notes', '')
                if notes:
                    notes += f" (Incluye {self._format_duration(total_breakfast_time)} de descanso de desayuno)"
                else:
                    notes = f"Incluye {self._format_duration(total_breakfast_time)} de descanso de desayuno"
                merged_activity['notes'] = notes
            
            merged_activities.append(merged_activity)
        
        return merged_activities

    def _get_employee_identification(self, employee: Dict) -> tuple:
        """Extract employee identification type and number"""
        identity_type = employee.get('identityNumberType', 'N/A')
        identity_number = employee.get('nid', employee.get('ssn', 'N/A'))
        
        # Map identity types to Spanish
        type_mapping = {
            'dni': 'DNI',
            'nie': 'NIE',
            'rut': 'RUT',
            'other': 'Otro'
        }
        
        return type_mapping.get(identity_type, identity_type), identity_number

    def generate_report(self, from_date: str = None, to_date: str = None, 
                       employee_id: str = None, company_id: str = None) -> Optional[bytes]:
        """Generate XLSX report with employee activities and merged breakfast breaks"""
        try:
            # Get token info to get company ID if not provided
            if not company_id:
                token_info = self.sesame_api.get_token_info()
                if token_info and token_info.get('data', {}).get('company', {}).get('id'):
                    company_id = token_info['data']['company']['id']
                else:
                    self.logger.error("Could not get company ID from token info")
                    return None

            # Get employees data
            if employee_id:
                employee_data = self.sesame_api.get_employee_details(employee_id)
                employees = [employee_data['data']] if employee_data else []
            else:
                employees = self.sesame_api.get_all_employees_data(company_id=company_id)

            if not employees:
                self.logger.error("No employees found")
                return None

            # Create workbook and worksheet
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Reporte de Actividades"

            # Define headers
            headers = [
                "Empleado",
                "Tipo de Identificación",
                "Nº de Identificación",
                "Fecha",
                "Actividad",
                "Grupo",
                "Entrada",
                "Salida",
                "Tiempo registrado"
            ]

            # Add headers with styling
            for col, header in enumerate(headers, 1):
                cell = ws.cell(row=1, column=col, value=header)
                cell.font = Font(bold=True)
                cell.fill = PatternFill(start_color="CCCCCC", end_color="CCCCCC", fill_type="solid")
                cell.alignment = Alignment(horizontal="center")

            # Process data for each employee
            row = 2
            for employee in employees:
                emp_id = employee.get('id')
                emp_name = f"{employee.get('firstName', '')} {employee.get('lastName', '')}".strip()
                identity_type, identity_number = self._get_employee_identification(employee)

                # Get time tracking data
                time_entries = self.sesame_api.get_all_time_tracking_data(
                    employee_id=emp_id,
                    company_id=company_id,
                    from_date=from_date,
                    to_date=to_date
                )

                # Get break data
                break_entries = self.sesame_api.get_all_breaks_data(
                    employee_id=emp_id,
                    company_id=company_id,
                    from_date=from_date,
                    to_date=to_date
                )

                # Merge breakfast breaks with activities
                merged_activities = self._merge_breakfast_breaks(time_entries, break_entries)

                # Add data to worksheet
                for activity in merged_activities:
                    start_time = self._parse_datetime(activity.get('startTime'))
                    end_time = self._parse_datetime(activity.get('endTime'))
                    
                    if not start_time:
                        continue

                    # Get activity details
                    activity_name = activity.get('activity', {}).get('name', 'N/A')
                    activity_group = activity.get('activity', {}).get('group', {}).get('name', 'N/A')
                    
                    # Calculate registered time
                    if 'totalTime' in activity:
                        registered_time = self._format_duration(activity['totalTime'])
                    elif end_time:
                        registered_time = self._format_duration(self._calculate_duration(start_time, end_time))
                    else:
                        registered_time = "N/A"

                    # Add row data
                    ws.cell(row=row, column=1, value=emp_name)
                    ws.cell(row=row, column=2, value=identity_type)
                    ws.cell(row=row, column=3, value=identity_number)
                    ws.cell(row=row, column=4, value=start_time.strftime("%Y-%m-%d") if start_time else "N/A")
                    ws.cell(row=row, column=5, value=activity_name)
                    ws.cell(row=row, column=6, value=activity_group)
                    ws.cell(row=row, column=7, value=start_time.strftime("%H:%M:%S") if start_time else "N/A")
                    ws.cell(row=row, column=8, value=end_time.strftime("%H:%M:%S") if end_time else "N/A")
                    ws.cell(row=row, column=9, value=registered_time)

                    row += 1

            # Auto-adjust column widths
            for column in ws.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                ws.column_dimensions[column_letter].width = adjusted_width

            # Save to bytes
            excel_buffer = io.BytesIO()
            wb.save(excel_buffer)
            excel_buffer.seek(0)
            
            return excel_buffer.getvalue()

        except Exception as e:
            self.logger.error(f"Error generating report: {str(e)}")
            return None

    def test_connection(self) -> Dict:
        """Test API connection and return status"""
        try:
            token_info = self.sesame_api.get_token_info()
            if token_info:
                return {
                    "status": "success",
                    "message": "Connection successful",
                    "company": token_info.get('data', {}).get('company', {}).get('name', 'Unknown')
                }
            else:
                return {
                    "status": "error",
                    "message": "Failed to connect to Sesame API"
                }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Connection test failed: {str(e)}"
            }

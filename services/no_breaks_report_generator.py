import openpyxl
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from io import BytesIO
from openpyxl.styles import Font, PatternFill, Alignment
from services.sesame_api import SesameAPI

class NoBreaksReportGenerator:
    def __init__(self):
        self.sesame_api = SesameAPI()
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.INFO)

    def generate_report(self, from_date: str = None, to_date: str = None, 
                       employee_id: str = None, office_id: str = None, 
                       department_id: str = None, report_type: str = "by_employee") -> Optional[bytes]:
        """Generate report without work-breaks calls"""
        
        try:
            self.logger.info("=== GENERANDO REPORTE SIN WORK-BREAKS ===")
            
            # Step 1: Get employees
            if employee_id:
                employee_response = self.sesame_api.get_employee_details(employee_id)
                employees = [employee_response.get('data')] if employee_response else []
            else:
                employees_response = self.sesame_api.get_employees(page=1, per_page=100)
                employees = employees_response.get('data', []) if employees_response else []
                
                # Apply filters
                if office_id:
                    employees = [emp for emp in employees if emp.get('office', {}).get('id') == office_id]
                if department_id:
                    employees = [emp for emp in employees if emp.get('department', {}).get('id') == department_id]
            
            if not employees:
                return self._create_empty_report()
            
            # Step 2: Get work entries only (no breaks)
            all_employee_data = {}
            for employee in employees:
                emp_id = employee.get('id')
                emp_name = f"{employee.get('firstName', '')} {employee.get('lastName', '')}".strip()
                
                self.logger.info(f"Procesando empleado: {emp_name}")
                
                # Get time entries only
                time_entries = self.sesame_api.get_all_time_tracking_data(
                    employee_id=emp_id,
                    from_date=from_date,
                    to_date=to_date
                )
                
                all_employee_data[emp_id] = {
                    'employee': employee,
                    'time_entries': time_entries or []
                }
            
            # Step 3: Create Excel report
            self.logger.info("Generando archivo Excel...")
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Reporte Sin Breaks"
            
            # Headers
            headers = ["Empleado", "Tipo ID", "Número ID", "Fecha", "Actividad", "Grupo", "Entrada", "Salida", "Tiempo Registrado"]
            for col, header in enumerate(headers, 1):
                cell = ws.cell(row=1, column=col, value=header)
                cell.font = Font(bold=True)
                cell.fill = PatternFill(start_color="CCCCCC", end_color="CCCCCC", fill_type="solid")
            
            current_row = 2
            
            # Process employee data
            for emp_id, data in all_employee_data.items():
                employee = data['employee']
                emp_name = f"{employee.get('firstName', '')} {employee.get('lastName', '')}".strip()
                identity_type, identity_number = self._get_employee_identification(employee)
                
                time_entries = data['time_entries']
                
                if time_entries:
                    # Group by date
                    entries_by_date = {}
                    for entry in time_entries:
                        work_in = entry.get('workEntryIn', {}) if entry.get('workEntryIn') else {}
                        if work_in and work_in.get('date'):
                            try:
                                parsed_date = self._parse_datetime(work_in.get('date'))
                                if parsed_date:
                                    date_key = parsed_date.strftime('%Y-%m-%d')
                                    if date_key not in entries_by_date:
                                        entries_by_date[date_key] = []
                                    entries_by_date[date_key].append(entry)
                            except Exception:
                                continue
                    
                    # Process each date
                    for date_key in sorted(entries_by_date.keys()):
                        date_entries = entries_by_date[date_key]
                        
                        for entry in date_entries:
                            work_in = entry.get('workEntryIn', {}) if entry.get('workEntryIn') else {}
                            work_out = entry.get('workEntryOut', {}) if entry.get('workEntryOut') else {}
                            
                            start_time = self._parse_datetime(work_in.get('date')) if work_in else None
                            end_time = self._parse_datetime(work_out.get('date')) if work_out else None
                            
                            # Skip entries without start time
                            if not start_time:
                                continue
                            
                            # Calculate duration
                            duration_str = "00:00:00"
                            end_time_str = "--"
                            
                            if start_time and end_time:
                                duration = end_time - start_time
                                entry_seconds = duration.total_seconds()
                                hours = int(entry_seconds // 3600)
                                minutes = int((entry_seconds % 3600) // 60)
                                seconds = int(entry_seconds % 60)
                                duration_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                                end_time_str = end_time.strftime("%H:%M:%S")
                            
                            # Write to Excel
                            ws.cell(row=current_row, column=1, value=emp_name)
                            ws.cell(row=current_row, column=2, value=identity_type)
                            ws.cell(row=current_row, column=3, value=identity_number)
                            ws.cell(row=current_row, column=4, value=date_key)
                            ws.cell(row=current_row, column=5, value=entry.get('workEntryType', 'No especificado'))
                            ws.cell(row=current_row, column=6, value="")  # Group - empty
                            ws.cell(row=current_row, column=7, value=start_time.strftime("%H:%M:%S"))
                            ws.cell(row=current_row, column=8, value=end_time_str)
                            ws.cell(row=current_row, column=9, value=duration_str)
                            
                            current_row += 1
            
            # Save to BytesIO
            output = BytesIO()
            wb.save(output)
            output.seek(0)
            
            self.logger.info(f"Reporte generado exitosamente con {current_row - 2} registros")
            return output.getvalue()
            
        except Exception as e:
            self.logger.error(f"Error generating report: {str(e)}")
            return self._create_error_report(str(e))

    def _create_empty_report(self) -> bytes:
        """Create an empty report when no data is found"""
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Reporte Vacío"
        
        ws.cell(row=1, column=1, value="No se encontraron datos para los filtros especificados")
        
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        return output.getvalue()

    def _create_error_report(self, error_message: str) -> bytes:
        """Create an error report"""
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Error"
        
        ws.cell(row=1, column=1, value=f"Error al generar reporte: {error_message}")
        
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        return output.getvalue()

    def _parse_datetime(self, date_str: str) -> Optional[datetime]:
        """Parse datetime string from API"""
        if not date_str:
            return None
        
        try:
            # Handle different datetime formats
            if date_str.endswith('Z'):
                date_str = date_str.replace('Z', '+00:00')
            
            return datetime.fromisoformat(date_str)
        except Exception:
            return None

    def _get_employee_identification(self, employee: Dict) -> tuple:
        """Extract employee identification type and number"""
        identification_type = employee.get('identityNumberType', 'DNI')
        identification_number = employee.get('nid', employee.get('id', 'No disponible'))
        
        return identification_type, identification_number
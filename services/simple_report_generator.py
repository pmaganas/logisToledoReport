import openpyxl
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from io import BytesIO
from openpyxl.styles import Font, PatternFill, Alignment
from services.sesame_api import SesameAPI

class SimpleReportGenerator:
    def __init__(self):
        self.sesame_api = SesameAPI()
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.INFO)

    def generate_simple_report(self, from_date: str = None, to_date: str = None, 
                             employee_id: str = None, office_id: str = None, 
                             department_id: str = None, report_type: str = "by_employee") -> Optional[bytes]:
        """Generate a simplified XLSX report with reduced API calls"""
        
        try:
            self.logger.info(f"Starting simple report generation - Type: {report_type}")
            
            # Get employees data
            if employee_id:
                employee_response = self.sesame_api.get_employee_details(employee_id)
                employees = [employee_response.get('data')] if employee_response else []
            else:
                # Get limited employee data to avoid timeout
                employees_response = self.sesame_api.get_employees(page=1, per_page=50)
                all_employees = employees_response.get('data', []) if employees_response else []
                
                employees = []
                for employee in all_employees:
                    include_employee = True
                    
                    # Filter by office_id
                    if office_id:
                        employee_office_id = employee.get('office', {}).get('id') if employee.get('office') else None
                        if employee_office_id != office_id:
                            include_employee = False
                    
                    # Filter by department_id
                    if department_id and include_employee:
                        employee_department_id = employee.get('department', {}).get('id') if employee.get('department') else None
                        if employee_department_id != department_id:
                            include_employee = False
                    
                    if include_employee:
                        employees.append(employee)
                        
                    # Limit to 20 employees for stability
                    if len(employees) >= 20:
                        break
            
            if not employees:
                self.logger.warning("No employees found")
                return self._create_empty_report()
            
            self.logger.info(f"Processing {len(employees)} employees")
            
            # Create workbook and worksheet
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Reporte Simplificado"
            
            # Headers
            headers = ["Empleado", "Tipo ID", "Número ID", "Fecha", "Horas Trabajadas", "Estado"]
            for col, header in enumerate(headers, 1):
                cell = ws.cell(row=1, column=col, value=header)
                cell.font = Font(bold=True)
                cell.fill = PatternFill(start_color="CCCCCC", end_color="CCCCCC", fill_type="solid")
                cell.alignment = Alignment(horizontal="center")
            
            current_row = 2
            
            # Process each employee
            for i, employee in enumerate(employees, 1):
                emp_id = employee.get('id')
                emp_name = f"{employee.get('firstName', '')} {employee.get('lastName', '')}".strip()
                identity_type, identity_number = self._get_employee_identification(employee)
                
                self.logger.info(f"Processing employee {i}/{len(employees)}: {emp_name}")
                
                try:
                    # Get limited time tracking data
                    time_response = self.sesame_api.get_time_tracking(
                        employee_id=emp_id,
                        from_date=from_date,
                        to_date=to_date,
                        page=1,
                        limit=30  # Reduced limit
                    )
                    time_entries = time_response.get('data', []) if time_response else []
                    
                    if time_entries:
                        # Group by date and calculate hours
                        date_hours = {}
                        for entry in time_entries:
                            date_key = entry.get('date', 'Unknown')
                            if date_key not in date_hours:
                                date_hours[date_key] = 0
                            
                            # Simple hour calculation
                            work_in = entry.get('workEntryIn', {})
                            work_out = entry.get('workEntryOut', {})
                            
                            if work_in and work_out:
                                start_time = self._parse_datetime(work_in.get('date'))
                                end_time = self._parse_datetime(work_out.get('date'))
                                
                                if start_time and end_time:
                                    duration = end_time - start_time
                                    hours = duration.total_seconds() / 3600
                                    date_hours[date_key] += hours
                        
                        # Add rows for each date
                        for date_str, hours in date_hours.items():
                            ws.cell(row=current_row, column=1, value=emp_name)
                            ws.cell(row=current_row, column=2, value=identity_type)
                            ws.cell(row=current_row, column=3, value=identity_number)
                            ws.cell(row=current_row, column=4, value=date_str)
                            ws.cell(row=current_row, column=5, value=f"{hours:.2f}")
                            ws.cell(row=current_row, column=6, value="Procesado")
                            current_row += 1
                    else:
                        # No data for this employee
                        ws.cell(row=current_row, column=1, value=emp_name)
                        ws.cell(row=current_row, column=2, value=identity_type)
                        ws.cell(row=current_row, column=3, value=identity_number)
                        ws.cell(row=current_row, column=4, value="Sin datos")
                        ws.cell(row=current_row, column=5, value="0.00")
                        ws.cell(row=current_row, column=6, value="Sin registros")
                        current_row += 1
                        
                except Exception as e:
                    self.logger.error(f"Error processing employee {emp_name}: {str(e)}")
                    # Add error row
                    ws.cell(row=current_row, column=1, value=emp_name)
                    ws.cell(row=current_row, column=2, value=identity_type)
                    ws.cell(row=current_row, column=3, value=identity_number)
                    ws.cell(row=current_row, column=4, value="Error")
                    ws.cell(row=current_row, column=5, value="0.00")
                    ws.cell(row=current_row, column=6, value="Error al procesar")
                    current_row += 1
            
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
            output = BytesIO()
            wb.save(output)
            output.seek(0)
            
            self.logger.info("Simple report generated successfully")
            return output.getvalue()
            
        except Exception as e:
            self.logger.error(f"Error generating simple report: {str(e)}")
            return self._create_error_report(str(e))

    def _create_empty_report(self) -> bytes:
        """Create an empty report when no data is found"""
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Reporte Vacío"
        
        ws.cell(row=1, column=1, value="No se encontraron empleados")
        ws.cell(row=2, column=1, value="Verifique los filtros aplicados")
        
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        return output.getvalue()

    def _create_error_report(self, error_message: str) -> bytes:
        """Create an error report"""
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Error"
        
        ws.cell(row=1, column=1, value="Error al generar el reporte")
        ws.cell(row=2, column=1, value=error_message)
        
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        return output.getvalue()

    def _parse_datetime(self, date_str: str) -> Optional[datetime]:
        """Parse datetime string from API"""
        if not date_str:
            return None
        
        try:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except ValueError:
            try:
                return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                return None

    def _get_employee_identification(self, employee: Dict) -> tuple:
        """Extract employee identification type and number"""
        identification = employee.get('identification', {})
        if identification:
            return identification.get('type', 'Sin tipo'), identification.get('number', 'Sin número')
        return 'Sin tipo', 'Sin número'
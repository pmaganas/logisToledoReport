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
        """Generate report with only work entries - no employee data processing"""
        
        try:
            self.logger.info("=== GENERANDO REPORTE SOLO CON FICHAJES ===")
            
            # Get work entries with safe incremental loading
            self.logger.info("=== INICIANDO FETCH INCREMENTAL DE REGISTROS ===")
            self.logger.info(f"Parámetros: employee_id={employee_id}, from_date={from_date}, to_date={to_date}")
            
            all_work_entries = []
            page = 1
            max_safe_pages = 100  # Limite aumentado para 10,000 registros
            
            while page <= max_safe_pages:
                try:
                    response = self.sesame_api.get_time_tracking(
                        employee_id=employee_id,
                        from_date=from_date,
                        to_date=to_date,
                        page=page,
                        limit=100
                    )
                    
                    if not response or not response.get('data'):
                        self.logger.info(f"No más datos en página {page}, terminando")
                        break
                    
                    entries = response['data']
                    all_work_entries.extend(entries)
                    self.logger.info(f"Página {page}: {len(entries)} registros, total: {len(all_work_entries)}")
                    
                    # Verificar si hay más páginas
                    meta = response.get('meta', {})
                    if page >= meta.get('lastPage', 1):
                        self.logger.info(f"Llegamos a la última página ({meta.get('lastPage', 1)})")
                        break
                    
                    # Si no hay suficientes registros, terminamos
                    if len(entries) < 100:
                        self.logger.info(f"Página {page} tiene menos de 100 registros, terminando")
                        break
                    
                    page += 1
                    
                except Exception as e:
                    self.logger.error(f"Error en página {page}: {str(e)}")
                    if page == 1:
                        # Si falla la primera página, es un error crítico
                        raise e
                    else:
                        # Si falla una página posterior, continuamos con lo que tenemos
                        self.logger.warning(f"Continuando con {len(all_work_entries)} registros obtenidos hasta página {page-1}")
                        break
            
            if all_work_entries:
                self.logger.info(f"=== COMPLETADO: {len(all_work_entries)} registros obtenidos en {page-1} páginas ===")
            else:
                self.logger.warning("=== NO SE OBTUVIERON REGISTROS ===")
                return self._create_empty_report()

            if not all_work_entries:
                return self._create_empty_report()

            # Get check types for activity name resolution (limit to first 100 to save API calls)
            check_types_response = self.sesame_api.get_check_types(page=1, per_page=100)
            check_types_map = {}
            if check_types_response and check_types_response.get('data'):
                for check_type in check_types_response['data']:
                    check_types_map[check_type.get('id')] = check_type.get(
                        'name', 'Actividad no especificada')

            self.logger.info(f"Processing {len(all_work_entries)} fichajes for report")
            self.logger.info(f"Loaded {len(check_types_map)} check types")
            
            # Step 3: Create Excel report
            self.logger.info("Generando archivo Excel...")
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Reporte Fichajes"
            
            # Headers (same as preview)
            headers = ["Empleado", "Tipo ID", "Nº ID", "Fecha", "Actividad", "Grupo", "Entrada", "Salida", "Tiempo Registrado"]
            for col, header in enumerate(headers, 1):
                cell = ws.cell(row=1, column=col, value=header)
                cell.font = Font(bold=True)
                cell.fill = PatternFill(start_color="CCCCCC", end_color="CCCCCC", fill_type="solid")
            
            current_row = 2
            
            # Process work entries directly (fichajes only)
            for entry in all_work_entries:
                # Get employee info from the work entry
                employee_info = entry.get('employee', {})
                employee_name = f"{employee_info.get('firstName', '')} {employee_info.get('lastName', '')}".strip()
                
                if not employee_name:
                    employee_name = "Empleado desconocido"

                # Extract employee identification
                employee_nid = employee_info.get('nid', 'No disponible')
                employee_id_type = employee_info.get('identityNumberType', 'DNI')

                # Extract date from workEntryIn.date (same as preview)
                entry_date = "No disponible"
                if entry.get('workEntryIn') and entry['workEntryIn'].get('date'):
                    try:
                        entry_datetime = datetime.fromisoformat(
                            entry['workEntryIn']['date'].replace('Z', '+00:00'))
                        entry_date = entry_datetime.strftime('%Y-%m-%d')
                    except Exception as e:
                        self.logger.error(f"Error parsing entry date: {e}")
                        entry_date = "Error en fecha"

                # Get activity name from workCheckTypeId using check types mapping (same as preview)
                activity_name = "Actividad no especificada"
                work_check_type_id = entry.get('workCheckTypeId')
                if work_check_type_id and work_check_type_id in check_types_map:
                    activity_name = check_types_map[work_check_type_id]
                elif entry.get('workEntryType'):
                    activity_name = entry.get('workEntryType', 'Actividad no especificada')

                # Group name left empty as requested (same as preview)
                group_name = ""

                # Extract times from workEntryIn and workEntryOut (same as preview)
                start_time = "No disponible"
                end_time = "No disponible"

                if entry.get('workEntryIn') and entry['workEntryIn'].get('date'):
                    try:
                        start_datetime = datetime.fromisoformat(
                            entry['workEntryIn']['date'].replace('Z', '+00:00'))
                        start_time = start_datetime.strftime('%H:%M:%S')
                    except Exception as e:
                        self.logger.error(f"Error parsing start time: {e}")
                        start_time = "Error en hora"

                if entry.get('workEntryOut') and entry['workEntryOut'].get('date'):
                    try:
                        end_datetime = datetime.fromisoformat(
                            entry['workEntryOut']['date'].replace('Z', '+00:00'))
                        end_time = end_datetime.strftime('%H:%M:%S')
                    except Exception as e:
                        self.logger.error(f"Error parsing end time: {e}")
                        end_time = "Error en hora"

                # Calculate duration (same as preview)
                final_duration = "No disponible"
                if entry.get('workedSeconds') is not None:
                    try:
                        worked_seconds = entry['workedSeconds']
                        final_duration = self._format_duration(timedelta(seconds=worked_seconds))
                    except Exception as e:
                        self.logger.error(f"Error calculating duration: {e}")
                        final_duration = "Error en duración"
                        
                # Write to Excel
                ws.cell(row=current_row, column=1, value=employee_name)
                ws.cell(row=current_row, column=2, value=employee_id_type)
                ws.cell(row=current_row, column=3, value=employee_nid)
                ws.cell(row=current_row, column=4, value=entry_date)
                ws.cell(row=current_row, column=5, value=activity_name)
                ws.cell(row=current_row, column=6, value=group_name)
                ws.cell(row=current_row, column=7, value=start_time)
                ws.cell(row=current_row, column=8, value=end_time)
                ws.cell(row=current_row, column=9, value=final_duration)
                
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

    def _format_duration(self, duration):
        """Format duration as HH:MM:SS - same as preview"""
        if isinstance(duration, timedelta):
            total_seconds = int(duration.total_seconds())
        else:
            total_seconds = int(duration)

        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60

        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
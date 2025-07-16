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
                        limit=300
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
                    if len(entries) < 300:
                        self.logger.info(f"Página {page} tiene menos de 300 registros, terminando")
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
            
            # Group entries by employee and date
            current_row = self._process_grouped_entries(ws, all_work_entries, check_types_map, current_row)
            
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

    def _redistribute_pause_time(self, entries: List[Dict]) -> List[Dict]:
        """Redistribute pause time by eliminating gaps and adjusting adjacent work entries"""
        if not entries:
            return entries
        
        processed_entries = []
        i = 0
        
        while i < len(entries):
            entry = entries[i]
            work_entry_type = entry.get('workEntryType', '')
            
            if work_entry_type == 'pause':
                # This is a pause entry - adjust adjacent work entries to eliminate gap
                pause_start = self._get_entry_start_time(entry)
                pause_end = self._get_entry_end_time(entry)
                
                if pause_start and pause_end:
                    # Find previous work entry
                    prev_entry = self._find_previous_work_entry(entries, i)
                    # Find next work entry
                    next_entry = self._find_next_work_entry(entries, i)
                    
                    if prev_entry and next_entry:
                        # Extend previous entry to end when pause starts
                        # Move next entry to start when pause starts
                        self._extend_entry_to_time(prev_entry, pause_end)
                        self._move_entry_start_to_time(next_entry, pause_start)
                        self.logger.info(f"Eliminated pause gap by connecting adjacent work entries")
                    elif prev_entry:
                        # Only previous entry exists - extend it by pause duration
                        pause_duration = self._get_entry_duration_seconds(entry)
                        self._extend_entry_by_duration(prev_entry, pause_duration)
                        self.logger.info(f"Extended previous work entry by {pause_duration} seconds")
                    elif next_entry:
                        # Only next entry exists - move it to start when pause started
                        self._move_entry_start_to_time(next_entry, pause_start)
                        self.logger.info(f"Moved next work entry to eliminate pause gap")
                
                # Skip adding this pause entry to processed_entries
                i += 1
                continue
            else:
                # This is a work entry - add it to processed entries
                processed_entries.append(entry)
                i += 1
        
        return processed_entries

    def _get_entry_duration_seconds(self, entry: Dict) -> int:
        """Get the duration of an entry in seconds"""
        try:
            work_entry_in = entry.get('workEntryIn', {})
            work_entry_out = entry.get('workEntryOut', {})
            
            if not work_entry_in.get('date') or not work_entry_out.get('date'):
                return 0
            
            in_time = datetime.fromisoformat(work_entry_in['date'].replace('Z', '+00:00'))
            out_time = datetime.fromisoformat(work_entry_out['date'].replace('Z', '+00:00'))
            
            duration = out_time - in_time
            return int(duration.total_seconds())
        except Exception as e:
            self.logger.error(f"Error calculating entry duration: {e}")
            return 0

    def _get_entry_start_time(self, entry: Dict) -> Optional[datetime]:
        """Get the start time of an entry"""
        try:
            work_entry_in = entry.get('workEntryIn', {})
            if work_entry_in.get('date'):
                return datetime.fromisoformat(work_entry_in['date'].replace('Z', '+00:00'))
        except Exception:
            pass
        return None

    def _get_entry_end_time(self, entry: Dict) -> Optional[datetime]:
        """Get the end time of an entry"""
        try:
            work_entry_out = entry.get('workEntryOut', {})
            if work_entry_out.get('date'):
                return datetime.fromisoformat(work_entry_out['date'].replace('Z', '+00:00'))
        except Exception:
            pass
        return None

    def _find_previous_work_entry(self, entries: List[Dict], pause_index: int) -> Optional[Dict]:
        """Find the previous work entry before the pause"""
        for i in range(pause_index - 1, -1, -1):
            if entries[i].get('workEntryType', '') != 'pause':
                return entries[i]
        return None

    def _find_next_work_entry(self, entries: List[Dict], pause_index: int) -> Optional[Dict]:
        """Find the next work entry after the pause"""
        for i in range(pause_index + 1, len(entries)):
            if entries[i].get('workEntryType', '') != 'pause':
                return entries[i]
        return None

    def _extend_entry_to_time(self, entry: Dict, end_time: datetime):
        """Extend a work entry to end at the specified time"""
        try:
            work_entry_out = entry.get('workEntryOut', {})
            if work_entry_out:
                work_entry_out['date'] = end_time.isoformat().replace('+00:00', 'Z')
        except Exception as e:
            self.logger.error(f"Error extending entry to time: {e}")

    def _move_entry_start_to_time(self, entry: Dict, start_time: datetime):
        """Move a work entry to start at the specified time"""
        try:
            work_entry_in = entry.get('workEntryIn', {})
            if work_entry_in:
                work_entry_in['date'] = start_time.isoformat().replace('+00:00', 'Z')
        except Exception as e:
            self.logger.error(f"Error moving entry start time: {e}")

    def _extend_entry_by_duration(self, entry: Dict, duration_seconds: int):
        """Extend a work entry by the specified duration"""
        try:
            work_entry_out = entry.get('workEntryOut', {})
            if work_entry_out and work_entry_out.get('date'):
                end_time = datetime.fromisoformat(work_entry_out['date'].replace('Z', '+00:00'))
                new_end_time = end_time + timedelta(seconds=duration_seconds)
                work_entry_out['date'] = new_end_time.isoformat().replace('+00:00', 'Z')
        except Exception as e:
            self.logger.error(f"Error extending entry by duration: {e}")

    def _get_entry_sort_key(self, entry: Dict):
        """Get sort key for chronological ordering by entry start time"""
        try:
            work_entry_in = entry.get('workEntryIn', {})
            if work_entry_in and work_entry_in.get('date'):
                # Parse the datetime and return it for sorting
                parsed_time = datetime.fromisoformat(work_entry_in['date'].replace('Z', '+00:00'))
                return parsed_time
        except Exception as e:
            self.logger.error(f"Error parsing entry date for sorting: {e}")
        
        # Return a very old datetime as fallback for entries without valid dates
        return datetime.min.replace(tzinfo=datetime.now().astimezone().tzinfo)

    def _process_grouped_entries(self, ws, all_work_entries, check_types_map, current_row):
        """Process entries grouped by employee, redistributing pause time"""
        # Group entries by employee only (not by date to handle night shifts properly)
        grouped_entries = {}
        
        for entry in all_work_entries:
            # Get employee info
            employee_info = entry.get('employee', {})
            employee_name = f"{employee_info.get('firstName', '')} {employee_info.get('lastName', '')}".strip()
            employee_id = employee_info.get('id', 'unknown')
            
            if not employee_name:
                employee_name = "Empleado desconocido"
            
            # Create group key by employee only
            group_key = f"{employee_id}"
            
            if group_key not in grouped_entries:
                grouped_entries[group_key] = {
                    'employee_name': employee_name,
                    'employee_id': employee_id,
                    'employee_info': employee_info,
                    'all_entries': []
                }
            
            # Add ALL entries (work, pause, everything)
            grouped_entries[group_key]['all_entries'].append(entry)
        
        # Sort groups by employee name
        sorted_groups = sorted(grouped_entries.values(), 
                             key=lambda x: x['employee_name'])
        
        # Process each group
        for group in sorted_groups:
            all_entries = group['all_entries']
            
            # Sort all entries chronologically by entry start time
            all_entries.sort(key=self._get_entry_sort_key)
            
            # Process pause redistribution
            processed_entries = self._redistribute_pause_time(all_entries)
            
            # Sort processed entries again to ensure chronological order after pause redistribution
            processed_entries.sort(key=self._get_entry_sort_key)
            
            # Write processed entries to Excel (without pause entries)
            daily_totals = {}
            total_worked_seconds = 0
            
            for entry in processed_entries:
                row_data = self._extract_entry_data(entry, group['employee_info'], check_types_map)
                
                # Write to Excel
                ws.cell(row=current_row, column=1, value=row_data['employee_name'])
                ws.cell(row=current_row, column=2, value=row_data['employee_id_type'])
                ws.cell(row=current_row, column=3, value=row_data['employee_nid'])
                ws.cell(row=current_row, column=4, value=row_data['entry_date'])
                ws.cell(row=current_row, column=5, value=row_data['activity_name'])
                ws.cell(row=current_row, column=6, value=row_data['group_name'])
                ws.cell(row=current_row, column=7, value=row_data['start_time'])
                ws.cell(row=current_row, column=8, value=row_data['end_time'])
                ws.cell(row=current_row, column=9, value=row_data['final_duration'])
                
                # Accumulate totals by activity type
                activity_name = row_data['activity_name']
                worked_seconds = row_data['worked_seconds']
                
                if activity_name not in daily_totals:
                    daily_totals[activity_name] = 0
                daily_totals[activity_name] += worked_seconds
                total_worked_seconds += worked_seconds
                
                current_row += 1
            
            # Add TOTAL row for this employee
            current_row = self._add_total_row(ws, group, daily_totals, total_worked_seconds, current_row)
            
            # Add blank row between different employees
            current_row += 1
        
        return current_row
    
    def _extract_entry_data(self, entry, employee_info, check_types_map):
        """Extract data from a work entry for Excel output"""
        # Employee name
        employee_name = f"{employee_info.get('firstName', '')} {employee_info.get('lastName', '')}".strip()
        if not employee_name:
            employee_name = "Empleado desconocido"
        
        # Employee identification
        employee_nid = employee_info.get('nid', 'No disponible')
        employee_id_type = employee_info.get('identityNumberType', 'DNI')
        
        # Get activity name from workCheckTypeId using check types mapping
        activity_name = "Actividad no especificada"
        work_check_type_id = entry.get('workCheckTypeId')
        if work_check_type_id and work_check_type_id in check_types_map:
            activity_name = check_types_map[work_check_type_id]
        elif entry.get('workEntryType'):
            activity_name = entry.get('workEntryType', 'Actividad no especificada')
        
        # Group name left empty as requested
        group_name = ""
        
        # Extract date from workEntryIn.date
        entry_date = "No disponible"
        if entry.get('workEntryIn') and entry['workEntryIn'].get('date'):
            try:
                entry_datetime = datetime.fromisoformat(
                    entry['workEntryIn']['date'].replace('Z', '+00:00'))
                entry_date = entry_datetime.strftime('%Y-%m-%d')
            except Exception as e:
                self.logger.error(f"Error parsing entry date: {e}")
                entry_date = "Error en fecha"
        
        # Extract times from workEntryIn and workEntryOut
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
        
        # Calculate duration
        worked_seconds = entry.get('workedSeconds', 0)
        final_duration = self._format_duration(timedelta(seconds=worked_seconds))
        
        return {
            'employee_name': employee_name,
            'employee_id_type': employee_id_type,
            'employee_nid': employee_nid,
            'entry_date': entry_date,
            'activity_name': activity_name,
            'group_name': group_name,
            'start_time': start_time,
            'end_time': end_time,
            'final_duration': final_duration,
            'worked_seconds': worked_seconds
        }
    
    def _add_total_row(self, ws, group, daily_totals, total_worked_seconds, current_row):
        """Add TOTAL row for employee"""
        employee_info = group['employee_info']
        employee_name = group['employee_name']
        employee_nid = employee_info.get('nid', 'No disponible')
        employee_id_type = employee_info.get('identityNumberType', 'DNI')
        entry_date = "TOTAL"  # Since we're not grouping by date anymore
        
        # Create summary of activity types
        activity_summary = []
        for activity_name, seconds in daily_totals.items():
            duration_str = self._format_duration(timedelta(seconds=seconds))
            activity_summary.append(f"{activity_name}: {duration_str}")
        
        # Join activity summary (limit to avoid Excel cell size issues)
        activity_summary_str = "; ".join(activity_summary[:5])  # Limit to 5 activities
        if len(daily_totals) > 5:
            activity_summary_str += f"; ... y {len(daily_totals) - 5} más"
        
        # Total duration
        total_duration = self._format_duration(timedelta(seconds=total_worked_seconds))
        
        # Apply bold formatting for TOTAL row
        total_font = Font(bold=True)
        total_fill = PatternFill(start_color="E6E6E6", end_color="E6E6E6", fill_type="solid")
        
        # Write TOTAL row
        ws.cell(row=current_row, column=1, value=employee_name).font = total_font
        ws.cell(row=current_row, column=2, value=employee_id_type).font = total_font
        ws.cell(row=current_row, column=3, value=employee_nid).font = total_font
        ws.cell(row=current_row, column=4, value=entry_date).font = total_font
        ws.cell(row=current_row, column=5, value="TOTAL").font = total_font
        ws.cell(row=current_row, column=6, value="").font = total_font
        ws.cell(row=current_row, column=7, value="").font = total_font
        ws.cell(row=current_row, column=8, value="").font = total_font
        ws.cell(row=current_row, column=9, value=total_duration).font = total_font
        
        # Apply background color to TOTAL row
        for col in range(1, 10):
            ws.cell(row=current_row, column=col).fill = total_fill
        
        return current_row + 1

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
    
    def get_data_metrics(self, from_date: str = None, to_date: str = None, 
                         employee_id: str = None, office_id: str = None, 
                         department_id: str = None) -> dict:
        """Get data collection metrics without generating full report"""
        try:
            # Get all work entries
            all_work_entries = self.api.get_all_time_tracking_data(
                employee_id=employee_id,
                from_date=from_date,
                to_date=to_date
            )
            
            # Get check types mapping
            check_types_response = self.api.get_check_types()
            check_types_map = {}
            if check_types_response and 'data' in check_types_response:
                for check_type in check_types_response['data']:
                    check_types_map[check_type['id']] = check_type['name']
            
            # Process first 10 entries for preview
            preview_entries = []
            for entry in all_work_entries[:10]:  # Only first 10 for preview
                employee_info = entry.get('employee', {})
                employee_name = f"{employee_info.get('firstName', '')} {employee_info.get('lastName', '')}".strip()
                
                if not employee_name:
                    employee_name = "Empleado desconocido"
                
                # Extract date
                entry_date = "No disponible"
                if entry.get('workEntryIn') and entry['workEntryIn'].get('date'):
                    try:
                        entry_datetime = datetime.fromisoformat(
                            entry['workEntryIn']['date'].replace('Z', '+00:00'))
                        entry_date = entry_datetime.strftime('%Y-%m-%d')
                    except Exception:
                        entry_date = "Error en fecha"
                
                row_data = self._extract_entry_data(entry, employee_info, entry_date, check_types_map)
                preview_entries.append(row_data)
            
            return {
                'total_entries': len(all_work_entries),
                'preview_entries': preview_entries,
                'success': True
            }
            
        except Exception as e:
            self.logger.error(f"Error getting data metrics: {str(e)}")
            return {
                'total_entries': 0,
                'preview_entries': [],
                'success': False,
                'error': str(e)
            }
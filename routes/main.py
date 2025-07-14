from flask import Blueprint, render_template, request, jsonify, send_file, flash, redirect, url_for
from datetime import datetime, timedelta
import io
import logging
from services.report_generator import ReportGenerator
from services.simple_report_generator import SimpleReportGenerator

main_bp = Blueprint('main', __name__)
logger = logging.getLogger(__name__)

@main_bp.route('/')
def index():
    """Main page with report generation form"""
    return render_template('index.html')

@main_bp.route('/test-connection')
def test_connection():
    """Test API connection"""
    try:
        report_generator = ReportGenerator()
        result = report_generator.test_connection()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error testing connection: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Connection test failed: {str(e)}"
        }), 500

@main_bp.route('/generate-report', methods=['POST'])
def generate_report():
    """Generate and download XLSX report"""
    try:
        # Get form data
        from_date = request.form.get('from_date')
        to_date = request.form.get('to_date')
        date_range = request.form.get('date_range', 'today')
        employee_id = request.form.get('employee_id')
        office_id = request.form.get('office_id')
        department_id = request.form.get('department_id')
        report_type = request.form.get('report_type', 'by_employee')
        
        # Validate dates
        if from_date:
            try:
                datetime.strptime(from_date, '%Y-%m-%d')
            except ValueError:
                flash('Fecha de inicio inválida', 'error')
                return redirect(url_for('main.index'))
                
        if to_date:
            try:
                datetime.strptime(to_date, '%Y-%m-%d')
            except ValueError:
                flash('Fecha de fin inválida', 'error')
                return redirect(url_for('main.index'))

        # Generate report with error handling - using simplified generator
        try:
            logger.info(f"Starting simplified report generation - Type: {report_type}, Employee: {employee_id}, Office: {office_id}, Department: {department_id}")
            simple_generator = SimpleReportGenerator()
            report_data = simple_generator.generate_simple_report(
                from_date=from_date,
                to_date=to_date,
                employee_id=employee_id,
                office_id=office_id,
                department_id=department_id,
                report_type=report_type
            )
            logger.info("Simplified report generation completed successfully")
        except Exception as report_error:
            logger.error(f"Error during simplified report generation: {str(report_error)}")
            flash(f'Error al generar el reporte: {str(report_error)}', 'error')
            return redirect(url_for('main.index'))
        
        if report_data:
            # Create filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"reporte_actividades_{timestamp}.xlsx"
            
            # Return file
            return send_file(
                io.BytesIO(report_data),
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=filename
            )
        else:
            flash('Error al generar el reporte. Verifique los datos y vuelva a intentar.', 'error')
            return redirect(url_for('main.index'))
            
    except Exception as e:
        logger.error(f"Error generating report: {str(e)}")
        flash(f'Error al generar el reporte: {str(e)}', 'error')
        return redirect(url_for('main.index'))

@main_bp.route('/preview-report', methods=['POST'])
def preview_report():
    """Preview report data in table format"""
    try:
        # Get form data
        data = request.get_json()
        from_date = data.get('from_date')
        to_date = data.get('to_date')
        employee_id = data.get('employee_id')
        office_id = data.get('office_id')
        department_id = data.get('department_id')
        report_type = data.get('report_type', 'by_employee')
        
        # Validate dates
        if from_date:
            try:
                datetime.strptime(from_date, '%Y-%m-%d')
            except ValueError:
                return jsonify({
                    "status": "error",
                    "message": "Fecha de inicio inválida"
                }), 400
                
        if to_date:
            try:
                datetime.strptime(to_date, '%Y-%m-%d')
            except ValueError:
                return jsonify({
                    "status": "error",
                    "message": "Fecha de fin inválida"
                }), 400

        # Get preview data using the API
        from services.sesame_api import SesameAPI
        api = SesameAPI()
        
        # Get employees data
        employees_data = api.get_all_employees_data()
        if not employees_data:
            return jsonify({
                "status": "error",
                "message": "No se pudo obtener la información de empleados"
            }), 400
            
        # Filter employees if needed
        if employee_id:
            employees_data = [emp for emp in employees_data if emp.get('id') == employee_id]
        if office_id:
            employees_data = [emp for emp in employees_data if emp.get('officeId') == office_id]
        if department_id:
            employees_data = [emp for emp in employees_data if emp.get('departmentId') == department_id]
            
        if not employees_data:
            return jsonify({
                "status": "success",
                "message": "No se encontraron empleados con los filtros aplicados",
                "data": [],
                "headers": []
            })
            
        # Get check types for activity name resolution
        check_types_data = api.get_all_check_types_data()
        check_types_map = {}
        if check_types_data:
            for check_type in check_types_data:
                check_types_map[check_type.get('id')] = check_type.get('name', 'Actividad no especificada')
        
        # Get complete time tracking data with pagination and break handling
        preview_data = []
        headers = ["Empleado", "Tipo ID", "Nº ID", "Fecha", "Actividad", "Grupo", "Entrada", "Salida", "Tiempo Original", "Tiempo Descanso", "Tiempo Final", "Procesado"]
        
        logger.info(f"Processing {len(employees_data)} employees for preview")
        logger.info(f"Loaded {len(check_types_map)} check types")
        
        # Process employees for preview with 10 record limit
        processed_count = 0
        record_count = 0
        for employee in employees_data:
            employee_name = f"{employee.get('firstName', '')} {employee.get('lastName', '')}".strip()
            logger.info(f"Processing employee: {employee_name} (ID: {employee.get('id')})")
            
            # Special check for the specific employee mentioned
            if "IGNACIO GARRIDO SALINAS" in employee_name.upper():
                logger.info(f"*** FOUND IGNACIO GARRIDO SALINAS - Processing data for this employee ***")
            
            # Get ALL time tracking data with complete pagination
            all_time_data = api.get_all_time_tracking_data(
                employee_id=employee['id'],
                from_date=from_date,
                to_date=to_date
            )
            
            # Get ALL break data with complete pagination
            all_break_data = api.get_all_breaks_data(
                employee_id=employee['id'],
                from_date=from_date,
                to_date=to_date
            )
            
            # Always log the count for each employee
            logger.info(f"Employee {employee_name}: {len(all_time_data)} time entries, {len(all_break_data)} break entries")
            
            if all_time_data:
                processed_count += 1
                logger.info(f"Found {len(all_time_data)} time entries and {len(all_break_data)} break entries")
                
                # Debug: log employee structure
                logger.debug(f"Employee structure: {employee}")
                
                # Debug: log first time entry structure
                if all_time_data:
                    logger.debug(f"First time entry structure: {all_time_data[0]}")
                
                # Process break time redistribution
                processed_entries = _process_break_redistribution(all_time_data, all_break_data)
                
                # Extract employee identification with better mapping
                identification_type = "No especificado"
                identification_number = "No especificado"
                
                # Try different possible field names for identification
                identification_number = (
                    employee.get('identificationNumber') or
                    employee.get('nid') or
                    employee.get('code') or
                    str(employee.get('pin')) if employee.get('pin') else None or
                    employee.get('id', 'No especificado')
                )
                
                identification_type = (
                    employee.get('identificationType') or
                    employee.get('identityNumberType') or
                    'DNI'
                )
                
                # Show processed entries (limit to 10 for preview)
                for entry in processed_entries[:10]:
                    # Debug: log entry structure
                    logger.debug(f"Processing entry: {entry}")
                    
                    # Extract employee name and identification from work-entries data
                    employee_name = "Nombre no disponible"
                    employee_nid = "No disponible"
                    employee_id_type = "DNI"
                    
                    if entry.get('employee'):
                        first_name = entry['employee'].get('firstName', '')
                        last_name = entry['employee'].get('lastName', '')
                        employee_name = f"{first_name} {last_name}".strip()
                        if not employee_name:
                            employee_name = "Nombre no disponible"
                        
                        # Extract nid and identification type from employee object
                        employee_nid = entry['employee'].get('nid', 'No disponible')
                        employee_id_type = entry['employee'].get('identityNumberType', 'DNI')
                    
                    # Extract date from workEntryIn.date
                    entry_date = "No disponible"
                    if entry.get('workEntryIn') and entry['workEntryIn'].get('date'):
                        try:
                            entry_datetime = datetime.fromisoformat(entry['workEntryIn']['date'].replace('Z', '+00:00'))
                            entry_date = entry_datetime.strftime('%Y-%m-%d')
                        except Exception as e:
                            logger.error(f"Error parsing entry date: {e}")
                            entry_date = "Error en fecha"
                    
                    # Get activity name from workCheckTypeId using check types mapping
                    activity_name = "Actividad no especificada"
                    work_check_type_id = entry.get('workCheckTypeId')
                    if work_check_type_id and work_check_type_id in check_types_map:
                        activity_name = check_types_map[work_check_type_id]
                    elif entry.get('workEntryType'):
                        activity_name = entry.get('workEntryType', 'Actividad no especificada')
                    
                    # Group name left empty as requested - no information available yet
                    group_name = ""
                    
                    # Extract times from workEntryIn and workEntryOut
                    start_time = "No disponible"
                    end_time = "No disponible"
                    
                    if entry.get('workEntryIn') and entry['workEntryIn'].get('date'):
                        try:
                            start_datetime = datetime.fromisoformat(entry['workEntryIn']['date'].replace('Z', '+00:00'))
                            start_time = start_datetime.strftime('%H:%M:%S')
                        except Exception as e:
                            logger.error(f"Error parsing start time: {e}")
                            start_time = "Error en hora"
                    
                    if entry.get('workEntryOut') and entry['workEntryOut'].get('date'):
                        try:
                            end_datetime = datetime.fromisoformat(entry['workEntryOut']['date'].replace('Z', '+00:00'))
                            end_time = end_datetime.strftime('%H:%M:%S')
                        except Exception as e:
                            logger.error(f"Error parsing end time: {e}")
                            end_time = "Error en hora"
                    
                    # Calculate durations
                    original_duration = "No disponible"
                    break_time = "00:00:00"
                    final_duration = "No disponible"
                    
                    if entry.get('workedSeconds') is not None:
                        try:
                            original_seconds = entry['workedSeconds']
                            original_duration = _format_duration(timedelta(seconds=original_seconds))
                            
                            # Break time added
                            break_seconds = entry.get('added_break_time', 0)
                            if break_seconds > 0:
                                break_time = _format_duration(timedelta(seconds=break_seconds))
                            
                            # Final duration
                            final_seconds = original_seconds + break_seconds
                            final_duration = _format_duration(timedelta(seconds=final_seconds))
                        except Exception as e:
                            logger.error(f"Error calculating duration: {e}")
                            final_duration = "Error en cálculo"
                    elif entry.get('workEntryIn') and entry.get('workEntryOut'):
                        try:
                            start_dt = datetime.fromisoformat(entry['workEntryIn']['date'].replace('Z', '+00:00'))
                            end_dt = datetime.fromisoformat(entry['workEntryOut']['date'].replace('Z', '+00:00'))
                            duration_td = end_dt - start_dt
                            original_duration = _format_duration(duration_td)
                            
                            # Add break time if any
                            added_break_time = entry.get('added_break_time', 0)
                            if added_break_time > 0:
                                break_time = _format_duration(timedelta(seconds=added_break_time))
                                final_duration = _format_duration(duration_td + timedelta(seconds=added_break_time))
                            else:
                                final_duration = original_duration
                        except Exception as e:
                            logger.error(f"Error calculating duration from dates: {e}")
                            original_duration = "Error en cálculo"
                            final_duration = "Error en cálculo"
                    
                    processing_status = "Procesado" if entry.get('processed', False) else "Original"
                    
                    preview_data.append([
                        employee_name,
                        employee_id_type,
                        employee_nid,
                        entry_date,
                        activity_name,
                        group_name,
                        start_time,
                        end_time,
                        original_duration,
                        break_time,
                        final_duration,
                        processing_status
                    ])
                    
                    record_count += 1
                    
                    # Limit preview to 10 records total
                    if record_count >= 10:
                        logger.info(f"Reached preview limit of 10 records. Stopping processing.")
                        break
            
            # Break if we've reached our record limit
            if record_count >= 10:
                break
        
        return jsonify({
            "status": "success",
            "message": f"Vista previa: {len(preview_data)} registros (limitada a 10 líneas) de {len(employees_data)} empleados totales",
            "data": preview_data,
            "headers": headers,
            "total_employees": len(employees_data),
            "processed_employees": processed_count,
            "preview_records": len(preview_data),
            "note": "Esta es una vista previa limitada. El informe completo tendrá todos los registros de todos los empleados."
        })
        
    except Exception as e:
        logger.error(f"Error generating preview: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Error al generar la vista previa: {str(e)}"
        }), 500

def _process_break_redistribution(time_entries, break_entries):
    """Process break time redistribution based on workEntryType"""
    logger.info(f"Processing break redistribution: {len(time_entries)} time entries, {len(break_entries)} break entries")
    
    # Separate work/remote entries from break/pause entries
    work_entries = []
    break_entries_to_redistribute = []
    
    for entry in time_entries:
        work_entry_type = entry.get('workEntryType', '').lower()
        
        # Keep only 'work' and 'remote' entries as final results
        if work_entry_type in ['work', 'remote']:
            work_entries.append({
                **entry,
                'added_break_time': 0,
                'processed': False
            })
        else:
            # Everything else (pause, break, etc.) gets redistributed
            break_entries_to_redistribute.append(entry)
            logger.info(f"Found break/pause entry to redistribute: {work_entry_type}")
    
    # Add explicit break entries from break endpoint
    for break_entry in break_entries:
        break_entries_to_redistribute.append(break_entry)
        logger.info(f"Found break entry from breaks endpoint")
    
    # Sort work entries by date and time for redistribution
    work_entries.sort(key=lambda x: x.get('workEntryIn', {}).get('date', ''))
    
    # Process each break entry for redistribution
    for break_entry in break_entries_to_redistribute:
        break_start_date = None
        break_end_date = None
        break_duration = 0
        
        # Try to get break timing from different possible structures
        if break_entry.get('workEntryIn') and break_entry.get('workEntryOut'):
            try:
                break_start_date = break_entry['workEntryIn']['date']
                break_end_date = break_entry['workEntryOut']['date']
                break_start = datetime.fromisoformat(break_start_date.replace('Z', '+00:00'))
                break_end = datetime.fromisoformat(break_end_date.replace('Z', '+00:00'))
                break_duration = (break_end - break_start).total_seconds()
            except Exception as e:
                logger.error(f"Error parsing break entry timing: {e}")
                continue
        elif break_entry.get('workedSeconds'):
            break_duration = break_entry['workedSeconds']
        else:
            logger.warning(f"Could not determine break duration for entry")
            continue
            
        if break_duration <= 0:
            continue
            
        break_type = break_entry.get('workEntryType', 'pause')
        logger.info(f"Processing break: {break_type}, duration: {break_duration:.0f}s")
        
        # Find adjacent work/remote activities
        previous_work_entry = None
        next_work_entry = None
        
        if break_start_date:
            break_start_dt = datetime.fromisoformat(break_start_date.replace('Z', '+00:00'))
            
            for i, work_entry in enumerate(work_entries):
                if not work_entry.get('workEntryOut'):
                    continue
                    
                try:
                    work_end_dt = datetime.fromisoformat(work_entry['workEntryOut']['date'].replace('Z', '+00:00'))
                    
                    # Check if this is the previous work activity (ends before break starts)
                    if work_end_dt <= break_start_dt:
                        previous_work_entry = work_entry
                    
                    # Check if this is the next work activity (starts after break ends)  
                    if work_entry.get('workEntryIn'):
                        work_start_dt = datetime.fromisoformat(work_entry['workEntryIn']['date'].replace('Z', '+00:00'))
                        if break_end_date:
                            break_end_dt = datetime.fromisoformat(break_end_date.replace('Z', '+00:00'))
                            if work_start_dt >= break_end_dt and next_work_entry is None:
                                next_work_entry = work_entry
                                break
                except Exception as e:
                    logger.error(f"Error comparing work entry timing: {e}")
                    continue
        
        # Redistribute break time (prefer previous, then next)
        if previous_work_entry:
            previous_work_entry['added_break_time'] += break_duration
            previous_work_entry['processed'] = True
            prev_type = previous_work_entry.get('workEntryType', 'work')
            logger.info(f"Added {break_duration:.0f}s break time ({break_type}) to previous {prev_type} entry")
        elif next_work_entry:
            next_work_entry['added_break_time'] += break_duration
            next_work_entry['processed'] = True
            next_type = next_work_entry.get('workEntryType', 'work')
            logger.info(f"Added {break_duration:.0f}s break time ({break_type}) to next {next_type} entry")
        else:
            logger.warning(f"Could not redistribute break time of {break_duration:.0f}s ({break_type}) - no adjacent work/remote activities found")
    
    logger.info(f"Final result: {len(work_entries)} work/remote entries (filtered from {len(time_entries)} total entries)")
    return work_entries

def _format_duration(duration):
    """Format duration as HH:MM:SS"""
    if isinstance(duration, timedelta):
        total_seconds = int(duration.total_seconds())
    else:
        total_seconds = int(duration)
    
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

@main_bp.route('/apply-token', methods=['POST'])
def apply_token():
    """Apply new API token"""
    try:
        data = request.get_json()
        new_token = data.get('token')
        region = data.get('region', 'eu1')
        description = data.get('description', f'Token aplicado desde interfaz web - Región: {region}')
        
        if not new_token:
            return jsonify({
                "status": "error",
                "message": "Token is required"
            }), 400
        
        # Test the token first by creating a temporary API instance
        from services.sesame_api import SesameAPI
        
        # Create a temporary API instance for testing
        test_api = SesameAPI()
        test_api.token = new_token
        test_api.region = region
        test_api.base_url = f"https://api-{region}.sesametime.com"
        test_api.headers["Authorization"] = f"Bearer {new_token}"
        
        # Test the token
        result = test_api.get_token_info()
        
        if result:
            # Save the token to database
            from models import SesameToken
            SesameToken.set_active_token(new_token, description, region)
            
            return jsonify({
                "status": "success",
                "message": "Token aplicado correctamente y guardado en base de datos",
                "company": result.get('company', 'Unknown'),
                "region": region
            })
        else:
            return jsonify({
                "status": "error",
                "message": "Token inválido o región incorrecta"
            }), 400
            
    except Exception as e:
        logger.error(f"Error applying token: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Error al aplicar el token: {str(e)}"
        }), 500

@main_bp.route('/get-current-token')
def get_current_token():
    """Get information about current token (masked for security)"""
    try:
        from models import SesameToken
        
        # Get active token from database
        active_token = SesameToken.get_active_token()
        
        if not active_token:
            return jsonify({
                "status": "error",
                "message": "No token configured",
                "token_preview": "No token"
            })
        
        # Show only first 8 and last 4 characters for security
        token_value = active_token.token
        if len(token_value) > 12:
            token_preview = token_value[:8] + "..." + token_value[-4:]
        else:
            token_preview = token_value[:4] + "..." + token_value[-2:]
        
        return jsonify({
            "status": "success",
            "token_preview": token_preview,
            "token_length": len(token_value),
            "description": active_token.description,
            "region": active_token.region,
            "created_at": active_token.created_at.isoformat() if active_token.created_at else None
        })
    except Exception as e:
        logger.error(f"Error getting current token: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Error getting current token: {str(e)}"
        }), 500

@main_bp.route('/get-employees')
def get_employees():
    """Get list of employees for dropdown"""
    try:
        report_generator = ReportGenerator()
        employees = report_generator.sesame_api.get_all_employees_data()
        
        employee_list = []
        for employee in employees:
            employee_list.append({
                'id': employee.get('id'),
                'name': f"{employee.get('firstName', '')} {employee.get('lastName', '')}".strip()
            })
        
        return jsonify({
            "status": "success",
            "employees": employee_list
        })
    except Exception as e:
        logger.error(f"Error getting employees: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Error getting employees: {str(e)}"
        }), 500

@main_bp.route('/get-offices')
def get_offices():
    """Get list of offices/centers for dropdown"""
    try:
        report_generator = ReportGenerator()
        offices = report_generator.sesame_api.get_all_offices_data()
        
        office_list = []
        for office in offices:
            office_list.append({
                'id': office.get('id'),
                'name': office.get('name', 'Centro sin nombre')
            })
        
        return jsonify({
            "status": "success",
            "offices": office_list
        })
    except Exception as e:
        logger.error(f"Error getting offices: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Error getting offices: {str(e)}"
        }), 500

@main_bp.route('/get-departments')
def get_departments():
    """Get list of departments for dropdown"""
    try:
        report_generator = ReportGenerator()
        departments = report_generator.sesame_api.get_all_departments_data()
        
        department_list = []
        for department in departments:
            department_list.append({
                'id': department.get('id'),
                'name': department.get('name', 'Departamento sin nombre')
            })
        
        return jsonify({
            "status": "success",
            "departments": department_list
        })
    except Exception as e:
        logger.error(f"Error getting departments: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Error getting departments: {str(e)}"
        }), 500

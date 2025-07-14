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
            
        # Get complete time tracking data with pagination and break handling
        preview_data = []
        headers = ["Empleado", "Tipo ID", "Nº ID", "Fecha", "Actividad", "Grupo", "Entrada", "Salida", "Tiempo Original", "Tiempo Descanso", "Tiempo Final", "Procesado"]
        
        logger.info(f"Processing {len(employees_data)} employees for preview")
        
        for employee in employees_data[:5]:  # Limit to first 5 employees for preview
            logger.info(f"Processing employee: {employee.get('name', 'Unknown')}")
            
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
            
            if all_time_data:
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
                    
                    # Format entry data with multiple possible field names
                    entry_date = (
                        entry.get('date') or
                        entry.get('entryDate') or
                        entry.get('workDate') or
                        entry.get('created_at', 'No especificado')
                    )
                    if entry_date and 'T' in entry_date:
                        entry_date = entry_date.split('T')[0]
                    
                    # Try different possible structures for activity info
                    activity_name = (
                        entry.get('activity', {}).get('name') or
                        entry.get('activityName') or
                        entry.get('type') or
                        entry.get('description') or
                        'Actividad no especificada'
                    )
                    
                    group_name = (
                        entry.get('activity', {}).get('group', {}).get('name') or
                        entry.get('groupName') or
                        entry.get('group') or
                        'Sin grupo'
                    )
                    
                    # Format times with multiple possible field names
                    start_time = (
                        entry.get('timeIn') or
                        entry.get('startTime') or
                        entry.get('clockIn') or
                        entry.get('entrada') or
                        'No especificado'
                    )
                    
                    end_time = (
                        entry.get('timeOut') or
                        entry.get('endTime') or
                        entry.get('clockOut') or
                        entry.get('salida') or
                        'No especificado'
                    )
                    
                    if start_time and 'T' in start_time:
                        start_time = start_time.split('T')[1][:8]
                    if end_time and 'T' in end_time:
                        end_time = end_time.split('T')[1][:8]
                    
                    # Calculate durations
                    original_duration = "No calculado"
                    break_time = "0:00:00"
                    final_duration = "No calculado"
                    
                    if entry.get('timeIn') and entry.get('timeOut'):
                        try:
                            start_dt = datetime.fromisoformat(entry['timeIn'].replace('Z', '+00:00'))
                            end_dt = datetime.fromisoformat(entry['timeOut'].replace('Z', '+00:00'))
                            duration_td = end_dt - start_dt
                            original_duration = _format_duration(duration_td)
                            
                            # Add break time if any
                            added_break_time = entry.get('added_break_time', 0)
                            if added_break_time > 0:
                                break_time = _format_duration(timedelta(seconds=added_break_time))
                                final_duration = _format_duration(duration_td + timedelta(seconds=added_break_time))
                            else:
                                final_duration = original_duration
                        except:
                            original_duration = "Error en cálculo"
                            final_duration = "Error en cálculo"
                    
                    processing_status = "Procesado" if entry.get('processed', False) else "Original"
                    
                    preview_data.append([
                        employee.get('name', 'Nombre no disponible'),
                        identification_type,
                        identification_number,
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
        
        return jsonify({
            "status": "success",
            "message": f"Vista previa mostrando {len(preview_data)} registros",
            "data": preview_data,
            "headers": headers,
            "total_employees": len(employees_data),
            "note": "Esta es una vista previa limitada. El informe completo tendrá todos los registros."
        })
        
    except Exception as e:
        logger.error(f"Error generating preview: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Error al generar la vista previa: {str(e)}"
        }), 500

def _process_break_redistribution(time_entries, break_entries):
    """Process break time redistribution to adjacent activities"""
    logger.info(f"Processing break redistribution: {len(time_entries)} time entries, {len(break_entries)} break entries")
    
    # Create a copy of time entries to modify
    processed_entries = []
    break_entries_to_process = []
    
    # Separate break activities from regular activities
    for entry in time_entries:
        activity_name = entry.get('activity', {}).get('name', '').lower()
        group_name = entry.get('activity', {}).get('group', {}).get('name', '').lower()
        
        # Check if this is a break activity (contains words like "descanso", "break", "pausa")
        is_break = any(keyword in activity_name or keyword in group_name for keyword in 
                      ['descanso', 'break', 'pausa', 'breakfast', 'lunch', 'almuerzo', 'comida'])
        
        if is_break:
            break_entries_to_process.append(entry)
            logger.info(f"Found break activity in time entries: {activity_name}")
        else:
            processed_entries.append({
                **entry,
                'added_break_time': 0,
                'processed': False
            })
    
    # Add explicit break entries from break endpoint
    for break_entry in break_entries:
        break_entries_to_process.append(break_entry)
        # Try different possible structures for activity name
        break_activity_name = (
            break_entry.get('activity', {}).get('name') or
            break_entry.get('activityName') or
            break_entry.get('type') or
            break_entry.get('description') or
            'Descanso'
        )
        logger.info(f"Found break entry from breaks endpoint: {break_activity_name}")
        logger.debug(f"Break entry structure: {break_entry}")
    
    # Sort entries by date and time
    processed_entries.sort(key=lambda x: x.get('timeIn', ''))
    
    # Process each break entry
    for break_entry in break_entries_to_process:
        if not break_entry.get('timeIn') or not break_entry.get('timeOut'):
            continue
            
        try:
            break_start = datetime.fromisoformat(break_entry['timeIn'].replace('Z', '+00:00'))
            break_end = datetime.fromisoformat(break_entry['timeOut'].replace('Z', '+00:00'))
            break_duration = (break_end - break_start).total_seconds()
            
            break_activity_name = break_entry.get('activity', {}).get('name', 'Unknown Break')
            logger.info(f"Processing break: {break_activity_name}, duration: {break_duration:.0f}s")
            
            # Find adjacent activities
            previous_entry = None
            next_entry = None
            
            for i, entry in enumerate(processed_entries):
                if not entry.get('timeOut'):
                    continue
                    
                entry_end = datetime.fromisoformat(entry['timeOut'].replace('Z', '+00:00'))
                
                # Check if this is the previous activity (ends before break starts)
                if entry_end <= break_start:
                    previous_entry = entry
                
                # Check if this is the next activity (starts after break ends)  
                if entry.get('timeIn'):
                    entry_start = datetime.fromisoformat(entry['timeIn'].replace('Z', '+00:00'))
                    if entry_start >= break_end and next_entry is None:
                        next_entry = entry
                        break
            
            # Redistribute break time (prefer previous, then next)
            if previous_entry:
                previous_entry['added_break_time'] += break_duration
                previous_entry['processed'] = True
                prev_activity = previous_entry.get('activity', {}).get('name', 'Unknown')
                logger.info(f"Added {break_duration:.0f}s break time ({break_activity_name}) to previous activity: {prev_activity}")
            elif next_entry:
                next_entry['added_break_time'] += break_duration
                next_entry['processed'] = True
                next_activity = next_entry.get('activity', {}).get('name', 'Unknown')
                logger.info(f"Added {break_duration:.0f}s break time ({break_activity_name}) to next activity: {next_activity}")
            else:
                logger.warning(f"Could not redistribute break time of {break_duration:.0f}s ({break_activity_name}) - no adjacent activities found")
                
        except Exception as e:
            logger.error(f"Error processing break entry: {str(e)}")
            continue
    
    return processed_entries

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

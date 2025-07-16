from flask import Blueprint, render_template, request, jsonify, send_file, flash, redirect, url_for, session
from datetime import datetime, timedelta
import io
import logging
import threading
import uuid
import os
from services.report_generator import ReportGenerator
from services.no_breaks_report_generator import NoBreaksReportGenerator

main_bp = Blueprint('main', __name__)
logger = logging.getLogger(__name__)

# Store for background reports
background_reports = {}

def generate_report_background(report_id, form_data):
    """Generate report in background thread"""
    try:
        logger.info(f"Starting background report generation - ID: {report_id}")
        background_reports[report_id]['status'] = 'processing'
        
        # Generate report
        report_data = None
        
        try:
            logger.info(f"Starting NO-BREAKS report generation - Type: {form_data['report_type']}")
            no_breaks_generator = NoBreaksReportGenerator()
            report_data = no_breaks_generator.generate_report(
                from_date=form_data['from_date'],
                to_date=form_data['to_date'],
                employee_id=form_data['employee_id'],
                office_id=form_data['office_id'],
                department_id=form_data['department_id'],
                report_type=form_data['report_type'])
            logger.info("NO-BREAKS report generation completed successfully")
        except Exception as no_breaks_error:
            logger.error(f"NO-BREAKS report generator failed: {str(no_breaks_error)}")
            
            # Try ultra-basic fallback for SSL issues
            try:
                logger.info("Trying ULTRA-BASIC fallback for SSL issues...")
                from services.ultra_basic_report_generator import UltraBasicReportGenerator
                ultra_basic_generator = UltraBasicReportGenerator()
                report_data = ultra_basic_generator.generate_ultra_basic_report(
                    from_date=form_data['from_date'],
                    to_date=form_data['to_date'],
                    employee_id=form_data['employee_id'],
                    office_id=form_data['office_id'],
                    department_id=form_data['department_id'],
                    report_type=form_data['report_type'])
                logger.info("ULTRA-BASIC fallback completed successfully")
            except Exception as fallback_error:
                logger.error(f"ULTRA-BASIC fallback also failed: {str(fallback_error)}")
                background_reports[report_id]['status'] = 'error'
                background_reports[report_id]['error'] = f'Error SSL persistente: {str(fallback_error)}'
                return

        if report_data:
            # Save report to temporary file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"reporte_actividades_{timestamp}.xlsx"
            
            # Create temp directory if it doesn't exist
            temp_dir = 'temp_reports'
            os.makedirs(temp_dir, exist_ok=True)
            
            # Save file
            file_path = os.path.join(temp_dir, f"{report_id}_{filename}")
            with open(file_path, 'wb') as f:
                f.write(report_data)
            
            background_reports[report_id]['status'] = 'completed'
            background_reports[report_id]['filename'] = filename
            background_reports[report_id]['file_path'] = file_path
            logger.info(f"Background report completed - ID: {report_id}, File: {filename}")
        else:
            background_reports[report_id]['status'] = 'error'
            background_reports[report_id]['error'] = 'Error al generar el reporte'
            
    except Exception as e:
        logger.error(f"Background report generation failed - ID: {report_id}, Error: {str(e)}")
        background_reports[report_id]['status'] = 'error'
        background_reports[report_id]['error'] = str(e)


@main_bp.route('/', methods=['GET', 'POST'])
def index():
    """Main page with report generation form and background report generation"""
    if request.method == 'GET':
        return render_template('index.html')
    
    # Handle POST request for background report generation
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
                return render_template('index.html')

        if to_date:
            try:
                datetime.strptime(to_date, '%Y-%m-%d')
            except ValueError:
                flash('Fecha de fin inválida', 'error')
                return render_template('index.html')

        # Generate unique report ID
        report_id = str(uuid.uuid4())
        
        # Store form data and initial status
        form_data = {
            'from_date': from_date,
            'to_date': to_date,
            'employee_id': employee_id,
            'office_id': office_id,
            'department_id': department_id,
            'report_type': report_type
        }
        
        background_reports[report_id] = {
            'status': 'starting',
            'created_at': datetime.now(),
            'form_data': form_data
        }
        
        # Start background thread
        thread = threading.Thread(target=generate_report_background, args=(report_id, form_data))
        thread.daemon = True
        thread.start()
        
        flash('Reporte iniciado en segundo plano. Se mostrará el enlace de descarga cuando esté listo.', 'info')
        return render_template('index.html', report_id=report_id)

    except Exception as e:
        logger.error(f"Error starting background report: {str(e)}")
        flash(f'Error al iniciar el reporte: {str(e)}', 'error')
        return render_template('index.html')


@main_bp.route('/report-status/<report_id>')
def report_status(report_id):
    """Check the status of a background report"""
    if report_id not in background_reports:
        return jsonify({'status': 'not_found'}), 404
    
    report = background_reports[report_id]
    return jsonify({
        'status': report['status'],
        'created_at': report['created_at'].isoformat(),
        'filename': report.get('filename', ''),
        'error': report.get('error', '')
    })


@main_bp.route('/download-report/<report_id>')
def download_report(report_id):
    """Download a completed background report"""
    if report_id not in background_reports:
        flash('Reporte no encontrado', 'error')
        return redirect(url_for('main.index'))
    
    report = background_reports[report_id]
    
    if report['status'] != 'completed':
        flash('Reporte no está listo para descarga', 'error')
        return redirect(url_for('main.index'))
    
    if not os.path.exists(report['file_path']):
        flash('Archivo de reporte no encontrado', 'error')
        return redirect(url_for('main.index'))
    
    try:
        return send_file(
            report['file_path'],
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=report['filename']
        )
    except Exception as e:
        logger.error(f"Error downloading report {report_id}: {str(e)}")
        flash(f'Error al descargar el reporte: {str(e)}', 'error')
        return redirect(url_for('main.index'))


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

        # Use NO-BREAKS report generator with SSL error handling
        report_data = None
        
        try:
            logger.info(f"Starting NO-BREAKS report generation - Type: {report_type}")
            no_breaks_generator = NoBreaksReportGenerator()
            report_data = no_breaks_generator.generate_report(
                from_date=from_date,
                to_date=to_date,
                employee_id=employee_id,
                office_id=office_id,
                department_id=department_id,
                report_type=report_type)
            logger.info("NO-BREAKS report generation completed successfully")
        except Exception as no_breaks_error:
            logger.error(f"NO-BREAKS report generator failed: {str(no_breaks_error)}")
            
            # Try ultra-basic fallback for SSL issues
            try:
                logger.info("Trying ULTRA-BASIC fallback for SSL issues...")
                from services.ultra_basic_report_generator import UltraBasicReportGenerator
                ultra_basic_generator = UltraBasicReportGenerator()
                report_data = ultra_basic_generator.generate_ultra_basic_report(
                    from_date=from_date,
                    to_date=to_date,
                    employee_id=employee_id,
                    office_id=office_id,
                    department_id=department_id,
                    report_type=report_type)
                logger.info("ULTRA-BASIC fallback completed successfully")
            except Exception as fallback_error:
                logger.error(f"ULTRA-BASIC fallback also failed: {str(fallback_error)}")
                flash(f'Error SSL persistente. Intente con un rango de fechas más corto: {str(fallback_error)}', 'error')
                return redirect(url_for('main.index'))

        if report_data:
            # Create filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"reporte_actividades_{timestamp}.xlsx"

            # Return file
            return send_file(
                io.BytesIO(report_data),
                mimetype=
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=filename)
        else:
            flash(
                'Error al generar el reporte. Verifique los datos y vuelva a intentar.',
                'error')
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

        # Get work entries data directly - this is the ONLY data source
        logger.info("Fetching work entries data directly - NO employee processing")
        all_work_entries = api.get_all_time_tracking_data(
            employee_id=employee_id,
            from_date=from_date,
            to_date=to_date
        )

        if not all_work_entries:
            return jsonify({
                "status": "success",
                "message": "No se encontraron fichajes para el rango de fechas especificado",
                "data": [],
                "headers": []
            })

        # Get check types for activity name resolution
        check_types_data = api.get_all_check_types_data()
        check_types_map = {}
        if check_types_data:
            for check_type in check_types_data:
                check_types_map[check_type.get('id')] = check_type.get(
                    'name', 'Actividad no especificada')

        # No longer fetching break data as requested

        # Set up response structure
        preview_data = []
        headers = [
            "Empleado", "Tipo ID", "Nº ID", "Fecha", "Actividad", "Grupo",
            "Entrada", "Salida", "Tiempo Registrado"
        ]

        logger.info(f"Processing {len(all_work_entries)} fichajes for preview")
        logger.info(f"Loaded {len(check_types_map)} check types")

        # Process work entries directly - limited to 10 records for fast loading
        record_count = 0
        for entry in all_work_entries:
            if record_count >= 10:  # Limit preview to 10 records
                break
                
            # Get employee info from the work entry
            employee_info = entry.get('employee', {})
            employee_name = f"{employee_info.get('firstName', '')} {employee_info.get('lastName', '')}".strip()
            
            if not employee_name:
                employee_name = "Empleado desconocido"

            # Extract employee identification
            employee_nid = employee_info.get('nid', 'No disponible')
            employee_id_type = employee_info.get('identityNumberType', 'DNI')

            # Extract date from workEntryIn.date
            entry_date = "No disponible"
            if entry.get('workEntryIn') and entry['workEntryIn'].get('date'):
                try:
                    entry_datetime = datetime.fromisoformat(
                        entry['workEntryIn']['date'].replace('Z', '+00:00'))
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
                    start_datetime = datetime.fromisoformat(
                        entry['workEntryIn']['date'].replace('Z', '+00:00'))
                    start_time = start_datetime.strftime('%H:%M:%S')
                except Exception as e:
                    logger.error(f"Error parsing start time: {e}")
                    start_time = "Error en hora"

            if entry.get('workEntryOut') and entry['workEntryOut'].get('date'):
                try:
                    end_datetime = datetime.fromisoformat(
                        entry['workEntryOut']['date'].replace('Z', '+00:00'))
                    end_time = end_datetime.strftime('%H:%M:%S')
                except Exception as e:
                    logger.error(f"Error parsing end time: {e}")
                    end_time = "Error en hora"

            # Calculate duration
            final_duration = "No disponible"
            if entry.get('workedSeconds') is not None:
                try:
                    worked_seconds = entry['workedSeconds']
                    final_duration = _format_duration(timedelta(seconds=worked_seconds))
                except Exception as e:
                    logger.error(f"Error calculating duration: {e}")
                    final_duration = "Error en duración"

            # Add data to preview
            preview_data.append([
                employee_name, employee_id_type, employee_nid,
                entry_date, activity_name, group_name, start_time,
                end_time, final_duration
            ])

            record_count += 1

        return jsonify({
            "status": "success",
            "message": f"Vista previa: {len(preview_data)} registros (limitada a 10 líneas) de {len(all_work_entries)} fichajes totales",
            "data": preview_data,
            "headers": headers,
            "total_entries": len(all_work_entries),
            "preview_records": len(preview_data),
            "note": "Esta es una vista previa limitada. El informe completo tendrá todos los registros de fichajes."
        })

    except Exception as e:
        logger.error(f"Error generating preview: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Error al generar la vista previa: {str(e)}"
        }), 500


def _process_break_redistribution(time_entries, break_entries):
    """Process break time redistribution based on workEntryType"""
    logger.info(
        f"Processing break redistribution: {len(time_entries)} time entries, {len(break_entries)} break entries"
    )

    # Separate work/remote entries from break/pause entries
    work_entries = []
    break_entries_to_redistribute = []

    for entry in time_entries:
        work_entry_type = entry.get('workEntryType', '').lower()

        # Keep only 'work' and 'remote' entries as final results
        if work_entry_type in ['work', 'remote']:
            work_entries.append({
                **entry, 'added_break_time': 0,
                'processed': False
            })
        else:
            # Everything else (pause, break, etc.) gets redistributed
            break_entries_to_redistribute.append(entry)
            logger.info(
                f"Found break/pause entry to redistribute: {work_entry_type}")

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
                break_start = datetime.fromisoformat(
                    break_start_date.replace('Z', '+00:00'))
                break_end = datetime.fromisoformat(
                    break_end_date.replace('Z', '+00:00'))
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
        logger.info(
            f"Processing break: {break_type}, duration: {break_duration:.0f}s")

        # Find adjacent work/remote activities
        previous_work_entry = None
        next_work_entry = None

        if break_start_date:
            break_start_dt = datetime.fromisoformat(
                break_start_date.replace('Z', '+00:00'))

            for i, work_entry in enumerate(work_entries):
                if not work_entry.get('workEntryOut'):
                    continue

                try:
                    work_end_dt = datetime.fromisoformat(
                        work_entry['workEntryOut']['date'].replace(
                            'Z', '+00:00'))

                    # Check if this is the previous work activity (ends before break starts)
                    if work_end_dt <= break_start_dt:
                        previous_work_entry = work_entry

                    # Check if this is the next work activity (starts after break ends)
                    if work_entry.get('workEntryIn'):
                        work_start_dt = datetime.fromisoformat(
                            work_entry['workEntryIn']['date'].replace(
                                'Z', '+00:00'))
                        if break_end_date:
                            break_end_dt = datetime.fromisoformat(
                                break_end_date.replace('Z', '+00:00'))
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
            logger.info(
                f"Added {break_duration:.0f}s break time ({break_type}) to previous {prev_type} entry"
            )
        elif next_work_entry:
            next_work_entry['added_break_time'] += break_duration
            next_work_entry['processed'] = True
            next_type = next_work_entry.get('workEntryType', 'work')
            logger.info(
                f"Added {break_duration:.0f}s break time ({break_type}) to next {next_type} entry"
            )
        else:
            logger.warning(
                f"Could not redistribute break time of {break_duration:.0f}s ({break_type}) - no adjacent work/remote activities found"
            )

    logger.info(
        f"Final result: {len(work_entries)} work/remote entries (filtered from {len(time_entries)} total entries)"
    )
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
        description = data.get(
            'description',
            f'Token aplicado desde interfaz web - Región: {region}')

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
                "message":
                "Token aplicado correctamente y guardado en base de datos",
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
            "status":
            "success",
            "token_preview":
            token_preview,
            "token_length":
            len(token_value),
            "description":
            active_token.description,
            "region":
            active_token.region,
            "created_at":
            active_token.created_at.isoformat()
            if active_token.created_at else None
        })
    except Exception as e:
        logger.error(f"Error getting current token: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Error getting current token: {str(e)}"
        }), 500



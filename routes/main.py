from flask import Blueprint, render_template, request, jsonify, send_file, flash, redirect, url_for, session
from datetime import datetime, timedelta
import io
import logging
import threading
import uuid
import os
import glob
from services.no_breaks_report_generator import NoBreaksReportGenerator
from services.sesame_api import SesameAPI
from auth import requires_auth, check_auth, login_user, logout_user, authenticate

main_bp = Blueprint('main', __name__)
logger = logging.getLogger(__name__)

# Configuration
MAX_REPORTS = 10

# Store for background reports
background_reports = {}

def _enforce_report_limit(temp_dir, max_reports=MAX_REPORTS):
    """Enforce maximum number of reports, delete oldest if exceeded"""
    deleted_files = []
    try:
        # Get all xlsx files in temp directory
        report_files = glob.glob(os.path.join(temp_dir, '*.xlsx'))
        
        if len(report_files) <= max_reports:
            return deleted_files
        
        # Sort files by modification time (oldest first)
        report_files.sort(key=lambda x: os.path.getmtime(x))
        
        # Calculate how many files to delete
        files_to_delete = len(report_files) - max_reports
        
        for i in range(files_to_delete):
            file_to_delete = report_files[i]
            try:
                # Extract report_id from filename for cleanup
                filename = os.path.basename(file_to_delete)
                if '_' in filename:
                    report_id = filename.split('_')[0]
                    # Remove from background_reports if it exists
                    if report_id in background_reports:
                        del background_reports[report_id]
                
                # Delete the file
                os.remove(file_to_delete)
                deleted_files.append(filename)
                logger.info(f"Deleted old report file: {filename} (enforcing {max_reports} report limit)")
                
            except Exception as e:
                logger.warning(f"Failed to delete old report file {file_to_delete}: {str(e)}")
                
    except Exception as e:
        logger.error(f"Error enforcing report limit: {str(e)}")
    
    return deleted_files


def generate_report_background(report_id, form_data, app_context):
    """Generate report in background thread"""
    try:
        with app_context:
            logger.info(f"Starting background report generation - ID: {report_id}")
            background_reports[report_id]['status'] = 'processing'
            
            # Generate report
            report_data = None
            
            logger.info(f"Starting NO-BREAKS report generation - Type: {form_data['report_type']}")
            no_breaks_generator = NoBreaksReportGenerator()
            report_data = no_breaks_generator.generate_report(
                from_date=form_data['from_date'],
                to_date=form_data['to_date'],
                employee_id=form_data['employee_id'],
                office_id=form_data['office_id'],
                department_id=form_data['department_id'],
                report_type=form_data['report_type'],
                format=form_data.get('format', 'xlsx'))
            logger.info("NO-BREAKS report generation completed successfully")

            if report_data:
                # Save report to temporary file
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                format_type = form_data.get('format', 'xlsx')
                file_extension = 'csv' if format_type == 'csv' else 'xlsx'
                filename = f"reporte_actividades_{timestamp}.{file_extension}"
                
                # Create temp directory if it doesn't exist
                temp_dir = 'temp_reports'
                os.makedirs(temp_dir, exist_ok=True)
                
                # Save file
                file_path = os.path.join(temp_dir, f"{report_id}_{filename}")
                with open(file_path, 'wb') as f:
                    f.write(report_data)
                
                # Check and enforce 10 report limit
                deleted_files = _enforce_report_limit(temp_dir)
                if deleted_files:
                    logger.info(f"Deleted {len(deleted_files)} old report(s) to enforce 10 report limit: {', '.join(deleted_files)}")
                
                # Update status outside app context to avoid DB connection issues
                logger.info(f"Background report completed - ID: {report_id}, File: {filename}")
            else:
                logger.error("No report data generated")
                
    except Exception as e:
        logger.error(f"Background report generation failed - ID: {report_id}, Error: {str(e)}")
        
    # Update status outside app context to avoid DB SSL issues
    try:
        # Initialize variables
        filename = None
        file_path = None
        report_data = None
        
        if report_data:
            background_reports[report_id]['status'] = 'completed'
            background_reports[report_id]['filename'] = filename or f"{report_id}_reporte.xlsx"
            background_reports[report_id]['file_path'] = file_path or f"temp_reports/{report_id}_reporte.xlsx"
        else:
            background_reports[report_id]['status'] = 'error'
            background_reports[report_id]['error'] = 'Error al generar el reporte'
    except Exception as e:
        logger.error(f"Error updating report status - ID: {report_id}, Error: {str(e)}")
        background_reports[report_id]['status'] = 'error'
        background_reports[report_id]['error'] = 'Error en el proceso final'


@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if check_auth(username, password):
            login_user()
            return redirect(url_for('main.index'))
        else:
            flash('Usuario o contraseña incorrectos', 'error')
    
    return render_template('login.html')

@main_bp.route('/logout')
def logout():
    """Logout"""
    logout_user()
    flash('Sesión cerrada exitosamente', 'success')
    return redirect(url_for('main.login'))

@main_bp.route('/', methods=['GET', 'POST'])
@requires_auth
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
            'report_type': report_type,
            'format': request.form.get('format', 'xlsx')
        }
        
        background_reports[report_id] = {
            'status': 'starting',
            'created_at': datetime.now(),
            'form_data': form_data
        }
        
        # Start background thread with app context
        from flask import current_app
        thread = threading.Thread(target=generate_report_background, args=(report_id, form_data, current_app.app_context()))
        thread.daemon = True
        thread.start()
        

        return render_template('index.html', report_id=report_id)

    except Exception as e:
        logger.error(f"Error starting background report: {str(e)}")
        flash(f'Error al iniciar el reporte: {str(e)}', 'error')
        return render_template('index.html')


@main_bp.route('/report-status/<report_id>')
@requires_auth
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
@requires_auth
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
        # Determine mimetype based on file extension
        if report['filename'].endswith('.csv'):
            mimetype = 'text/csv'
        else:
            mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        
        return send_file(
            report['file_path'],
            mimetype=mimetype,
            as_attachment=True,
            download_name=report['filename']
        )
    except Exception as e:
        logger.error(f"Error downloading report {report_id}: {str(e)}")
        flash(f'Error al descargar el reporte: {str(e)}', 'error')
        return redirect(url_for('main.index'))


@main_bp.route('/test-connection')
@requires_auth
def test_connection():
    """Test API connection"""
    try:
        from services.sesame_api import SesameAPI
        api = SesameAPI()
        result = api.get_token_info()
        
        if result:
            # Extract company name from the API response
            company_name = "Empresa no identificada"
            if 'data' in result and 'company' in result['data']:
                company_name = result['data']['company'].get('name', 'Empresa no identificada')
            elif 'company' in result:
                company_name = result['company'].get('name', 'Empresa no identificada')
            
            # Sync check types when connection is tested successfully
            try:
                from services.check_types_service import CheckTypesService
                check_types_service = CheckTypesService()
                check_types_service.ensure_check_types_cached()
            except Exception as e:
                logger.warning(f"Failed to verify check types cache after connection test: {str(e)}")
                # Don't fail the connection test if check types sync fails
            
            return jsonify({
                "status": "success",
                "message": "Conexión exitosa",
                "company": company_name,
                "data": result
            })
        else:
            return jsonify({
                "status": "error",
                "message": "No se pudo conectar a la API"
            }), 500
    except Exception as e:
        logger.error(f"Error testing connection: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Error de conexión: {str(e)}"
        }), 500


@main_bp.route('/refresh-check-types', methods=['POST'])
@requires_auth
def refresh_check_types():
    """Refresh check types from API"""
    try:
        from services.check_types_service import CheckTypesService
        check_types_service = CheckTypesService()
        result = check_types_service.refresh_check_types()
        
        if result:
            return jsonify({
                "status": "success",
                "message": "Tipos de fichajes actualizados correctamente"
            })
        else:
            return jsonify({
                "status": "error",
                "message": "Error al actualizar tipos de fichajes"
            }), 500
    except Exception as e:
        logger.error(f"Error refreshing check types: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Error al actualizar tipos de fichajes: {str(e)}"
        }), 500


def _process_break_redistribution(time_entries, break_entries):
    """Process break time redistribution based on workEntryType"""
    # Group entries by date and employee
    grouped_entries = {}
    
    for entry in time_entries:
        date = entry.get('date', '')
        employee_id = entry.get('employeeId', '')
        key = f"{date}_{employee_id}"
        
        if key not in grouped_entries:
            grouped_entries[key] = {'work_entries': [], 'break_entries': []}
        
        grouped_entries[key]['work_entries'].append(entry)
    
    # Add break entries to their respective groups
    for entry in break_entries:
        date = entry.get('date', '')
        employee_id = entry.get('employeeId', '')
        key = f"{date}_{employee_id}"
        
        if key in grouped_entries:
            grouped_entries[key]['break_entries'].append(entry)
    
    # Process each group
    processed_entries = []
    
    for key, group in grouped_entries.items():
        work_entries = group['work_entries']
        break_entries = group['break_entries']
        
        # Sort work entries by start time
        work_entries.sort(key=lambda x: x.get('startTime', ''))
        
        # Calculate total break time
        total_break_seconds = 0
        for break_entry in break_entries:
            work_entry_type = break_entry.get('workEntryType', '')
            if work_entry_type == 'pause':
                start_time = break_entry.get('startTime', '')
                end_time = break_entry.get('endTime', '')
                
                if start_time and end_time:
                    try:
                        start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                        end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                        break_seconds = (end_dt - start_dt).total_seconds()
                        total_break_seconds += break_seconds
                    except:
                        pass
        
        # Redistribute break time to work entries
        if total_break_seconds > 0 and work_entries:
            break_seconds_per_entry = total_break_seconds / len(work_entries)
            
            for work_entry in work_entries:
                original_start = work_entry.get('startTime', '')
                original_end = work_entry.get('endTime', '')
                
                if original_start and original_end:
                    try:
                        start_dt = datetime.fromisoformat(original_start.replace('Z', '+00:00'))
                        end_dt = datetime.fromisoformat(original_end.replace('Z', '+00:00'))
                        
                        # Add break time to the work entry
                        new_end_dt = end_dt + timedelta(seconds=break_seconds_per_entry)
                        work_entry['endTime'] = new_end_dt.isoformat()
                    except:
                        pass
        
        processed_entries.extend(work_entries)
    
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


@main_bp.route('/conexion')
@requires_auth
def connection():
    """Connection management page"""
    return render_template('connection.html')


@main_bp.route('/apply-token', methods=['POST'])
@requires_auth
def apply_token():
    """Apply new API token"""
    try:
        data = request.get_json()
        new_token = data.get('token', '').strip()
        region = data.get('region', 'eu1')
        description = data.get('description', '')
        
        if not new_token:
            return jsonify({
                'status': 'error',
                'message': 'Token is required'
            }), 400
        
        # Import here to avoid circular imports
        from models import SesameToken
        
        # Set the new token as active
        SesameToken.set_active_token(new_token, description, region)
        
        # Test the token and get company info
        from services.sesame_api import SesameAPI
        api = SesameAPI()
        result = api.get_token_info()
        
        company_name = "Empresa no identificada"
        if result:
            if 'data' in result and 'company' in result['data']:
                company_name = result['data']['company'].get('name', 'Empresa no identificada')
            elif 'company' in result:
                company_name = result['company'].get('name', 'Empresa no identificada')
            
            # Sync check types when token is successfully configured
            try:
                from services.check_types_service import CheckTypesService
                check_types_service = CheckTypesService()
                check_types_service.sync_check_types()
                logger.info("Check types synchronized successfully after token configuration")
            except Exception as e:
                logger.warning(f"Failed to sync check types after token configuration: {str(e)}")
                # Don't fail the token configuration if check types sync fails
        
        return jsonify({
            'status': 'success',
            'message': 'Token aplicado correctamente',
            'company': company_name
        })
        
    except Exception as e:
        logger.error(f"Error applying token: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Error al aplicar el token: {str(e)}'
        }), 500


@main_bp.route('/get-current-token')
@requires_auth
def get_current_token():
    """Get information about current token (masked for security)"""
    try:
        from models import SesameToken
        from services.sesame_api import SesameAPI
        
        token_info = SesameToken.get_active_token()
        
        if token_info:
            # Get company name from API
            api = SesameAPI()
            result = api.get_token_info()
            
            company_name = "Empresa no identificada"
            if result:
                if 'data' in result and 'company' in result['data']:
                    company_name = result['data']['company'].get('name', 'Empresa no identificada')
                elif 'company' in result:
                    company_name = result['company'].get('name', 'Empresa no identificada')
            
            # Mask the token for security
            masked_token = token_info.token[:8] + '*' * (len(token_info.token) - 12) + token_info.token[-4:]
            
            return jsonify({
                'status': 'success',
                'has_token': True,
                'token': masked_token,
                'token_preview': masked_token,
                'token_length': len(token_info.token),
                'masked_token': masked_token,
                'region': token_info.region,
                'description': token_info.description or '',
                'company': company_name,
                'created_at': token_info.created_at.isoformat()
            })
        else:
            return jsonify({
                'status': 'error',
                'has_token': False,
                'message': 'No hay token configurado'
            })
            
    except Exception as e:
        logger.error(f"Error getting current token: {str(e)}")
        return jsonify({
            'status': 'error',
            'has_token': False,
            'message': f'Error al obtener información del token: {str(e)}'
        }), 500


@main_bp.route('/descargas')
@requires_auth
def downloads():
    """Downloads page - show all generated reports"""
    try:
        # Get all report files from temp directory
        temp_dir = 'temp_reports'
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir, exist_ok=True)
        
        # Get all xlsx files in temp directory
        report_files = glob.glob(os.path.join(temp_dir, '*.xlsx'))
        
        # Parse file information
        reports = []
        for file_path in report_files:
            try:
                filename = os.path.basename(file_path)
                # Extract report_id and timestamp from filename
                # Format: {report_id}_reporte_actividades_{timestamp}.xlsx
                parts = filename.split('_')
                if len(parts) >= 4:
                    report_id = parts[0]
                    timestamp_str = parts[3] + '_' + parts[4].replace('.xlsx', '')
                    
                    # Parse timestamp
                    try:
                        timestamp = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')
                    except:
                        timestamp = datetime.fromtimestamp(os.path.getmtime(file_path))
                    
                    # Get file size
                    file_size = os.path.getsize(file_path)
                    file_size_mb = round(file_size / (1024 * 1024), 2)
                    
                    reports.append({
                        'id': report_id,
                        'filename': filename,
                        'original_filename': f"reporte_actividades_{timestamp_str}.xlsx",
                        'created_at': timestamp,
                        'size_mb': file_size_mb,
                        'file_path': file_path
                    })
            except Exception as e:
                logger.warning(f"Error parsing report file {file_path}: {str(e)}")
                continue
        
        # Sort by creation date (newest first)
        reports.sort(key=lambda x: x['created_at'], reverse=True)
        
        return render_template('downloads.html', reports=reports, max_reports=MAX_REPORTS)
        
    except Exception as e:
        logger.error(f"Error in downloads page: {str(e)}")
        flash('Error al cargar la página de descargas', 'error')
        return redirect(url_for('main.index'))


@main_bp.route('/descargas/download/<report_id>')
@requires_auth
def download_report_by_id(report_id):
    """Download a specific report by ID"""
    try:
        temp_dir = 'temp_reports'
        # Find the file that starts with the report_id
        pattern = os.path.join(temp_dir, f"{report_id}_*.xlsx")
        matching_files = glob.glob(pattern)
        
        if not matching_files:
            flash('Reporte no encontrado', 'error')
            return redirect(url_for('main.downloads'))
        
        file_path = matching_files[0]
        filename = os.path.basename(file_path)
        
        # Extract original filename
        parts = filename.split('_')
        if len(parts) >= 4:
            timestamp_str = parts[3] + '_' + parts[4].replace('.xlsx', '')
            original_filename = f"reporte_actividades_{timestamp_str}.xlsx"
        else:
            original_filename = filename
        
        return send_file(file_path, as_attachment=True, download_name=original_filename)
        
    except Exception as e:
        logger.error(f"Error downloading report {report_id}: {str(e)}")
        flash('Error al descargar el reporte', 'error')
        return redirect(url_for('main.downloads'))


@main_bp.route('/descargas/delete/<report_id>', methods=['POST'])
@requires_auth
def delete_report(report_id):
    """Delete a specific report"""
    try:
        temp_dir = 'temp_reports'
        # Find the file that starts with the report_id
        pattern = os.path.join(temp_dir, f"{report_id}_*.xlsx")
        matching_files = glob.glob(pattern)
        
        if not matching_files:
            return jsonify({
                'status': 'error',
                'message': 'Reporte no encontrado'
            }), 404
        
        file_path = matching_files[0]
        
        # Delete the file
        os.remove(file_path)
        
        # Also remove from background_reports if it exists
        if report_id in background_reports:
            del background_reports[report_id]
        
        return jsonify({
            'status': 'success',
            'message': 'Reporte eliminado correctamente'
        })
        
    except Exception as e:
        logger.error(f"Error deleting report {report_id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Error al eliminar el reporte: {str(e)}'
        }), 500


@main_bp.route('/get-offices')
@requires_auth
def get_offices():
    """Get list of offices"""
    try:
        api = SesameAPI()
        response = api.get_offices()
        
        if response and 'data' in response:
            offices = response['data']
            return jsonify({
                'status': 'success',
                'offices': offices
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'No se pudieron cargar las oficinas'
            }), 500
            
    except Exception as e:
        logger.error(f"Error getting offices: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Error al obtener oficinas: {str(e)}'
        }), 500


@main_bp.route('/get-departments')
@requires_auth
def get_departments():
    """Get list of departments"""
    try:
        api = SesameAPI()
        response = api.get_departments()
        
        if response and 'data' in response:
            departments = response['data']
            return jsonify({
                'status': 'success',
                'departments': departments
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'No se pudieron cargar los departamentos'
            }), 500
            
    except Exception as e:
        logger.error(f"Error getting departments: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Error al obtener departamentos: {str(e)}'
        }), 500
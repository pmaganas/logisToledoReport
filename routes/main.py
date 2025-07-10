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

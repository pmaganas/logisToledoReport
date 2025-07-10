from flask import Blueprint, render_template, request, jsonify, send_file, flash, redirect, url_for
from datetime import datetime, timedelta
import io
import logging
from services.report_generator import ReportGenerator

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
        employee_id = request.form.get('employee_id')
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

        # Generate report
        report_generator = ReportGenerator()
        report_data = report_generator.generate_report(
            from_date=from_date,
            to_date=to_date,
            employee_id=employee_id,
            report_type=report_type
        )
        
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
        
        if not new_token:
            return jsonify({
                "status": "error",
                "message": "Token is required"
            }), 400
        
        # Update environment variable temporarily (in memory)
        import os
        old_token = os.environ.get('SESAME_TOKEN')
        os.environ['SESAME_TOKEN'] = new_token
        
        # Test new token
        report_generator = ReportGenerator()
        result = report_generator.test_connection()
        
        if result.get('status') == 'success':
            return jsonify({
                "status": "success",
                "company": result.get('company', 'Unknown'),
                "message": "Token applied successfully"
            })
        else:
            # Restore old token if test failed
            if old_token:
                os.environ['SESAME_TOKEN'] = old_token
            return jsonify({
                "status": "error",
                "message": result.get('message', 'Token test failed')
            }), 400
            
    except Exception as e:
        logger.error(f"Error applying token: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Error applying token: {str(e)}"
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

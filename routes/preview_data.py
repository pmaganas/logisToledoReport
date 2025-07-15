from flask import Blueprint, request, jsonify
from datetime import datetime
import logging
from services.optimized_report_generator import OptimizedReportGenerator

preview_bp = Blueprint('preview', __name__)
logger = logging.getLogger(__name__)

@preview_bp.route('/preview-data', methods=['POST'])
def preview_data():
    """Preview data collection metrics before generating report"""
    try:
        # Get form data
        from_date = request.form.get('from_date')
        to_date = request.form.get('to_date')
        employee_id = request.form.get('employee_id')
        office_id = request.form.get('office_id')
        department_id = request.form.get('department_id')
        
        # Validate dates
        if from_date:
            try:
                datetime.strptime(from_date, '%Y-%m-%d')
            except ValueError:
                return jsonify({'error': 'Fecha de inicio inválida'}), 400
        
        if to_date:
            try:
                datetime.strptime(to_date, '%Y-%m-%d')
            except ValueError:
                return jsonify({'error': 'Fecha de fin inválida'}), 400
        
        # Create preview generator
        preview_generator = OptimizedReportGenerator()
        
        # Get data metrics without generating full report
        metrics = preview_generator.get_data_metrics(
            from_date=from_date,
            to_date=to_date,
            employee_id=employee_id,
            office_id=office_id,
            department_id=department_id
        )
        
        return jsonify({
            'success': True,
            'metrics': metrics
        })
        
    except Exception as e:
        logger.error(f"Error getting preview data: {str(e)}")
        return jsonify({'error': f'Error al obtener vista previa: {str(e)}'}), 500
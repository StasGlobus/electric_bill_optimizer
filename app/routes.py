from flask import Blueprint, request, jsonify, send_from_directory, current_app, send_file
import os
from werkzeug.utils import secure_filename
from plan_analyzer import ElectricityPlanAnalyzer
import pandas as pd
import json
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

main = Blueprint('main', __name__)

ALLOWED_EXTENSIONS = {'csv'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@main.route('/')
def index():
    return send_from_directory('templates', 'index.html')

@main.route('/api/analyze', methods=['POST'])
def analyze():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type'}), 400
    
    try:
        # Ensure upload and output directories exist
        os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)
        os.makedirs('output', exist_ok=True)
        
        # Save the uploaded file
        filename = secure_filename(file.filename)
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Initialize and run the analyzer with the file path
        analyzer = ElectricityPlanAnalyzer(consumption_data_path=filepath)
        
        # Load consumption data (10%)
        analyzer.load_consumption_data()
        
        # Analyze plans (40%)
        plan_costs = analyzer.analyze_all_plans()
        
        # Generate visualizations (30%)
        analyzer.generate_visualizations(plan_costs)
        
        # Generate and save the report (20%)
        report_content = analyzer.generate_report(plan_costs)
        analyzer.save_report(report_content)
        
        # Get the latest report
        output_dir = 'output'
        report_files = [f for f in os.listdir(output_dir) if f.startswith('analysis_report_')]
        if not report_files:
            return jsonify({'error': 'No report generated'}), 500
        
        latest_report = max(report_files)
        with open(os.path.join(output_dir, latest_report), 'r', encoding='utf-8') as f:
            report_content = f.read()
        
        # Get visualization files with timestamps
        visualizations = {}
        for viz_file in ['plan_comparison.png', 'hourly_patterns.png', 'monthly_consumption.png', 'daily_consumption.png']:
            viz_path = os.path.join(output_dir, viz_file)
            if os.path.exists(viz_path):
                # Add timestamp to prevent caching
                timestamp = int(datetime.now().timestamp())
                visualizations[viz_file.replace('.png', '')] = f"{viz_file}?t={timestamp}"
                logger.info(f"Found visualization file: {viz_path}")
            else:
                logger.warning(f"Visualization file not found: {viz_path}")
        
        return jsonify({
            'success': True,
            'report': report_content,
            'visualizations': visualizations
        })
        
    except Exception as e:
        logger.error(f"Error during analysis: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@main.route('/output/<path:filename>')
def get_output_file(filename):
    try:
        # Remove query parameters if present
        filename = filename.split('?')[0]
        file_path = os.path.join('output', filename)
        
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return jsonify({'error': 'File not found'}), 404
            
        logger.info(f"Serving file: {file_path}")
        return send_file(file_path, mimetype='image/png' if filename.endswith('.png') else 'text/plain')
    except Exception as e:
        logger.error(f"Error serving file {filename}: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500 
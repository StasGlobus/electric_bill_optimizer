from flask import Flask, request, jsonify, send_from_directory, render_template
from flask_cors import CORS
import pandas as pd
import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO
import base64
import os
import logging
from data_analysis import analyze_data, detect_anomalies, read_electricity_data
from web_scraper import get_electricity_plans

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get the absolute path to the app directory
app_dir = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, 
    static_folder=os.path.join(app_dir, 'static'), 
    static_url_path='',
    template_folder=os.path.join(app_dir, 'app', 'templates')
)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Ensure static directory exists
static_dir = os.path.join(app_dir, 'static')
if not os.path.exists(static_dir):
    os.makedirs(static_dir)
    logger.info(f"Created static directory at {static_dir}")

@app.route('/')
def index():
    logger.info("Serving index.html from templates")
    return render_template('index.html')

@app.route('/static/<path:path>')
def serve_static(path):
    logger.info(f"Serving static file: {path}")
    return send_from_directory(static_dir, path)

@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    try:
        # Save the uploaded file temporarily
        temp_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'temp_upload.csv')
        file.save(temp_path)
        
        try:
            # Use the read_electricity_data function from data_analysis.py
            df = read_electricity_data(temp_path)
            analysis_results = analyze_data(df)
            
            # Return the response in the format expected by the frontend
            return jsonify({
                'analysis': {
                    'hourly_plot': analysis_results['hourly_plot'],
                    'plan_analysis': {
                        'plot': analysis_results['plan_analysis']['plot'],
                        'comparisons': analysis_results['plan_analysis']['comparisons']
                    }
                }
            })
            
        except Exception as e:
            logger.error(f"Error processing file: {str(e)}")
            return jsonify({'error': str(e)}), 500
            
        finally:
            # Clean up the temporary file
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
    except Exception as e:
        logger.error(f"Error handling file upload: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/plans', methods=['GET'])
def get_plans():
    try:
        plans = get_electricity_plans()
        return jsonify(plans)
    except Exception as e:
        logger.error(f"Error getting plans: {str(e)}")
        return jsonify({'error': str(e)}), 500

def create_app():
    return app

if __name__ == '__main__':
    logger.info("Starting Flask application")
    app.run(debug=True, host='0.0.0.0', port=5000) 
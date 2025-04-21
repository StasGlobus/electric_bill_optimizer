from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO
import base64
from data_analysis import analyze_data, detect_anomalies
from web_scraper import get_electricity_plans

app = Flask(__name__)
CORS(app)

@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    try:
        df = pd.read_csv(file)
        analysis_results = analyze_data(df)
        anomalies = detect_anomalies(df)
        return jsonify({
            'analysis': analysis_results,
            'anomalies': anomalies
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/plans', methods=['GET'])
def get_plans():
    try:
        plans = get_electricity_plans()
        return jsonify(plans)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True) 
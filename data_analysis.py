import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO
import base64
import re
import time
import logging
import json
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data_analysis.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def read_electricity_data(file_path):
    """Read electricity data from CSV file, handling both formats with and without metadata."""
    start_time = time.time()
    
    # Read the file to check if it contains metadata
    with open(file_path, 'r', encoding='utf-8') as f:
        first_lines = [next(f) for _ in range(15)]
    
    # Check if the file contains metadata
    has_metadata = any('שם לקוח' in line for line in first_lines)
    
    if has_metadata:
        # Find the header row
        header_row = None
        for i, line in enumerate(first_lines):
            if any(word in line for word in ['תאריך', 'צריכה בקוט"ש']):
                header_row = i
                break
        
        if header_row is None:
            raise ValueError("Could not find data headers in the file")
        
        # Read the data efficiently
        df = pd.read_csv(
            file_path,
            skiprows=header_row+2,
            encoding='utf-8',
            usecols=[0, 1, 2],
            names=['date', 'time', 'usage'],
            parse_dates={'datetime': ['date', 'time']},
            dayfirst=True,
            dtype={'usage': 'float32'},
            na_values=['', ' ', 'NA', 'N/A'],
            skip_blank_lines=True
        )
        
        # Clean up the data efficiently
        df = df.dropna(subset=['usage'])
        df['usage'] = pd.to_numeric(df['usage'], errors='coerce', downcast='float')
        
    else:
        df = pd.read_csv(
            file_path,
            encoding='utf-8',
            parse_dates=['datetime'],
            dayfirst=True,
            dtype={'usage': 'float32'}
        )
    
    logger.info(f"Data reading completed in {time.time() - start_time:.2f} seconds")
    logger.info(f"Loaded {len(df)} rows of data")
    return df

def generate_hourly_plot(df):
    """Generate a circular plot of average hourly electricity usage."""
    start_time = time.time()
    
    # Calculate average usage by hour
    df['hour'] = df['datetime'].dt.hour
    hourly_avg = df.groupby('hour')['usage'].mean()
    
    # Create circular plot
    plt.figure(figsize=(10, 10))
    ax = plt.subplot(111, polar=True)
    
    # Create the circular plot
    theta = np.linspace(0, 2*np.pi, 24, endpoint=False)
    bars = ax.bar(theta, hourly_avg.values, width=2*np.pi/24, bottom=0.0)
    
    # Customize the plot
    ax.set_theta_zero_location('N')
    ax.set_theta_direction(-1)
    ax.set_xticks(theta)
    ax.set_xticklabels([f'{h:02d}:00' for h in range(24)])
    
    # Add grid and labels
    ax.grid(True)
    plt.title('Average Hourly Electricity Usage', pad=20)
    
    # Color bars based on usage
    for bar in bars:
        bar.set_alpha(0.7)
        if bar.get_height() > hourly_avg.mean():
            bar.set_color('red')
        else:
            bar.set_color('blue')
    
    # Convert plot to base64
    buffer = BytesIO()
    plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
    buffer.seek(0)
    plt.close()
    
    logger.info(f"Hourly plot generated in {time.time() - start_time:.2f} seconds")
    return base64.b64encode(buffer.getvalue()).decode()

def analyze_plans(df, plans_file='electricity_plans_20250421_223808.json'):
    """Analyze electricity plans and compare with IEC basic rates."""
    try:
        from plan_analysis import analyze_plans as analyze_plans_new
        return analyze_plans_new(df, plans_file)
    except Exception as e:
        logger.error(f"Error analyzing plans: {str(e)}")
        return None

def analyze_data(df):
    """Analyze the electricity usage data."""
    start_time = time.time()
    
    # Ensure we have the correct columns
    if 'datetime' not in df.columns or 'usage' not in df.columns:
        raise ValueError("DataFrame must contain 'datetime' and 'usage' columns")
    
    # Generate plots
    hourly_plot = generate_hourly_plot(df)
    plan_analysis = analyze_plans(df)
    
    logger.info(f"Analysis completed in {time.time() - start_time:.2f} seconds")
    return {
        'hourly_plot': hourly_plot,
        'plan_analysis': plan_analysis
    }

def detect_anomalies(df, contamination=0.05):
    """Detect anomalies in the electricity usage data."""
    start_time = time.time()
    
    # Prepare data for anomaly detection
    X = df['usage'].values.reshape(-1, 1)
    
    # Use a smaller sample for training if the dataset is large
    sample_size = min(10000, len(X))
    if len(X) > sample_size:
        np.random.seed(42)
        sample_indices = np.random.choice(len(X), sample_size, replace=False)
        X_sample = X[sample_indices]
    else:
        X_sample = X
    
    # Train the model on the sample
    clf = IsolationForest(
        contamination=contamination,
        random_state=42,
        n_jobs=-1
    )
    clf.fit(X_sample)
    
    # Predict anomalies for the entire dataset
    predictions = clf.predict(X)
    anomalies = df[predictions == -1]
    
    logger.info(f"Anomaly detection completed in {time.time() - start_time:.2f} seconds")
    logger.info(f"Found {len(anomalies)} anomalies")
    
    return {
        'anomaly_dates': anomalies['datetime'].dt.strftime('%Y-%m-%d %H:%M').tolist(),
        'anomaly_values': anomalies['usage'].tolist()
    }

if __name__ == "__main__":
    start_time = time.time()
    
    try:
        # Read and analyze the data
        logger.info("Starting data analysis...")
        df = read_electricity_data('input.csv')
        results = analyze_data(df)
        anomalies = detect_anomalies(df)
        
        # Print results
        print("\nHourly Usage Plot:")
        print(results['hourly_plot'])
        
        print("\nPlan Analysis:")
        print(results['plan_analysis']['plot'])
        
        print("\nAnomalies Detected:")
        for date, value in zip(anomalies['anomaly_dates'], anomalies['anomaly_values']):
            print(f"Date: {date}, Usage: {value:.2f} kWh")
            
        logger.info(f"Total execution time: {time.time() - start_time:.2f} seconds")
        
    except Exception as e:
        logger.error(f"Error during execution: {str(e)}")
        raise 
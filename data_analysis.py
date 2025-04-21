import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO
import base64

def analyze_data(df):
    # Convert date column to datetime if it exists
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
    
    # Calculate basic statistics
    monthly_stats = df.groupby(df['date'].dt.to_period('M'))['usage'].agg(['mean', 'sum', 'std'])
    weekly_stats = df.groupby(df['date'].dt.to_period('W'))['usage'].agg(['mean', 'sum', 'std'])
    
    # Generate plots
    monthly_plot = generate_monthly_plot(df)
    weekly_plot = generate_weekly_plot(df)
    
    return {
        'monthly_stats': monthly_stats.to_dict(),
        'weekly_stats': weekly_stats.to_dict(),
        'monthly_plot': monthly_plot,
        'weekly_plot': weekly_plot
    }

def detect_anomalies(df):
    # Prepare data for anomaly detection
    X = df['usage'].values.reshape(-1, 1)
    
    # Use Isolation Forest for anomaly detection
    clf = IsolationForest(contamination=0.1, random_state=42)
    predictions = clf.fit_predict(X)
    
    # Get anomaly indices
    anomalies = df[predictions == -1]
    
    return {
        'anomaly_dates': anomalies['date'].dt.strftime('%Y-%m-%d').tolist(),
        'anomaly_values': anomalies['usage'].tolist()
    }

def generate_monthly_plot(df):
    plt.figure(figsize=(12, 6))
    monthly_usage = df.groupby(df['date'].dt.to_period('M'))['usage'].sum()
    monthly_usage.plot(kind='bar')
    plt.title('Monthly Electricity Usage')
    plt.xlabel('Month')
    plt.ylabel('Usage (kWh)')
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    # Convert plot to base64
    buffer = BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    return base64.b64encode(buffer.getvalue()).decode()

def generate_weekly_plot(df):
    plt.figure(figsize=(12, 6))
    weekly_usage = df.groupby(df['date'].dt.to_period('W'))['usage'].sum()
    weekly_usage.plot(kind='line', marker='o')
    plt.title('Weekly Electricity Usage')
    plt.xlabel('Week')
    plt.ylabel('Usage (kWh)')
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    # Convert plot to base64
    buffer = BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    return base64.b64encode(buffer.getvalue()).decode() 
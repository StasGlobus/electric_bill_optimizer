# Electric Bill Optimizer

A web application that helps users analyze their electricity usage and find the best electricity plans for their needs.

## Features

- Upload and analyze electricity usage data
- Visualize monthly and weekly usage patterns
- Detect usage anomalies
- Compare and recommend electricity plans
- Web scraping of current electricity plans

## Setup

### Backend Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the Flask server:
```bash
python app.py
```

### Frontend Setup

1. Install Node.js dependencies:
```bash
npm install
```

2. Start the React development server:
```bash
npm start
```

## Usage

1. Open your browser and navigate to `http://localhost:3000`
2. Upload your electricity usage data in CSV format
3. View the analysis of your usage patterns
4. Check the recommended electricity plans based on your usage

## Data Format

The application expects a CSV file with the following columns:
- date: The date of the reading (YYYY-MM-DD format)
- usage: The electricity usage in kWh

## Technologies Used

- Backend: Python, Flask, Pandas, NumPy, Matplotlib, BeautifulSoup
- Frontend: React, Material-UI, Axios
- Data Analysis: scikit-learn, pandas
- Web Scraping: BeautifulSoup, requests

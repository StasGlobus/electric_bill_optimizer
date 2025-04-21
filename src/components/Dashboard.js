import React, { useState } from 'react';
import {
  Paper,
  Typography,
  Button,
  Grid,
  Card,
  CardContent,
  Box,
} from '@material-ui/core';
import { makeStyles } from '@material-ui/core/styles';
import axios from 'axios';

const useStyles = makeStyles((theme) => ({
  root: {
    padding: theme.spacing(3),
  },
  uploadArea: {
    padding: theme.spacing(3),
    textAlign: 'center',
    marginBottom: theme.spacing(3),
  },
  graph: {
    marginTop: theme.spacing(2),
  },
  anomalyCard: {
    marginTop: theme.spacing(2),
  },
}));

function Dashboard() {
  const classes = useStyles();
  const [file, setFile] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [anomalies, setAnomalies] = useState(null);

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    setFile(file);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post('http://localhost:5000/api/upload', formData);
      setAnalysis(response.data.analysis);
      setAnomalies(response.data.anomalies);
    } catch (error) {
      console.error('Error uploading file:', error);
    }
  };

  return (
    <div className={classes.root}>
      <Paper className={classes.uploadArea}>
        <Typography variant="h5" gutterBottom>
          Upload Your Electricity Usage Data
        </Typography>
        <input
          accept=".csv"
          style={{ display: 'none' }}
          id="raised-button-file"
          type="file"
          onChange={handleFileUpload}
        />
        <label htmlFor="raised-button-file">
          <Button variant="contained" component="span" color="primary">
            Upload File
          </Button>
        </label>
      </Paper>

      {analysis && (
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Monthly Usage
                </Typography>
                <img
                  src={`data:image/png;base64,${analysis.monthly_plot}`}
                  alt="Monthly Usage"
                  className={classes.graph}
                />
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Weekly Usage
                </Typography>
                <img
                  src={`data:image/png;base64,${analysis.weekly_plot}`}
                  alt="Weekly Usage"
                  className={classes.graph}
                />
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {anomalies && anomalies.anomaly_dates.length > 0 && (
        <Card className={classes.anomalyCard}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Usage Anomalies Detected
            </Typography>
            <Box>
              {anomalies.anomaly_dates.map((date, index) => (
                <Typography key={date}>
                  Date: {date} - Usage: {anomalies.anomaly_values[index]} kWh
                </Typography>
              ))}
            </Box>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

export default Dashboard; 
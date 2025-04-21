import React, { useState, useEffect } from 'react';
import {
  Card,
  CardContent,
  Typography,
  Grid,
  Paper,
  Box,
} from '@material-ui/core';
import { makeStyles } from '@material-ui/core/styles';
import axios from 'axios';

const useStyles = makeStyles((theme) => ({
  root: {
    padding: theme.spacing(3),
  },
  planCard: {
    height: '100%',
  },
  bestPlan: {
    border: `2px solid ${theme.palette.primary.main}`,
  },
  featureList: {
    marginTop: theme.spacing(2),
  },
}));

function Plans() {
  const classes = useStyles();
  const [plans, setPlans] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchPlans = async () => {
      try {
        const response = await axios.get('http://localhost:5000/api/plans');
        setPlans(response.data);
        setLoading(false);
      } catch (error) {
        setError('Failed to fetch electricity plans');
        setLoading(false);
      }
    };

    fetchPlans();
  }, []);

  if (loading) {
    return <Typography>Loading plans...</Typography>;
  }

  if (error) {
    return <Typography color="error">{error}</Typography>;
  }

  if (!plans) {
    return <Typography>No plans available</Typography>;
  }

  return (
    <div className={classes.root}>
      <Typography variant="h4" gutterBottom>
        Recommended Electricity Plans
      </Typography>

      <Grid container spacing={3}>
        {plans.best_plan && (
          <Grid item xs={12}>
            <Paper elevation={3} className={classes.bestPlan}>
              <Box p={3}>
                <Typography variant="h5" color="primary" gutterBottom>
                  Best Plan for You
                </Typography>
                <Typography variant="h6">{plans.best_plan.name}</Typography>
                <Typography variant="h4" color="primary">
                  {plans.best_plan.price}
                </Typography>
                <Box className={classes.featureList}>
                  {plans.best_plan.features.map((feature, index) => (
                    <Typography key={index}>• {feature}</Typography>
                  ))}
                </Box>
              </Box>
            </Paper>
          </Grid>
        )}

        {plans.second_best && (
          <Grid item xs={12} md={6}>
            <Card className={classes.planCard}>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Second Best Option
                </Typography>
                <Typography variant="h6">{plans.second_best.name}</Typography>
                <Typography variant="h5" color="primary">
                  {plans.second_best.price}
                </Typography>
                <Box className={classes.featureList}>
                  {plans.second_best.features.map((feature, index) => (
                    <Typography key={index}>• {feature}</Typography>
                  ))}
                </Box>
              </CardContent>
            </Card>
          </Grid>
        )}

        {plans.third_best && (
          <Grid item xs={12} md={6}>
            <Card className={classes.planCard}>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Third Best Option
                </Typography>
                <Typography variant="h6">{plans.third_best.name}</Typography>
                <Typography variant="h5" color="primary">
                  {plans.third_best.price}
                </Typography>
                <Box className={classes.featureList}>
                  {plans.third_best.features.map((feature, index) => (
                    <Typography key={index}>• {feature}</Typography>
                  ))}
                </Box>
              </CardContent>
            </Card>
          </Grid>
        )}
      </Grid>
    </div>
  );
}

export default Plans; 
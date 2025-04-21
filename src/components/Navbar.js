import React from 'react';
import { AppBar, Toolbar, Typography, Button } from '@material-ui/core';
import { Link as RouterLink } from 'react-router-dom';
import { makeStyles } from '@material-ui/core/styles';

const useStyles = makeStyles((theme) => ({
  root: {
    flexGrow: 1,
  },
  title: {
    flexGrow: 1,
  },
  link: {
    color: 'white',
    textDecoration: 'none',
  },
}));

function Navbar() {
  const classes = useStyles();

  return (
    <div className={classes.root}>
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" className={classes.title}>
            Electric Bill Optimizer
          </Typography>
          <Button color="inherit">
            <RouterLink to="/" className={classes.link}>
              Dashboard
            </RouterLink>
          </Button>
          <Button color="inherit">
            <RouterLink to="/plans" className={classes.link}>
              Electricity Plans
            </RouterLink>
          </Button>
        </Toolbar>
      </AppBar>
    </div>
  );
}

export default Navbar; 
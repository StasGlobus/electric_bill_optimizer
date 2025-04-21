import React from 'react';
import { BrowserRouter as Router, Route, Switch } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@material-ui/core/styles';
import CssBaseline from '@material-ui/core/CssBaseline';
import Navbar from './components/Navbar';
import Dashboard from './components/Dashboard';
import Plans from './components/Plans';
import { Container } from '@material-ui/core';

const theme = createTheme({
  palette: {
    primary: {
      main: '#2196f3',
    },
    secondary: {
      main: '#f50057',
    },
  },
});

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Router>
        <Navbar />
        <Container maxWidth="lg" style={{ marginTop: '2rem' }}>
          <Switch>
            <Route exact path="/" component={Dashboard} />
            <Route path="/plans" component={Plans} />
          </Switch>
        </Container>
      </Router>
    </ThemeProvider>
  );
}

export default App; 
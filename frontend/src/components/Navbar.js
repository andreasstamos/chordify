import React, { useContext } from 'react';
import {
  AppBar,
  Toolbar,
  Typography,
  Button,
  Box
} from '@mui/material';
import { Link, useNavigate } from 'react-router-dom';
import { AuthContext } from '../context/AuthContext';

function Navbar() {
  const { isLoggedIn, logout } = useContext(AuthContext);
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <AppBar position="static" sx={{ mb: 2 }}>
      <Toolbar sx={{ display: 'flex', justifyContent: 'space-between' }}>
        <Typography variant="h6">Chord DHT Management</Typography>

        {isLoggedIn ? (
          <Box>
            <Button color="inherit" component={Link} to="/">
              Home
            </Button>
            <Button color="inherit" component={Link} to="/node-selection">
              Node Selection
            </Button>
            <Button color="inherit" component={Link} to="/physical-management">
              Physical Management
            </Button>
            <Button color="inherit" component={Link} to="/chord-operations">
              DHT Operations
            </Button>
            <Button color="inherit" component={Link} to="/overlay">
              Overlay
            </Button>

            <Button color="inherit" onClick={handleLogout} sx={{ ml: 3 }}>
              Logout
            </Button>
          </Box>
        ) : (
          <Button color="inherit" component={Link} to="/login">
            Login
          </Button>
        )}
      </Toolbar>
    </AppBar>
  );
}

export default Navbar;


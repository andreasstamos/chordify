import React, { useContext, useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  Button,
  Snackbar,
  Alert,
  Divider,
  CircularProgress,
  Fade,
  Checkbox,
  FormControlLabel,
  Link,
  IconButton
} from '@mui/material';
import { Close as CloseIcon } from '@mui/icons-material';
import { AuthContext } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';

function LoginPage() {
  const { login, checkCredentials } = useContext(AuthContext);
  const navigate = useNavigate();

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');

  const [snackbarOpen, setSnackbarOpen] = useState(false);
  const [snackbarMessage, setSnackbarMessage] = useState('');
  const [alertSeverity, setAlertSeverity] = useState('info');
  const [loading, setLoading] = useState(false);

  const handleCloseSnackbar = () => setSnackbarOpen(false);

  const showSnackbar = (msg, severity = 'info') => {
    setSnackbarMessage(msg);
    setAlertSeverity(severity);
    setSnackbarOpen(true);
  };

  const handleLogin = async () => {
    if (!username || !password) {
      showSnackbar('Please enter both username and password.', 'warning');
      return;
    }

    setLoading(true);

    const isValid = await checkCredentials(username, password);
    if (!isValid) {
      showSnackbar('Invalid credentials.', 'error');
      setLoading(false);
      return;
    }

    login(username, password);
    showSnackbar('Login successful!', 'success');
    setLoading(false);

    setTimeout(() => {
      navigate('/');
    }, 800);
  };

  return (
    <Box
      sx={{
        minHeight: '100vh',
        width: '100%',
        overflow: 'hidden',

        background: 'linear-gradient(270deg, #757F9A, #D7DDE8)',
        backgroundSize: '400% 400%',
        animation: 'gradientMove 15s ease infinite',
        '@keyframes gradientMove': {
          '0%': { backgroundPosition: '0% 50%' },
          '50%': { backgroundPosition: '100% 50%' },
          '100%': { backgroundPosition: '0% 50%' }
        },

        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        p: 2
      }}
    >
      <Fade in timeout={700}>
        <Card
          sx={{
            width: '100%',
            maxWidth: 420,
            p: 2,
            borderRadius: 3,
            backdropFilter: 'blur(9px)',
            backgroundColor: 'rgba(255, 255, 255, 0.35)',
            boxShadow: '0 8px 32px 0 rgba(31, 38, 135, 0.3)',
            border: '1px solid rgba(255, 255, 255, 0.2)'
          }}
        >
          <CardContent sx={{ position: 'relative' }}>
            {/* Optional Logo */}
            {/* 
            <Box sx={{ display: 'flex', justifyContent: 'center', mb: 2 }}>
              <img src="/path/to/logo.png" alt="Company Logo" style={{ width: 70, height: 70 }} />
            </Box> 
            */}
            
            <Typography
              variant="h5"
              gutterBottom
              textAlign="center"
              sx={{ fontWeight: 'medium' }}
            >
              Sign in to Your Account
            </Typography>

            <Typography
              variant="body2"
              align="center"
              sx={{ mb: 3 }}
              color="text.secondary"
            >
              Access your Chord DHT Management
            </Typography>

            <Divider sx={{ mb: 3, borderColor: 'rgba(255,255,255,0.4)' }} />

            {/* Username Field */}
            <TextField
              label="Username"
              variant="outlined"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              fullWidth
              sx={{ mb: 2 }}
            />

            {/* Password Field */}
            <TextField
              label="Password"
              variant="outlined"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              fullWidth
              sx={{ mb: 2 }}
            />

           
            {/* Login Button or Spinner */}
            {loading ? (
              <Box sx={{ display: 'flex', justifyContent: 'center' }}>
                <CircularProgress />
              </Box>
            ) : (
              <Button
                variant="contained"
                fullWidth
                size="large"
                onClick={handleLogin}
                sx={{
                  fontWeight: 'bold',
                  py: 1.2
                }}
              >
                Sign In
              </Button>
            )}
          </CardContent>
        </Card>
      </Fade>

      {/* Snackbar for Feedback */}
      <Snackbar
        open={snackbarOpen}
        autoHideDuration={3000}
        onClose={handleCloseSnackbar}
        anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
      >
        <Alert
          severity={alertSeverity}
          onClose={handleCloseSnackbar}
          sx={{ width: '100%' }}
          action={
            <IconButton
              aria-label="close"
              color="inherit"
              size="small"
              onClick={handleCloseSnackbar}
            >
              <CloseIcon fontSize="inherit" />
            </IconButton>
          }
        >
          {snackbarMessage}
        </Alert>
      </Snackbar>
    </Box>
  );
}

export default LoginPage;


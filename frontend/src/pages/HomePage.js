import React from 'react';
import {
  Box,
  Typography,
  Button,
  Fade
} from '@mui/material';
import { Link } from 'react-router-dom';

function HomePage() {
  return (
    <Box
      sx={{
        minHeight: '100vh',
        width: '100%',
        overflow: 'hidden',

        background: 'linear-gradient(270deg, #3a1c71, #d76d77, #ffaf7b)',
        backgroundSize: '400% 400%',
        animation: 'gradientShift 12s ease infinite',
        '@keyframes gradientShift': {
          '0%': { backgroundPosition: '0% 50%' },
          '50%': { backgroundPosition: '100% 50%' },
          '100%': { backgroundPosition: '0% 50%' }
        },

        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        p: 2
      }}
    >
      <Fade in timeout={900}>
        <Box
          sx={{
            textAlign: 'center',
            color: '#fff',
            maxWidth: 600
          }}
        >
          <Typography variant="h2" sx={{ fontWeight: 'bold', mb: 2 }}>
            Welcome to Chord DHT
          </Typography>
          <Typography variant="body1" sx={{ mb: 3, fontSize: 18 }}>
            Experience a powerful and intuitive interface to manage your distributed Chord ring,
            spawn and kill nodes, and perform all DHT operations with ease.
          </Typography>

          <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center', flexWrap: 'wrap' }}>
            <Button
              component={Link}
              to="/node-selection"
              variant="contained"
              color="primary"
              sx={{ fontWeight: 'medium', px: 3, py: 1.2 }}
            >
              Get Started
            </Button>
            <Button
              component={Link}
              to="/chord-operations"
              variant="outlined"
              color="inherit"
              sx={{ fontWeight: 'medium', px: 3, py: 1.2 }}
            >
              DHT Operations
            </Button>
          </Box>
        </Box>
      </Fade>
    </Box>
  );
}

export default HomePage;


import React from 'react';
import { Box, Typography, Button, Container, Fade } from '@mui/material';
import { useNavigate } from 'react-router-dom';

function ErrorPage({ errorCode, errorMessage }) {
  const navigate = useNavigate();

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        background: 'linear-gradient(135deg, #0f2027, #203a43, #2c5364)',
        backgroundSize: '200% 200%',
        animation: 'gradientAnimation 15s ease infinite',
        '@keyframes gradientAnimation': {
          '0%': { backgroundPosition: '0% 50%' },
          '50%': { backgroundPosition: '100% 50%' },
          '100%': { backgroundPosition: '0% 50%' },
        },
        alignItems: 'center',
        justifyContent: 'center',
        p: 2,
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      <Fade in timeout={1000}>
        <Container maxWidth="sm" sx={{ textAlign: 'center', color: '#fff' }}>
          <Typography
            variant="h1"
            sx={{
              fontWeight: 'bold',
              mb: 2,
              fontSize: { xs: '4rem', sm: '6rem' },
              animation: 'glitch 1.5s linear infinite',
              '@keyframes glitch': {
                '0%': { textShadow: '2px 2px red, -2px -2px cyan' },
                '20%': { textShadow: '-2px -2px red, 2px 2px cyan' },
                '40%': { textShadow: '2px -2px red, -2px 2px cyan' },
                '60%': { textShadow: '-2px 2px red, 2px -2px cyan' },
                '80%': { textShadow: '2px 2px red, -2px -2px cyan' },
                '100%': { textShadow: '-2px -2px red, 2px 2px cyan' },
              },
            }}
          >
            {errorCode || '404'}
          </Typography>
          <Typography variant="h4" sx={{ fontWeight: 'bold', mb: 2 }}>
            Oops, something went wrong.
          </Typography>
          <Typography variant="body1" sx={{ mb: 4 }}>
            {errorMessage ||
              "We couldn't find the page you're looking for. It might have been moved or deleted."}
          </Typography>
          <Button
            variant="contained"
            size="large"
            sx={{
              px: 4,
              py: 1.5,
              fontWeight: 'bold',
              backgroundColor: '#ff5e62',
              '&:hover': { backgroundColor: '#ff9966' },
              animation: 'bounce 2s infinite',
              '@keyframes bounce': {
                '0%, 20%, 50%, 80%, 100%': { transform: 'translateY(0)' },
                '40%': { transform: 'translateY(-10px)' },
                '60%': { transform: 'translateY(-5px)' },
              },
            }}
            onClick={() => navigate('/')}
          >
            Back to Home
          </Button>
        </Container>
      </Fade>
    </Box>
  );
}

export default ErrorPage;


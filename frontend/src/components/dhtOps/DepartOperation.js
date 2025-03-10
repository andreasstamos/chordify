import React, { useState } from 'react';
import {
  Paper,
  Typography,
  Button,
  Snackbar,
  Alert,
  Collapse
} from '@mui/material';
import EjectIcon from '@mui/icons-material/Eject';

function DepartOperation({ onDepart }) {
  const [result, setResult] = useState(null);
  const [showResult, setShowResult] = useState(false);

  const [snackbarOpen, setSnackbarOpen] = useState(false);
  const [snackbarMessage, setSnackbarMessage] = useState('');
  const [snackbarSeverity, setSnackbarSeverity] = useState('info');

  const handleCloseSnackbar = () => setSnackbarOpen(false);

  const showSnackbar = (msg, severity = 'info') => {
    setSnackbarMessage(msg);
    setSnackbarSeverity(severity);
    setSnackbarOpen(true);
  };

  const handleDepart = async () => {
    try {
      const resp = await onDepart();
      setResult(resp);
      setShowResult(true);
      showSnackbar('Departed successfully!', 'success');
    } catch (error) {
      showSnackbar(`Depart error: ${error.message}`, 'error');
    }
  };

  return (
    <Paper sx={{ p: 3, mb: 3, boxShadow: 4 }}>
      <Typography variant="h6" gutterBottom>
        Depart (Non-Bootstrap Only)
      </Typography>
      <Button
        variant="contained"
        color="error"
        startIcon={<EjectIcon />}
        onClick={handleDepart}
      >
        Depart
      </Button>

      <Collapse in={showResult} sx={{ mt: 2 }}>
        <Paper variant="outlined" sx={{ p: 2 }}>
          <Typography variant="subtitle2">Operation Result:</Typography>
          <Typography variant="body2">{JSON.stringify(result)}</Typography>
        </Paper>
      </Collapse>

      <Snackbar
        open={snackbarOpen}
        autoHideDuration={3000}
        onClose={handleCloseSnackbar}
      >
        <Alert
          onClose={handleCloseSnackbar}
          severity={snackbarSeverity}
          sx={{ width: '100%' }}
        >
          {snackbarMessage}
        </Alert>
      </Snackbar>
    </Paper>
  );
}

export default DepartOperation;


import React, { useState } from 'react';
import {
  Paper,
  Typography,
  TextField,
  Button,
  Snackbar,
  Alert,
  Collapse
} from '@mui/material';
import RemoveCircleOutlineIcon from '@mui/icons-material/RemoveCircleOutline';

function DeleteOperation({ onDelete }) {
  const [keyField, setKeyField] = useState('');
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

  const handleDelete = async () => {
    if (!keyField) {
      showSnackbar('Please provide a key.', 'warning');
      return;
    }
    try {
      const resp = await onDelete(keyField);
      setResult(resp);
      setShowResult(true);
      showSnackbar(`Delete success for key: "${keyField}"`, 'success');
    } catch (error) {
      showSnackbar(`Delete error: ${error.message}`, 'error');
    }
  };

  return (
    <Paper sx={{ p: 3, mb: 3, boxShadow: 4 }}>
      <Typography variant="h6" gutterBottom>
        Delete Key
      </Typography>

      <TextField
        label="Key"
        value={keyField}
        onChange={(e) => setKeyField(e.target.value)}
        sx={{ mr: 2, mb: 2 }}
      />
      <br />

      <Button
        variant="contained"
        color="warning"
        startIcon={<RemoveCircleOutlineIcon />}
        onClick={handleDelete}
      >
        Delete
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

export default DeleteOperation;


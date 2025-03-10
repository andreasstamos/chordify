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
import AddCircleOutlineIcon from '@mui/icons-material/AddCircleOutline';

function InsertOperation({ onInsert }) {
  const [keyField, setKeyField] = useState('');
  const [valueField, setValueField] = useState('');
  const [result, setResult] = useState(null);
  const [showResult, setShowResult] = useState(false);

  const [snackbarOpen, setSnackbarOpen] = useState(false);
  const [snackbarMessage, setSnackbarMessage] = useState('');
  const [snackbarSeverity, setSnackbarSeverity] = useState('info');

  const handleCloseSnackbar = () => setSnackbarOpen(false);

  const showSnackbar = (msg, severity) => {
    setSnackbarMessage(msg);
    setSnackbarSeverity(severity);
    setSnackbarOpen(true);
  };

  const handleInsert = async () => {
    if (!keyField || !valueField) {
      showSnackbar('Please provide key and value', 'warning');
      return;
    }
    try {
      const resp = await onInsert(keyField, valueField);
      setResult(resp);
      setShowResult(true);
      showSnackbar(`Insert success for key: ${keyField}`, 'success');
    } catch (error) {
      showSnackbar(`Insert error: ${error.message}`, 'error');
    }
  };

  return (
    <Paper sx={{ p: 3, mb: 3, transition: '0.3s', boxShadow: 4 }}>
      <Typography variant="h6" gutterBottom>
        Insert Key-Value
      </Typography>
      <TextField
        label="Key"
        value={keyField}
        onChange={(e) => setKeyField(e.target.value)}
        sx={{ mr: 2, mb: 2 }}
      />
      <TextField
        label="Value"
        value={valueField}
        onChange={(e) => setValueField(e.target.value)}
        sx={{ mb: 2 }}
      />
      <br />
      <Button
        variant="contained"
        startIcon={<AddCircleOutlineIcon />}
        onClick={handleInsert}
      >
        Insert
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
        <Alert onClose={handleCloseSnackbar} severity={snackbarSeverity} sx={{ width: '100%' }}>
          {snackbarMessage}
        </Alert>
      </Snackbar>
    </Paper>
  );
}

export default InsertOperation;


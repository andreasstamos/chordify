import React, { useState } from 'react';
import {
  Paper,
  Typography,
  TextField,
  Button,
  Box,
  Snackbar,
  Alert,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Collapse
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';

function QueryOperation({ onQueryKey, onQueryAll }) {
  const [queryKey, setQueryKey] = useState('');
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

  const handleQueryKey = async () => {
    if (!queryKey) {
      showSnackbar('Please enter a key.', 'warning');
      return;
    }
    try {
      const resp = await onQueryKey(queryKey);
      setResult(resp);
      setShowResult(true);
      showSnackbar(`Query success for key: "${queryKey}"`, 'success');
    } catch (error) {
      showSnackbar(`Query error: ${error.message}`, 'error');
    }
  };

  const handleQueryAll = async () => {
    try {
      const resp = await onQueryAll();
      setResult(resp);
      setShowResult(true);
      showSnackbar('Query All success', 'success');
    } catch (error) {
      showSnackbar(`QueryAll error: ${error.message}`, 'error');
    }
  };

  const renderResult = (res) => {
    if (!res) {
      return (
        <Typography variant="body2" sx={{ mt: 2 }}>
          No result or empty
        </Typography>
      );
    }

    if (typeof res === 'object' && !Array.isArray(res)) {
      const keys = Object.keys(res);
      if (keys.length === 0) {
        return (
          <Typography variant="body2" sx={{ mt: 2 }}>
            (No data in the DHT)
          </Typography>
        );
      }
      return (
        <Table sx={{ mt: 2 }} size="small">
          <TableHead>
            <TableRow>
              <TableCell><strong>Key</strong></TableCell>
              <TableCell><strong>Value</strong></TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {keys.map((k) => (
              <TableRow key={k}>
                <TableCell>{k}</TableCell>
                <TableCell>{JSON.stringify(res[k])}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      );
    }

    return (
      <Box sx={{ mt: 2 }}>
        <Typography variant="body2">{JSON.stringify(res)}</Typography>
      </Box>
    );
  };

  return (
    <Paper sx={{ p: 3, mb: 3, boxShadow: 4 }}>
      <Typography variant="h6" gutterBottom>
        Query
      </Typography>
      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, mb: 2 }}>
        <TextField
          label="Key"
          value={queryKey}
          onChange={(e) => setQueryKey(e.target.value)}
        />
        <Button variant="contained" startIcon={<SearchIcon />} onClick={handleQueryKey}>
          Query Key
        </Button>
        <Button variant="outlined" startIcon={<SearchIcon />} onClick={handleQueryAll}>
          Query All (*)
        </Button>
      </Box>

      <Collapse in={showResult}>
        <Paper variant="outlined" sx={{ p: 2 }}>
          <Typography variant="subtitle2" sx={{ mb: 1 }}>
            Operation Result
          </Typography>
          {renderResult(result)}
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

export default QueryOperation;


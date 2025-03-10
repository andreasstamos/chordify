import React, { useContext, useState } from 'react';
import {
  Box,
  Typography,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  TextField,
  Button,
  Snackbar,
  Alert,
  CircularProgress,
  FormControl,
  InputLabel,
  Select,
  MenuItem
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import DeleteForeverIcon from '@mui/icons-material/DeleteForever';
import PageTitle from '../components/PageTitle';
import { AppContext } from '../context/AppContext';
import { managerRequest } from '../api/apiClient';

function PhysicalManagementPage() {
  const { managerBaseURL, selectedWorkerId, setSelectedWorkerId } = useContext(AppContext);

  const [consistencyModel, setConsistencyModel] = useState('LINEARIZABLE');
  const [repFactor, setRepFactor] = useState(1);

  const [spawnResult, setSpawnResult] = useState('');
  const [bootstrapResult, setBootstrapResult] = useState('');
  const [killAllResult, setKillAllResult] = useState('');

  const [loading, setLoading] = useState(false);
  const [snackbarOpen, setSnackbarOpen] = useState(false);
  const [snackbarMessage, setSnackbarMessage] = useState('');
  const [alertSeverity, setAlertSeverity] = useState('success');

  const handleCloseSnackbar = () => setSnackbarOpen(false);

  const showAlert = (message, severity = 'success') => {
    setSnackbarMessage(message);
    setAlertSeverity(severity);
    setSnackbarOpen(true);
  };

  const handleSpawn = async () => {
    if (!managerBaseURL) {
      showAlert('Please select a Physical Node first!', 'warning');
      return;
    }
    try {
      setLoading(true);
      const resp = await managerRequest(managerBaseURL, 'spawn');
      setSpawnResult(JSON.stringify(resp));
      showAlert('Spawned a new Logical Worker!', 'success');

      setSelectedWorkerId(null);
    } catch (error) {
      showAlert(error.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleSpawnBootstrap = async () => {
    if (!managerBaseURL) {
      showAlert('Please select a Physical Node first!', 'warning');
      return;
    }
    try {
      setLoading(true);
      const resp = await managerRequest(managerBaseURL, 'spawnBootstrap', {
        consistency_model: consistencyModel,
        replication_factor: repFactor
      });
      if (resp.error) {
        setBootstrapResult(`Error: ${resp.error}`);
        showAlert(`Error: ${resp.error}`, 'error');
      } else {
        setBootstrapResult(JSON.stringify(resp));
        showAlert('Spawned the Bootstrap Node!', 'success');
      }

      setSelectedWorkerId(null);
    } catch (error) {
      showAlert(error.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleKillAll = async () => {
    if (!managerBaseURL) {
      showAlert('Please select a Physical Node first!', 'warning');
      return;
    }
    try {
      setLoading(true);
      const resp = await managerRequest(managerBaseURL, 'killall');
      setKillAllResult(JSON.stringify(resp));
      showAlert('Killed all Logical Workers!', 'success');

      setSelectedWorkerId(null);
    } catch (error) {
      showAlert(error.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box sx={{ p : 3 }}>
      <PageTitle
        title="Physical Node Management"
        subtitle="Spawn, kill, or bootstrap nodes on the selected Physical Node."
      />
      <Typography variant="body1" gutterBottom>
        Current Physical Node: {managerBaseURL || 'None'}
      </Typography>
      <Typography variant="body2" gutterBottom>
        Selected Worker ID: {selectedWorkerId ?? 'N/A'}
      </Typography>

      <Accordion sx={{ mt: 2 }}>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography variant="subtitle1">Spawn a Regular Worker</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Button
            variant="contained"
            onClick={handleSpawn}
            disabled={loading}
            startIcon={<CheckCircleOutlineIcon />}
          >
            Spawn
          </Button>
          {spawnResult && (
            <Typography variant="body2" sx={{ mt: 1 }}>
              Result: {spawnResult}
            </Typography>
          )}
        </AccordionDetails>
      </Accordion>

      <Accordion>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography variant="subtitle1">Spawn a Bootstrap Worker</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <FormControl sx={{ display: 'block', mb: 2, maxWidth: 300 }}>
            <InputLabel id="consistency-model-label">Consistency Model</InputLabel>
            <Select
              labelId="consistency-model-label"
              label="Consistency Model"
              value={consistencyModel}
              onChange={(e) => setConsistencyModel(e.target.value)}
            >
              <MenuItem value="LINEARIZABLE">LINEARIZABLE</MenuItem>
              <MenuItem value="EVENTUAL">EVENTUAL</MenuItem>
            </Select>
          </FormControl>
          <TextField
            label="Replication Factor"
            type="number"
            value={repFactor}
            onChange={(e) => setRepFactor(parseInt(e.target.value, 10))}
            sx={{ display: 'block', maxWidth: 300, mb: 2 }}
          />
          <Button
            variant="contained"
            onClick={handleSpawnBootstrap}
            disabled={loading}
            startIcon={<CheckCircleOutlineIcon />}
          >
            Spawn Bootstrap
          </Button>
          {bootstrapResult && (
            <Typography variant="body2" sx={{ mt: 1 }}>
              Result: {bootstrapResult}
            </Typography>
          )}
        </AccordionDetails>
      </Accordion>

      <Accordion>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography variant="subtitle1">Kill All Workers</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Button
            variant="contained"
            color="error"
            onClick={handleKillAll}
            disabled={loading}
            startIcon={<DeleteForeverIcon />}
          >
            Kill All
          </Button>
          {killAllResult && (
            <Typography variant="body2" sx={{ mt: 1 }}>
              Result: {killAllResult}
            </Typography>
          )}
        </AccordionDetails>
      </Accordion>

      {loading && (
        <Box sx={{ mt: 3 }}>
          <CircularProgress />
        </Box>
      )}

      <Snackbar
        open={snackbarOpen}
        autoHideDuration={3000}
        onClose={handleCloseSnackbar}
      >
        <Alert
          onClose={handleCloseSnackbar}
          severity={alertSeverity}
          sx={{ width: '100%' }}
        >
          {snackbarMessage}
        </Alert>
      </Snackbar>
    </Box>
  );
}

export default PhysicalManagementPage;


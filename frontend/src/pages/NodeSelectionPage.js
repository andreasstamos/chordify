import React, { useContext, useState } from 'react';
import {
  Box,
  Typography,
  Stepper,
  Step,
  StepLabel,
  Button,
  Grow,
  CircularProgress,
  Snackbar,
  Alert
} from '@mui/material';

import { AppContext } from '../context/AppContext';
import { managerRequest } from '../api/apiClient';
import PhysicalNodeCards from '../components/PhysicalNodeCards';
import LogicalList from '../components/LogicalList';
import ManualLogicalInput from '../components/ManualLogicalInput';
import PageTitle from '../components/PageTitle';
import { physical_urls } from '../config/Config';

const steps = ['Select Physical Node', 'List Logicals', 'Select Worker ID'];

function NodeSelectionPage() {
  const {
    managerBaseURL,
    setManagerBaseURL,
    selectedWorkerId,
    setSelectedWorkerId
  } = useContext(AppContext);

  const [activeStep, setActiveStep] = useState(0);
  const [logicals, setLogicals] = useState([]);
  const [loadingLogicals, setLoadingLogicals] = useState(false);

  const [snackbarOpen, setSnackbarOpen] = useState(false);
  const [snackbarMessage, setSnackbarMessage] = useState('');
  const [alertSeverity, setAlertSeverity] = useState('info');

  const handleCloseSnackbar = () => setSnackbarOpen(false);
  const showSnackbar = (msg, severity = 'info') => {
    setSnackbarMessage(msg);
    setAlertSeverity(severity);
    setSnackbarOpen(true);
  };

  const goNext = () => setActiveStep((prev) => Math.min(prev + 1, steps.length - 1));
  const goBack = () => setActiveStep((prev) => Math.max(prev - 1, 0));

  // Step 1: Select Physical
  const handleSelectPhysical = (url) => {
    setManagerBaseURL(url);
    setLogicals([]);
    showSnackbar(`Selected Physical Node: ${url}`, 'success');
  };

  // Step 2: List Logicals
  const handleListLogicals = async () => {
    if (!managerBaseURL) {
      showSnackbar('No Physical Node selected!', 'warning');
      return;
    }
    try {
      setLoadingLogicals(true);
      const resp = await managerRequest(managerBaseURL, 'list', {});
      setLogicals(resp);
      showSnackbar('Listed logical nodes.', 'success');
    } catch (error) {
      showSnackbar(error.message, 'error');
    } finally {
      setLoadingLogicals(false);
    }
  };

  // Step 3: Select Worker from list or manually
  const handleSelectLogical = (workerId) => {
    setSelectedWorkerId(workerId);
    showSnackbar(`Selected Worker ID: ${workerId}`, 'success');
  };

  return (
    <Box  sx={{ p: 3 }}>
      <PageTitle
        title="Node Selection"
        subtitle="Pick a physical node, list the logicals, and choose or manually enter a Worker ID."
      />
      <Stepper activeStep={activeStep} sx={{ mb: 4 }}>
        {steps.map((label) => (
          <Step key={label}>
            <StepLabel>{label}</StepLabel>
          </Step>
        ))}
      </Stepper>

      {/* Step 1: Physical Node */}
      {activeStep === 0 && (
        <Grow in>
          <Box>
            <Typography variant="h6" sx={{ mb: 2 }}>
              Step 1: Pick a Physical Node
            </Typography>
            <PhysicalNodeCards
              nodes={physical_urls}
              onSelect={handleSelectPhysical}
              selectedUrl={managerBaseURL}
            />
          </Box>
        </Grow>
      )}

      {/* Step 2: List Logicals */}
      {activeStep === 1 && (
        <Grow in>
          <Box>
            <Typography variant="h6" sx={{ mb: 2 }}>
              Step 2: List Logicals
            </Typography>
            <Button variant="contained" onClick={handleListLogicals} sx={{ mb: 2 }}>
              List Logicals
            </Button>
            {loadingLogicals && <CircularProgress size={24} sx={{ ml: 2 }} />}

            <LogicalList
              logicals={logicals}
              selectedWorkerId={selectedWorkerId}
              onSelectLogical={handleSelectLogical}
            />
          </Box>
        </Grow>
      )}

      {/* Step 3: Select Worker */}
      {activeStep === 2 && (
        <Grow in>
          <Box>
            <Typography variant="h6" sx={{ mb: 2 }}>
              Step 3: Select or Enter a Worker ID
            </Typography>
            {logicals.length > 0 ? (
              <LogicalList
                logicals={logicals}
                selectedWorkerId={selectedWorkerId}
                onSelectLogical={handleSelectLogical}
              />
            ) : (
              <Typography variant="body2" sx={{ mb: 2 }}>
                No logicals listed yet or you might skip the listing and do a manual input.
              </Typography>
            )}

            <ManualLogicalInput />
          </Box>
        </Grow>
      )}

      {/* Step Navigation */}
      <Box sx={{ mt: 4 }}>
        <Button onClick={goBack} disabled={activeStep === 0} sx={{ mr: 2 }}>
          Back
        </Button>
        <Button onClick={goNext} disabled={activeStep === steps.length - 1}>
          Next
        </Button>
      </Box>

      {/* Snackbars */}
      <Snackbar
        open={snackbarOpen}
        autoHideDuration={2500}
        onClose={handleCloseSnackbar}
      >
        <Alert onClose={handleCloseSnackbar} severity={alertSeverity} sx={{ width: '100%' }}>
          {snackbarMessage}
        </Alert>
      </Snackbar>
    </Box>
  );
}

export default NodeSelectionPage;


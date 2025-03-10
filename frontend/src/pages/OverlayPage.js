import React, { useContext, useState } from 'react';
import {
  Box,
  Typography,
  Button,
  Snackbar,
  Alert,
  Zoom,
  Card,
  CardContent,
  Grid
} from '@mui/material';
import { chordRequest } from '../api/apiClient';
import { AppContext } from '../context/AppContext';
import { shortHex } from '../utils/formatHash';
import PageTitle from '../components/PageTitle';

function OverlayPage() {
  const { managerBaseURL, selectedWorkerId } = useContext(AppContext);
  const [overlayData, setOverlayData] = useState([]);

  const [snackbarOpen, setSnackbarOpen] = useState(false);
  const [snackbarMessage, setSnackbarMessage] = useState('');
  const [alertSeverity, setAlertSeverity] = useState('info');

  const handleCloseSnackbar = () => setSnackbarOpen(false);

  const showSnackbar = (msg, severity = 'info') => {
    setSnackbarMessage(msg);
    setAlertSeverity(severity);
    setSnackbarOpen(true);
  };

  const handleGetOverlay = async () => {
    if (!managerBaseURL || selectedWorkerId == null) {
      showSnackbar('Select a manager URL and worker ID first!', 'warning');
      return;
    }
    try {
      const response = await chordRequest(managerBaseURL, selectedWorkerId, 'overlay');
      setOverlayData(response || []);
      showSnackbar('Overlay fetched successfully!', 'success');
    } catch (error) {
      showSnackbar(error.message, 'error');
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      <PageTitle
        title="Chord Ring Overlay"
        subtitle="Visualize the ring structure and key ranges"
      />
      <Typography variant="body2" sx={{ mb: 2 }}>
        Physical Node: {managerBaseURL || 'N/A'} — Worker ID: {selectedWorkerId ?? 'N/A'}
      </Typography>

      <Button variant="contained" onClick={handleGetOverlay} sx={{ mb: 3 }}>
        Show Overlay
      </Button>

      {overlayData.length === 0 ? (
        <Typography>No Overlay Data</Typography>
      ) : (
        <Grid container spacing={2}>
          {overlayData.map((node, idx) => (
            <Grid item xs={12} sm={6} md={4} lg={3} key={idx}>
              <Zoom in style={{ transitionDelay: `${idx * 100}ms` }}>
                <Card sx={{ boxShadow: 4 }}>
                  <CardContent>
                    <Typography variant="h6" gutterBottom>
                      Node URL
                    </Typography>
                    <Typography variant="body2" sx={{ mb: 1 }}>
                      {node.url}
                    </Typography>
                    <Typography variant="subtitle2">Predecessor</Typography>
                    <Typography variant="body2" sx={{ mb: 1 }}>
                      {node.predecessor_url}
                    </Typography>
                    <Typography variant="subtitle2">Successor</Typography>
                    <Typography variant="body2" sx={{ mb: 1 }}>
                      {node.successor_url}
                    </Typography>
                    <Typography variant="subtitle2">Key Range</Typography>
                    <Typography variant="body2">
                      {shortHex(node.keys_start)} - {shortHex(node.keys_end)}
                    </Typography>
                  </CardContent>
                </Card>
              </Zoom>
            </Grid>
          ))}
        </Grid>
      )}

      <Snackbar
        open={snackbarOpen}
        autoHideDuration={3000}
        onClose={handleCloseSnackbar}
      >
        <Alert
          severity={alertSeverity}
          onClose={handleCloseSnackbar}
          sx={{ width: '100%' }}
        >
          {snackbarMessage}
        </Alert>
      </Snackbar>
    </Box>
  );
}

export default OverlayPage;


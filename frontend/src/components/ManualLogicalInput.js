import React, { useContext, useState } from 'react';
import { Box, TextField, Button } from '@mui/material';
import { AppContext } from '../context/AppContext';

function ManualLogicalInput() {
  const { selectedWorkerId, setSelectedWorkerId } = useContext(AppContext);
  const [tempWorkerId, setTempWorkerId] = useState(
    selectedWorkerId !== null ? selectedWorkerId.toString() : ''
  );

  const handleSetManual = () => {
    if (tempWorkerId.trim() === '') {
      setSelectedWorkerId(null);
    } else {
      setSelectedWorkerId(parseInt(tempWorkerId, 10));
    }
  };

  return (
    <Box sx={{ mt: 3, maxWidth: 300 }}>
      <TextField
        label="Manual Worker ID"
        value={tempWorkerId}
        onChange={(e) => setTempWorkerId(e.target.value)}
        fullWidth
        sx={{ mb: 1 }}
      />
      <Button variant="outlined" onClick={handleSetManual}>
        Set Worker ID Manually
      </Button>
    </Box>
  );
}

export default ManualLogicalInput;


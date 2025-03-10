import React, { useContext } from 'react';
import { Box, Typography } from '@mui/material';
import { chordRequest } from '../api/apiClient';
import { AppContext } from '../context/AppContext';

import InsertOperation from '../components/dhtOps/InsertOperation';
import DeleteOperation from '../components/dhtOps/DeleteOperation';
import QueryOperation from '../components/dhtOps/QueryOperation';
import DepartOperation from '../components/dhtOps/DepartOperation';
import PageTitle from '../components/PageTitle';


function ChordOperationsPage() {
  const { managerBaseURL, selectedWorkerId, setSelectedWorkerId } = useContext(AppContext);

  const ensureWorkerSelected = () => {
    if (!managerBaseURL || selectedWorkerId == null) {
      throw new Error('No Physical Node / Worker Node selected!');
    }
  };

  const onInsert = async (key, value) => {
    ensureWorkerSelected();
    const resp = await chordRequest(managerBaseURL, selectedWorkerId, 'modify', {
      operation: 'insert',
      key,
      value
    });
    return resp;
  };

  const onDelete = async (key) => {
    ensureWorkerSelected();
    const resp = await chordRequest(managerBaseURL, selectedWorkerId, 'modify', {
      operation: 'delete',
      key
    });
    return resp;
  };

  const onQueryKey = async (key) => {
    ensureWorkerSelected();
    const resp = await chordRequest(managerBaseURL, selectedWorkerId, 'query', { key });
    return resp;
  };

  const onQueryAll = async () => {
    ensureWorkerSelected();
    const resp = await chordRequest(managerBaseURL, selectedWorkerId, 'query', { key: '*' });
    return resp;
  };

  const onDepart = async () => {
    ensureWorkerSelected();
    const resp = await chordRequest(managerBaseURL, selectedWorkerId, 'depart');
    setSelectedWorkerId(null);
    return resp;
  };

  return (
    <Box sx={{ p:3 }}>
      <PageTitle
        title="DHT Operations"
        subtitle="Insert, delete, query data, or depart the ring."
      />
      <Typography variant="body2" sx={{ mb: 3 }}>
        Physical Node: {managerBaseURL || 'N/A'} — Worker ID: {selectedWorkerId ?? 'N/A'}
      </Typography>

      <InsertOperation onInsert={onInsert} />
      <DeleteOperation onDelete={onDelete} />
      <QueryOperation onQueryKey={onQueryKey} onQueryAll={onQueryAll} />
      <DepartOperation onDepart={onDepart} />
    </Box>
  );
}

export default ChordOperationsPage;


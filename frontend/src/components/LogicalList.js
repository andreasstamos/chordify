import React from 'react';
import {
  Box,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  Paper,
  Typography
} from '@mui/material';
import SentimentDissatisfiedIcon from '@mui/icons-material/SentimentDissatisfied';

function LogicalList({ logicals, selectedWorkerId, onSelectLogical }) {
  if (!logicals || logicals.length === 0) {
    return (
      <Box sx={{ mt: 2 }}>
        <Paper
          elevation={3}
          sx={{
            p: 3,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: 1
          }}
        >
          <SentimentDissatisfiedIcon sx={{ fontSize: 48, color: 'text.secondary' }} />
          <Typography variant="h6" gutterBottom>
            No Logical Nodes Found
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Try spawning a new node or refresh the list.
          </Typography>
        </Paper>
      </Box>
    );
  }

  return (
    <Box sx={{ mt: 2, maxWidth: 400 }}>
      <Typography variant="subtitle2" sx={{ mb: 1 }}>
        Select a Logical Worker:
      </Typography>
      <Paper elevation={3}>
        <List>
          {logicals.map((workerId) => {
            const isSelected = workerId === selectedWorkerId;
            return (
              <ListItem key={workerId} disablePadding>
                <ListItemButton
                  onClick={() => onSelectLogical(workerId)}
                  selected={isSelected}
                >
                  <ListItemText primary={`Worker ID: ${workerId}`} />
                </ListItemButton>
              </ListItem>
            );
          })}
        </List>
      </Paper>
    </Box>
  );
}

export default LogicalList;


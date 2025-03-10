import React from 'react';
import {
  Grid,
  Card,
  CardContent,
  CardActions,
  Typography,
  Button
} from '@mui/material';

function PhysicalNodeCards({ nodes, onSelect, selectedUrl }) {
  return (
    <Grid container spacing={3}>
      {Object.entries(nodes).map(([key, url]) => {
        const isSelected = url === selectedUrl;
        return (
          <Grid item xs={12} sm={6} md={4} lg={3} key={key}>
            <Card
              sx={{
                transition: '0.3s',
                cursor: 'pointer',
                border: isSelected ? '3px solid #4caf50' : '1px solid #ccc',
                boxShadow: isSelected ? 4 : 1,
                '&:hover': {
                  transform: 'scale(1.04)',
                  boxShadow: 6
                }
              }}
            >
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  {key.toUpperCase()}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {url}
                </Typography>
              </CardContent>
              <CardActions sx={{ justifyContent: 'flex-end' }}>
                <Button
                  size="small"
                  variant={isSelected ? 'contained' : 'outlined'}
                  color={isSelected ? 'success' : 'primary'}
                  onClick={() => onSelect(url)}
                >
                  {isSelected ? 'Selected' : 'Select'}
                </Button>
              </CardActions>
            </Card>
          </Grid>
        );
      })}
    </Grid>
  );
}

export default PhysicalNodeCards;


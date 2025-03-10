import React from 'react';
import { Typography, Box, Divider } from '@mui/material';

function PageTitle({ title, subtitle }) {
  return (
    <Box sx={{ mb: 3 }}>
      <Typography variant="h4" sx={{ fontWeight: 'bold', mb: subtitle ? 1 : 2 }}>
        {title}
      </Typography>
      {subtitle && (
        <Typography variant="body1" color="text.secondary" sx={{ mb: 2 }}>
          {subtitle}
        </Typography>
      )}
      <Divider />
    </Box>
  );
}

export default PageTitle;


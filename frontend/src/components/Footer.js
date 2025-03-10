import React from 'react';
import { Box, Typography } from '@mui/material';
import CopyrightNotice from './CopyrightNotice';

function Footer() {
  return (
    <Box
      sx={{
        mt: 'auto', 
        py: 2,
        px: 2,
        textAlign: 'center',
        borderTop: '1px solid #ccc',
        backgroundColor: '#f9f9f9'
      }}
    >
      <CopyrightNotice />
    </Box>
  );
}

export default Footer;


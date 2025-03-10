import React from 'react';
import { Box } from '@mui/material';
import Navbar from './Navbar';
import Footer from './Footer';

function Layout({ children }) {
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column' }}>
      <Navbar />
      <Box component="main" sx={{ p: 2 }}>
        {children}
      </Box>
      <Footer />
    </Box>
  );
}

export default Layout;


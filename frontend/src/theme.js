import { createTheme } from '@mui/material/styles';

const theme = createTheme({
  palette: {
    primary: {
      main: '#2196f3'
    },
    secondary: {
      main: '#ef6c00'
    },
    background: {
      default: 'transparent',
    },
  },
  typography: {
    fontFamily: 'Roboto, sans-serif'
  }
});

export default theme;


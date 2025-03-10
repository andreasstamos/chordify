import { shuffle } from 'lodash';
import { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { Typography } from '@mui/material';

function CopyrightNotice() {
  let location = useLocation();
  const [names, setNames] = useState([
    'Andreas Stamos',
    'Harris Platanos',
    'Spyros Galanopoulos',
  ])
    ;

  useEffect(() => {setNames(shuffle(names))}, [location])

  return (<Typography variant="body2" color="text.secondary">
    &copy; 2025{new Date().getFullYear() !== 2025 && `-${+new Date().getFullYear()}`}   {names.join(', ')}
    </Typography>);
}

export default CopyrightNotice;


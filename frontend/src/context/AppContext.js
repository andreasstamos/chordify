import React, { createContext, useState, useMemo } from 'react';

export const AppContext = createContext();

export const AppProvider = ({ children }) => {
  const [managerBaseURL, setManagerBaseURL] = useState('');
  const [selectedWorkerId, setSelectedWorkerId] = useState(null);

  const contextValue = useMemo(
    () => ({
      managerBaseURL,
      setManagerBaseURL,
      selectedWorkerId,
      setSelectedWorkerId,
    }),
    [managerBaseURL, selectedWorkerId]
  );

  return (
    <AppContext.Provider value={contextValue}>
      {children}
    </AppContext.Provider>
  );
};


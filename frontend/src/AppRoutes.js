import React, { useContext } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';

import LoginPage from './pages/LoginPage';
import HomePage from './pages/HomePage';
import NodeSelectionPage from './pages/NodeSelectionPage';
import PhysicalManagementPage from './pages/PhysicalManagementPage';
import ChordOperationsPage from './pages/ChordOperationsPage';
import OverlayPage from './pages/OverlayPage';

import { AuthContext } from './context/AuthContext';

function RequireAuth({ children }) {
  const { isLoggedIn } = useContext(AuthContext);
  if (!isLoggedIn) {
    return <Navigate to="/login" replace />;
  }
  return children;
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      <Route path="/" element={<RequireAuth> <HomePage /> </RequireAuth>} />
      <Route path="/node-selection" element={<RequireAuth> <NodeSelectionPage /> </RequireAuth>}/>
      <Route path="/physical-management" element={<RequireAuth> <PhysicalManagementPage /> </RequireAuth>}/>
      <Route path="/chord-operations" element={<RequireAuth> <ChordOperationsPage /> </RequireAuth>}/>
      <Route path="/overlay" element={<RequireAuth> <OverlayPage /> </RequireAuth>}/>
    </Routes>
  );
}

export default AppRoutes;


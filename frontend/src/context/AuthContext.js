import React, { createContext, useState, useEffect } from 'react';
import axios from 'axios';
import { auth_check_url } from '../config/Config';

export const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [credentials, setCredentials] = useState({ username: '', password: '' });
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  useEffect(() => {
    if (isLoggedIn) {
      axios.defaults.auth = {
        username: credentials.username,
        password: credentials.password
      };
    } else {
      axios.defaults.auth = null;
    }
  }, [credentials, isLoggedIn]);

  const login = (username, password) => {
    setCredentials({ username, password });
    setIsLoggedIn(true);
  };

  const logout = () => {
    setCredentials({ username: '', password: '' });
    setIsLoggedIn(false);
  };

  const checkCredentials = async (username, password) => {
    try {
      const resp = await axios.get(auth_check_url, {auth: { username, password },
        validateStatus: (status) => {return status < 500;}}
      );
      return resp.status === 404;
    } catch (error) {
      if (error.response && error.response.status === 401) {
        return false;
      }
      return false;
    }
  };

  return (
    <AuthContext.Provider
      value={{
        isLoggedIn,
        username: credentials.username,
        password: credentials.password,
        login,
        logout,
        checkCredentials
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};


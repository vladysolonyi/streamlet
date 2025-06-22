import React, { createContext, useContext, useState, useEffect } from "react";

const ServerStatusContext = createContext();

export const ServerStatusProvider = ({ children, checkInterval = 5000 }) => {
  const [serverOnline, setServerOnline] = useState(false);
  const [loading, setLoading] = useState(true);

  const checkServerStatus = async () => {
    try {
      const response = await fetch("http://localhost:8000/health", {
        method: "GET",
        headers: { "X-API-Key": "SECRET_KEY" },
      });

      if (response.ok) {
        setServerOnline(true);
      } else {
        setServerOnline(false);
      }
    } catch (error) {
      setServerOnline(false);
    } finally {
      if (loading) setLoading(false);
    }
  };

  useEffect(() => {
    // Initial check
    checkServerStatus();

    // Setup periodic checks
    const intervalId = setInterval(checkServerStatus, checkInterval);

    return () => clearInterval(intervalId);
  }, []);

  return (
    <ServerStatusContext.Provider value={{ serverOnline, loading }}>
      {children}
    </ServerStatusContext.Provider>
  );
};

export const useServerStatus = () => useContext(ServerStatusContext);

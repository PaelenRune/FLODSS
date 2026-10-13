import { useState, useEffect, useCallback } from 'react';
import { SystemStatus } from '../types/api';
import { fetchSystemHealth } from '../services/api';

export function useHealthCheck(pollIntervalMs: number = 10000) {
  const [data, setData] = useState<SystemStatus | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const checkHealth = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const status = await fetchSystemHealth();
      setData(status);
    } catch (err: any) {
      setError(err?.message || 'Failed to connect to backend API server');
      setData(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, pollIntervalMs);
    return () => clearInterval(interval);
  }, [checkHealth, pollIntervalMs]);

  return { data, loading, error, refresh: checkHealth };
}

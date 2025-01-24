import { useState, useEffect } from 'react';
import { BatterySettings, ElectricitySettings } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080';

export function useSettings() {
  const [batterySettings, setBatterySettings] = useState<BatterySettings | null>(null);
  const [electricitySettings, setElectricitySettings] = useState<ElectricitySettings | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadSettings() {
      try {
        const [batteryRes, electricityRes] = await Promise.all([
          fetch(`${API_BASE_URL}/api/settings/battery`),
          fetch(`${API_BASE_URL}/api/settings/electricity`)
        ]);

        if (!batteryRes.ok || !electricityRes.ok) {
          throw new Error('Failed to fetch settings');
        }

        const batteryData = await batteryRes.json();
        const electricityData = await electricityRes.json();

        setBatterySettings(batteryData);
        setElectricitySettings(electricityData);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load settings');
      } finally {
        setIsLoading(false);
      }
    }

    loadSettings();
  }, []);

  const updateBatterySettings = async (settings: BatterySettings) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/settings/battery`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings)
      });
  
      if (!response.ok) {
        throw new Error('Failed to update battery settings');
      }
  
      setBatterySettings(settings);
  
      // Fetch new schedule after settings update
      const scheduleResponse = await fetch(`${API_BASE_URL}/api/schedule`);
      if (!scheduleResponse.ok) {
        throw new Error('Failed to fetch schedule');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update battery settings');
    }
  };
  
  const updateElectricitySettings = async (settings: ElectricitySettings) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/settings/electricity`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings)
      });
  
      if (!response.ok) {
        throw new Error('Failed to update electricity settings');
      }
  
      setElectricitySettings(settings);
  
      // Fetch new schedule after settings update
      const scheduleResponse = await fetch(`${API_BASE_URL}/api/schedule`);
      if (!scheduleResponse.ok) {
        throw new Error('Failed to fetch schedule');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update electricity settings');
    }
  };

  return {
    batterySettings,
    electricitySettings,
    updateBatterySettings,
    updateElectricitySettings,
    isLoading,
    error
  };
}
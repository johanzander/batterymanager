import { useState, useEffect, useCallback } from 'react';
import { SummaryCards } from '../components/SummaryCards';
import { BatteryLevelChart } from '../components/BatteryLevelChart';
import { BatteryActionsChart } from '../components/BatteryActionsChart';
import { BatteryScheduleTable } from '../components/BatteryScheduleTable';
import { BatterySettings } from '../components/BatterySettings';
import { ScheduleData } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080';

interface DashboardProps {
  selectedDate: Date;
  onLoadingChange: (loading: boolean) => void;
  settings: BatterySettings;
}

export default function OptimizationDashboard({ 
  selectedDate, 
  onLoadingChange,
  settings 
}: DashboardProps) {
  const [data, setData] = useState<ScheduleData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [noDataAvailable, setNoDataAvailable] = useState(false);

  const fetchScheduleData = useCallback(async () => {
    try {
      onLoadingChange(true);
      setNoDataAvailable(false);
      setError(null);
      
      const queryParams = new URLSearchParams({
        estimated_consumption: settings.estimatedConsumption.toString(),
        max_charging_power_rate: settings.maxChargingPowerRate.toString(),
        total_capacity: settings.totalCapacity.toString(),
        reserved_capacity: settings.reservedCapacity.toString(),
        date: selectedDate.toISOString().split('T')[0],
      });

      const response = await fetch(`${API_BASE_URL}/api/battery/schedule-data?${queryParams}`);
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(errorData.detail || 'Failed to fetch data');
      }
      
      const scheduleData: ScheduleData = await response.json();
      
      if (!scheduleData.hourlyData || scheduleData.hourlyData.length === 0) {
        setNoDataAvailable(true);
        return;
      }

      const totalGridCosts = scheduleData.hourlyData.reduce((sum, h) => sum + h.gridCost, 0);
      const totalBatteryCosts = scheduleData.hourlyData.reduce((sum, h) => sum + h.batteryCost, 0);

      const updatedData = {
        ...scheduleData,
        summary: {
          ...scheduleData.summary,
          gridCosts: totalGridCosts,
          batteryCosts: totalBatteryCosts
        }
      };

      setData(updatedData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error occurred');
    } finally {
      onLoadingChange(false);
    }
  }, [settings, selectedDate, onLoadingChange]);

  useEffect(() => {
    fetchScheduleData();
  }, [fetchScheduleData]);

  // Shared empty components with disabled state
  const emptyComponents = (message: string) => (
    <div className="p-6 space-y-8 bg-gray-50 relative">
      <div className="opacity-50 pointer-events-none">
        <SummaryCards summary={{
          baseCost: 0,
          optimizedCost: 0,
          savings: 0,
          cycleCount: 0,
          gridCosts: 0,
          batteryCosts: 0
        }} hourlyData={[]} />
        <BatteryLevelChart hourlyData={[]} settings={settings} />
        <BatteryActionsChart hourlyData={[]} />
        <BatteryScheduleTable 
          hourlyData={[]} 
          settings={settings}
          summary={{
            baseCost: 0,
            optimizedCost: 0,
            savings: 0,
            cycleCount: 0,
            gridCosts: 0,
            batteryCosts: 0
          }}
        />
      </div>
      <div className="absolute inset-0 flex items-center justify-center">
        <div className={`bg-white p-4 rounded-lg shadow-lg ${error ? 'border-red-500 border-2' : ''}`}>
          <p className={`text-lg font-medium ${error ? 'text-red-600' : 'text-gray-600'}`}>
            {message}
          </p>
        </div>
      </div>
    </div>
  );

  if (!data || error || noDataAvailable) {
    let message = 'Loading schedule data...';
    
    if (error) {
      message = `Error: ${error}`;
    } else if (noDataAvailable) {
      message = `No price data available for ${selectedDate.toLocaleDateString('sv-SE', { 
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
      })}`;
    }

    return emptyComponents(message);
  }

  return (
    <div className="p-6 space-y-8 bg-gray-50">
      <SummaryCards summary={data.summary} hourlyData={data.hourlyData} />
      <BatteryLevelChart hourlyData={data.hourlyData} settings={settings} />
      <BatteryActionsChart hourlyData={data.hourlyData} />
      <BatteryScheduleTable 
        hourlyData={data.hourlyData} 
        settings={settings}
        summary={data.summary}
      />
    </div>
  );
}
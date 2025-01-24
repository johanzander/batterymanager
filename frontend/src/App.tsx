import { useState, useMemo } from 'react';
import OptimizationDashboard from './pages/OptimizationDashboard';
import DateSelector from './components/DateSelector';
import { CombinedSettings } from './components/Settings';
import { useSettings } from './hooks/useSettings';

function App() {
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [isLoading, setIsLoading] = useState(false);
  const { 
    batterySettings, 
    electricitySettings, 
    updateBatterySettings,
    updateElectricitySettings,
    isLoading: settingsLoading,
    error: settingsError 
  } = useSettings();

  const handleDateChange = (date: Date) => {
    setSelectedDate(date);
  };

  const combinedSettings = useMemo(() => ({
    ...batterySettings,
    ...electricitySettings,
  }), [batterySettings, electricitySettings]);

  if (settingsLoading) {
    return <div>Loading settings...</div>;
  }

  if (settingsError) {
    return <div>Error loading settings: {settingsError}</div>;
  }

  if (!batterySettings || !electricitySettings) {
    return <div>No settings available</div>;
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow fixed top-0 left-0 w-full z-10">
        <div className="max-w-7xl mx-auto py-3 px-4">
          <div className="flex justify-between items-center">
            <div className="flex items-center space-x-4">
              <CombinedSettings
                batterySettings={batterySettings}
                electricitySettings={electricitySettings}
                onBatteryUpdate={updateBatterySettings}
                onElectricityUpdate={updateElectricitySettings}
              />
              <h1 className="text-2xl font-bold text-gray-900">Smart Charger</h1>
              <span className="italic text-gray-600">
                Turn electricity price differences into savings with your home battery
              </span>
            </div>
            <DateSelector
              selectedDate={selectedDate}
              onDateChange={handleDateChange}
              isLoading={isLoading}
            />
          </div>
        </div>
      </header>
      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8 mt-20">
        <OptimizationDashboard 
          selectedDate={selectedDate} 
          onLoadingChange={setIsLoading}
          settings={combinedSettings}
        />
      </main>
    </div>
  );
}

export default App;
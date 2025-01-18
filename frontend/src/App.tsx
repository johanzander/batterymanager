import { useState } from 'react';
import OptimizationDashboard from './pages/OptimizationDashboard';
import DateSelector from './components/DateSelector';
import BatterySettings, { BatterySettings as BatterySettingsType } from './components/BatterySettings';

const defaultSettings: BatterySettingsType = {
  totalCapacity: 30.0,
  reservedCapacity: 3.0,
  estimatedConsumption: 4.5,
  maxChargingPowerRate: 100,
};

function App() {
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [isLoading, setIsLoading] = useState(false);
  const [settings, setSettings] = useState<BatterySettingsType>(defaultSettings);

  const handleDateChange = (date: Date) => {
    setSelectedDate(date);
  };

  const handleSettingsUpdate = (newSettings: BatterySettingsType) => {
    console.log('App: Updating settings to:', newSettings);
    setSettings(newSettings);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow fixed top-0 left-0 w-full z-10">
        <div className="max-w-7xl mx-auto py-3 px-4">
          <div className="flex justify-between items-center">
            <div className="flex items-center space-x-4">
              <BatterySettings 
                settings={settings} 
                onUpdate={handleSettingsUpdate}
              />
              <h1 className="text-2xl font-bold text-gray-900">Smart Charger</h1>
              <span className="italic text-gray-600">Turn electricity price differences into savings with your home battery</span>
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
          settings={settings}
        />
      </main>
    </div>
  );
}

export default App;
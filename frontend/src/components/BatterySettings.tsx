// BatterySettings.tsx
import { useState } from 'react';

interface BatterySettings {
  estimatedConsumption: number;
  maxChargingPowerRate: number;
}

export default function BatterySettings({ 
  settings, 
  onUpdate 
}: { 
  settings: BatterySettings;
  onUpdate: (newSettings: BatterySettings) => void;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [formValues, setFormValues] = useState(settings);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onUpdate(formValues);
    setIsOpen(false);
  };

  return (
    <>
      {/* Settings Button */}
      <button
        onClick={() => setIsOpen(true)}
        className="fixed top-4 right-4 p-2 rounded-full bg-white shadow-lg hover:bg-gray-50"
      >
        <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
      </button>

      {/* Slide-out Panel */}
      <div className={`fixed inset-y-0 right-0 w-80 bg-white shadow-xl transform transition-transform duration-300 ease-in-out z-50 ${isOpen ? 'translate-x-0' : 'translate-x-full'}`}>
        <div className="p-4">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-semibold">Battery Settings</h2>
            <button onClick={() => setIsOpen(false)} className="text-gray-500 hover:text-gray-700">
              <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Estimated Consumption (kW/h)
              </label>
              <input
                type="number"
                value={formValues.estimatedConsumption}
                onChange={(e) => setFormValues({
                  ...formValues,
                  estimatedConsumption: parseFloat(e.target.value)
                })}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                step="0.1"
                min="0"
                max="15"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Max Charging Power Rate (%)
              </label>
              <input
                type="number"
                value={formValues.maxChargingPowerRate}
                onChange={(e) => setFormValues({
                  ...formValues,
                  maxChargingPowerRate: parseFloat(e.target.value)
                })}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                step="5"
                min="0"
                max="100"
              />
            </div>
            <button
              type="submit"
              className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 z-50"
            >
              Apply Settings
            </button>
          </form>
        </div>
      </div>
    </>
  );
}

export type { BatterySettings };
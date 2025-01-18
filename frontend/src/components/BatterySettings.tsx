import React, { useState, useEffect } from 'react';
import { Calendar, ChevronLeft, ChevronRight } from 'lucide-react';

import Cookies from 'js-cookie';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080';

export interface BatterySettings {
  totalCapacity: number;
  reservedCapacity: number;
  estimatedConsumption: number;
  maxChargingPowerRate: number;
}

const defaultSettings: BatterySettings = {
  totalCapacity: 30.0,
  reservedCapacity: 3.0,
  estimatedConsumption: 4.5,
  maxChargingPowerRate: 100,
};

export default function BatterySettings({ 
  settings = defaultSettings,
  onUpdate 
}: { 
  settings: BatterySettings;
  onUpdate: (settings: BatterySettings) => void;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [formValues, setFormValues] = useState<BatterySettings>(settings);

  // Update form values when settings prop changes
  useEffect(() => {
    setFormValues(settings);
  }, [settings]);

  // Load settings from API on mount
  useEffect(() => {
    const loadSettings = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/battery/settings`);
        if (!response.ok) throw new Error('Failed to fetch settings');
        const data = await response.json();
        
        const newSettings: BatterySettings = {
          totalCapacity: data.totalCapacity ?? settings.totalCapacity,
          reservedCapacity: data.reservedCapacity ?? settings.reservedCapacity,
          estimatedConsumption: data.estimatedConsumption ?? settings.estimatedConsumption,
          maxChargingPowerRate: data.maxChargingPowerRate ?? settings.maxChargingPowerRate,
        };
        
        onUpdate(newSettings);
        Cookies.set('batterySettings', JSON.stringify(newSettings), { expires: 365 });
      } catch (error) {
        console.error('Error fetching settings:', error);
        const savedSettings = Cookies.get('batterySettings');
        if (savedSettings) {
          try {
            const parsedSettings = JSON.parse(savedSettings);
            onUpdate(parsedSettings);
          } catch (parseError) {
            console.error('Error parsing saved settings:', parseError);
            // If there's an error parsing saved settings, use the default ones
            onUpdate(settings);
          }
        }
      }
    };

    loadSettings();
  }, []);  // Only run on mount

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Update parent component immediately
    onUpdate(formValues);
    setIsOpen(false);

    // Save to cookies
    Cookies.set('batterySettings', JSON.stringify(formValues), { expires: 365 });

    // Update API
    try {
      const response = await fetch(`${API_BASE_URL}/api/battery/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formValues),
      });
      
      if (!response.ok) {
        throw new Error('Failed to update settings');
      }
    } catch (error) {
      console.error('Error updating settings:', error);
    }
  };
  
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    const newValues = {
      ...formValues,
      [name]: Number(value)
    };
    setFormValues(newValues);
  };

  return (
    <>
      {/* Settings Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="p-2 rounded-full hover:bg-gray-100"
      >
        <svg 
          xmlns="http://www.w3.org/2000/svg" 
          className="h-6 w-6 text-gray-600" 
          fill="none" 
          viewBox="0 0 24 24" 
          stroke="currentColor"
        >
          <path 
            strokeLinecap="round" 
            strokeLinejoin="round" 
            strokeWidth={2} 
            d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" 
          />
          <path 
            strokeLinecap="round" 
            strokeLinejoin="round" 
            strokeWidth={2} 
            d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" 
          />
        </svg>
      </button>

      {/* Slide-out Panel */}
      <div 
        className={`fixed inset-y-0 left-0 w-80 bg-white shadow-xl transform transition-transform duration-300 ease-in-out z-50 ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="h-full flex flex-col p-4">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-semibold">Battery Settings</h2>
            <button 
              onClick={() => setIsOpen(false)} 
              className="text-gray-500 hover:text-gray-700"
            >
              <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Total Capacity (kWh)
              </label>
              <input
                type="number"
                name="totalCapacity"
                value={formValues.totalCapacity}
                onChange={handleChange}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                step="0.1"
                min="0"
                max="100"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Reserved Capacity (kWh)
              </label>
              <input
                type="number"
                name="reservedCapacity"
                value={formValues.reservedCapacity}
                onChange={handleChange}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                step="0.1"
                min="0"
                max="100"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Estimated Consumption (kW/h)
              </label>
              <input
                type="number"
                name="estimatedConsumption"
                value={formValues.estimatedConsumption}
                onChange={handleChange}
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
                name="maxChargingPowerRate"
                value={formValues.maxChargingPowerRate}
                onChange={handleChange}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                step="5"
                min="0"
                max="100"
              />
            </div>
            <button
              type="submit"
              className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
            >
              Apply Settings
            </button>
          </form>
        </div>
      </div>
    </>
  );
}
import { useState, useEffect, useCallback } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  BarChart, Bar, ReferenceLine, ResponsiveContainer, Cell
} from 'recharts';
import BatterySettings from './BatterySettings';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080';

interface HourlyData {
  hour: string;
  price: number;
  batteryLevel: number;
  action: number;
  gridCost: number;
  batteryCost: number;
  totalCost: number;
  baseCost: number;
  savings: number;
}

interface ScheduleSummary {
  baseCost: number;
  optimizedCost: number;
  savings: number;
  cycleCount: number;
}

interface ScheduleData {
  hourlyData: HourlyData[];
  summary: ScheduleSummary;
}

export default function PricePriorityDashboard() {
  const [data, setData] = useState<ScheduleData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [settings, setSettings] = useState({
    estimatedConsumption: 4.5,
    maxChargingPowerRate: 100,
  });

  const fetchScheduleData = useCallback(async () => {
    try {
      setLoading(true);
      const queryParams = new URLSearchParams({
        estimated_consumption: settings.estimatedConsumption.toString(),
        max_charging_power_rate: settings.maxChargingPowerRate.toString(),
      });

      const response = await fetch(`${API_BASE_URL}/api/battery/schedule-data?${queryParams}`);
      if (!response.ok) throw new Error('Failed to fetch data');
      const scheduleData = await response.json();
      setData(scheduleData);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error occurred');
    } finally {
      setLoading(false);
    }
  }, [settings]);

  useEffect(() => {
    fetchScheduleData();
  }, [fetchScheduleData]);

  const handleSettingsUpdate = (newSettings: typeof settings) => {
    setSettings(newSettings);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-4 text-red-500">
        Error: {error || 'No data available'}
      </div>
    );
  }

  const { summary, hourlyData } = data;

  return (
    <div className="p-6 space-y-8 bg-gray-50">
      <BatterySettings 
        settings={settings} 
        onUpdate={handleSettingsUpdate} 
      />
      
      {/* Cost Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-medium text-gray-900 mb-2">Base Cost</h3>
          <p className="text-3xl font-bold text-gray-600">{summary.baseCost.toFixed(2)} SEK</p>
          <p className="text-sm text-gray-500 mt-2">Without optimization</p>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-medium text-gray-900 mb-2">Optimized Cost</h3>
          <p className="text-3xl font-bold text-green-600">{summary.optimizedCost.toFixed(2)} SEK</p>
          <p className="text-sm text-gray-500 mt-2">With battery storage</p>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-medium text-gray-900 mb-2">Total Savings</h3>
          <p className="text-3xl font-bold text-purple-600">{summary.savings.toFixed(2)} SEK</p>
          <p className="text-sm text-gray-500 mt-2">{((summary.savings / summary.baseCost) * 100).toFixed(1)}% reduction</p>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-medium text-gray-900 mb-2">Battery Cycles</h3>
          <p className="text-3xl font-bold text-blue-600">{summary.cycleCount.toFixed(1)}</p>
          <p className="text-sm text-gray-500 mt-2">Discharge events</p>
        </div>
      </div>

      {/* Price and Battery Level Chart */}
      <div className="bg-white p-6 rounded-lg shadow">
        <h2 className="text-xl font-semibold mb-4">Price and Battery Level</h2>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={hourlyData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="hour" interval={2} />
              <YAxis yAxisId="left" domain={[0, 35]} />
              <YAxis yAxisId="right" orientation="right" domain={[0, 4]} />
              <Tooltip />
              <Legend />
              <ReferenceLine yAxisId="left" y={3} stroke="#ef4444" strokeDasharray="3 3" label="Min Level" />
              <ReferenceLine yAxisId="left" y={30} stroke="#ef4444" strokeDasharray="3 3" label="Max Level" />
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="price"
                stroke="#2563eb"
                name="Price (SEK/kWh)"
                strokeWidth={2}
              />
              <Line
                yAxisId="left"
                type="monotone"
                dataKey="batteryLevel"
                stroke="#16a34a"
                name="Battery Level (kWh)"
                strokeWidth={2}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Battery Actions Chart */}
      <div className="bg-white p-6 rounded-lg shadow">
        <h2 className="text-xl font-semibold mb-4">Battery Actions</h2>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={hourlyData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="hour" interval={2} />
              <YAxis domain={[-7, 7]} />
              <Tooltip />
              <Legend />
              <ReferenceLine y={0} stroke="#666666" />
              <ReferenceLine y={6} stroke="#ef4444" strokeDasharray="3 3" label="Max Charge" />
              <ReferenceLine y={-6} stroke="#ef4444" strokeDasharray="3 3" label="Max Discharge" />
              <Bar dataKey="action" name="Charge/Discharge (kWh)">
                {hourlyData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.action >= 0 ? '#16a34a' : '#dc2626'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Detailed Hourly Data Table */}
      <div className="bg-white p-6 rounded-lg shadow overflow-x-auto">
        <h2 className="text-xl font-semibold mb-4">Battery Schedule</h2>
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border">
                Hour
              </th>
              <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border">
                Price (SEK/kWh)
              </th>
              <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border">
                Base Cost (SEK)
              </th>
              <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border">
                Battery Level (kWh)
              </th>
              <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border">
                Action (kWh)
              </th>
              <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border">
                Grid Cost (SEK)
              </th>
              <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border">
                Battery Cost (SEK)
              </th>
              <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border">
                Total Cost (SEK)
              </th>
              <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border">
                Savings (SEK)
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {hourlyData.map((hour, index) => (
              <tr key={index} className={index % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-900 border">
                  {hour.hour}
                </td>
                <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-900 border">
                  {hour.price.toFixed(3)}
                </td>
                <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-900 border">
                  {hour.baseCost.toFixed(2)}
                </td>
                <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-900 border">
                  {hour.batteryLevel.toFixed(1)}
                </td>
                <td className="px-3 py-2 whitespace-nowrap border">
                  <span className={`px-2 inline-flex text-sm leading-5 font-semibold rounded-full ${
                    hour.action > 0
                      ? 'bg-green-100 text-green-800'
                      : hour.action < 0
                      ? 'bg-red-100 text-red-800'
                      : 'bg-gray-100 text-gray-800'
                  }`}>
                    {hour.action.toFixed(1)}
                  </span>
                </td>
                <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-900 border">
                  {hour.gridCost.toFixed(2)}
                </td>
                <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-900 border">
                  {hour.batteryCost.toFixed(2)}
                </td>
                <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-900 border">
                  {hour.totalCost.toFixed(2)}
                </td>
                <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-900 border">
                  {hour.savings.toFixed(2)}
                </td>
              </tr>
            ))}

            {/* Totals Row */}
            <tr className="bg-gray-100 font-semibold">
              <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-900 border">
                TOTAL
              </td>
              <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-900 border">
                {/* Average price */}
                {(hourlyData.reduce((sum, h) => sum + h.price, 0) / hourlyData.length).toFixed(3)}
              </td>
              <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-900 border">
                {summary.baseCost.toFixed(2)}
              </td>
              <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-900 border">
                {/* Average battery level */}
              </td>
              <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-900 border">
                C: {hourlyData.reduce((sum, h) => sum + (h.action > 0 ? h.action : 0), 0).toFixed(1)}
                <br />
                D: {Math.abs(hourlyData.reduce((sum, h) => sum + (h.action < 0 ? h.action : 0), 0)).toFixed(1)}
              </td>
              <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-900 border">
                {hourlyData.reduce((sum, h) => sum + h.gridCost, 0).toFixed(2)}
              </td>
              <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-900 border">
                {hourlyData.reduce((sum, h) => sum + h.batteryCost, 0).toFixed(2)}
              </td>
              <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-900 border">
                {summary.optimizedCost.toFixed(2)}
              </td>
              <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-900 border">
                {summary.savings.toFixed(2)}
              </td>
            </tr>

          </tbody>
        </table>
      </div>
    </div>
  );
}
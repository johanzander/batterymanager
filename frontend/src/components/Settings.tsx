import React, { useState } from 'react';
import { Settings2, X } from 'lucide-react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { Label } from "../components/ui/label";
import { Input } from "../components/ui/input";
import { Switch } from "../components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { Button } from "../components/ui/button";

type AreaCode = 'SE1' | 'SE2' | 'SE3' | 'SE4';

interface BatterySettings {
  totalCapacity: number;
  reservedCapacity: number;
  estimatedConsumption: number;
  maxChargeDischarge: number;
  chargeCycleCost: number;
  chargingPowerRate: number;
}

interface ElectricitySettings {
  useActualPrice: boolean;
  area: AreaCode;
  markupRate: number;
  vatMultiplier: number;
  additionalCosts: number;
  taxReduction: number;
}

interface CombinedSettingsProps {
  batterySettings: BatterySettings;
  electricitySettings: ElectricitySettings;
  onBatteryUpdate: (settings: BatterySettings) => void;
  onElectricityUpdate: (settings: ElectricitySettings) => void;
}

export function CombinedSettings({ 
  batterySettings,
  electricitySettings,
  onBatteryUpdate,
  onElectricityUpdate
}: CombinedSettingsProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});
  
  const [localBatteryValues, setLocalBatteryValues] = useState(() => ({
    totalCapacity: batterySettings.totalCapacity.toString(),
    reservedCapacity: batterySettings.reservedCapacity.toString(),
    estimatedConsumption: batterySettings.estimatedConsumption.toString(),
    maxChargeDischarge: batterySettings.maxChargeDischarge.toString(),
    chargeCycleCost: batterySettings.chargeCycleCost.toString(),
    chargingPowerRate: batterySettings.chargingPowerRate.toString(),
  }));

  const [localElectricityValues, setLocalElectricityValues] = useState(() => ({
    markupRate: electricitySettings.markupRate.toString(),
    vatMultiplier: electricitySettings.vatMultiplier.toString(),
    additionalCosts: electricitySettings.additionalCosts.toString(),
    taxReduction: electricitySettings.taxReduction.toString()
  }));

  const validateInput = (field: string, value: number) => {
    const errors: Record<string, string> = {};
    
    // Battery validations
    if (['totalCapacity', 'reservedCapacity', 'estimatedConsumption', 
         'maxChargeDischarge', 'chargeCycleCost', 'chargingPowerRate'].includes(field)) {
      switch (field) {
        case 'totalCapacity':
          if (value < batterySettings.reservedCapacity) {
            errors[field] = `Cannot be less than reserved capacity (${batterySettings.reservedCapacity} kWh)`;
          }
          break;
        case 'reservedCapacity':
          if (value > batterySettings.totalCapacity) {
            errors[field] = `Cannot exceed total capacity (${batterySettings.totalCapacity} kWh)`;
          }
          break;
        case 'estimatedConsumption':
          if (value < 0 || value > 15) {
            errors[field] = 'Must be between 0 and 15 kWh';
          }
          break;
        case 'chargingPowerRate':
          if (value < 0 || value > 100) {
            errors[field] = 'Must be between 0 and 100';
          }
          break;
        default:
          if (value < 0) {
            errors[field] = 'Must be greater than 0';
          }
      }
    }
    
    // Electricity validations
    if (['markupRate', 'additionalCosts', 'taxReduction'].includes(field)) {
      if (value < 0) {
        errors[field] = 'Must be greater than or equal to 0';
      }
    }
    
    if (field === 'vatMultiplier' && value < 1) {
      errors[field] = 'Must be greater than or equal to 1';
    }
    
    setValidationErrors(prev => ({ ...prev, ...errors }));
    return Object.keys(errors).length === 0;
  };

  const handleInputChange = (
    e: React.ChangeEvent<HTMLInputElement>, 
    field: string, 
    setLocalValues: React.Dispatch<React.SetStateAction<any>>
  ) => {
    const newValue = e.target.value.replace(',', '.');
    setLocalValues(prev => ({ ...prev, [field]: newValue }));
    setValidationErrors(prev => ({ ...prev, [field]: '' }));
  };

  const handleInputBlur = (
    field: string, 
    localValues: any,
    settings: any,
    onUpdate: (settings: any) => void,
    setLocalValues: React.Dispatch<React.SetStateAction<any>>
  ) => {
    const value = localValues[field];
    const parsed = parseFloat(value.replace(',', '.'));
    
    if (isNaN(parsed)) {
      setValidationErrors(prev => ({ 
        ...prev, 
        [field]: 'Please enter a valid number' 
      }));
      return;
    }

    if (!validateInput(field, parsed)) {
      return;
    }

    setLocalValues(prev => ({
      ...prev,
      [field]: parsed.toString()
    }));
    
    onUpdate({
      ...settings,
      [field]: parsed
    });
  };

  return (
    <>
      <Button
        variant="ghost"
        size="icon"
        onClick={() => setIsOpen(true)}
        className="hover:bg-gray-100 rounded-full"
      >
        <Settings2 className="h-5 w-5" />
      </Button>

      {isOpen && (
        <div className="fixed inset-0 z-50 bg-black/50">
          <div className="fixed inset-y-0 left-0 w-96 bg-white shadow-lg p-6 animate-in slide-in-from-left">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-xl font-semibold">Settings</h2>
              <Button variant="ghost" size="icon" onClick={() => setIsOpen(false)}>
                <X className="h-5 w-5" />
              </Button>
            </div>

            <Tabs defaultValue="battery" className="space-y-4">
              <TabsList className="w-full">
                <TabsTrigger value="battery" className="flex-1">Battery</TabsTrigger>
                <TabsTrigger value="electricity" className="flex-1">Electricity</TabsTrigger>
              </TabsList>

              <TabsContent value="battery" className="space-y-4">
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label>Total Capacity (kWh)</Label>
                    <Input
                      type="text"
                      value={localBatteryValues.totalCapacity}
                      onChange={(e) => handleInputChange(e, 'totalCapacity', setLocalBatteryValues)}
                      onBlur={() => handleInputBlur('totalCapacity', localBatteryValues, batterySettings, onBatteryUpdate, setLocalBatteryValues)}
                    />
                    {validationErrors.totalCapacity && (
                      <span className="text-sm text-red-500">{validationErrors.totalCapacity}</span>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label>Reserved Capacity (kWh)</Label>
                    <Input
                      type="text"
                      value={localBatteryValues.reservedCapacity}
                      onChange={(e) => handleInputChange(e, 'reservedCapacity', setLocalBatteryValues)}
                      onBlur={() => handleInputBlur('reservedCapacity', localBatteryValues, batterySettings, onBatteryUpdate, setLocalBatteryValues)}
                    />
                    {validationErrors.reservedCapacity && (
                      <span className="text-sm text-red-500">{validationErrors.reservedCapacity}</span>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label>Estimated Consumption (kWh)</Label>
                    <Input
                      type="text"
                      value={localBatteryValues.estimatedConsumption}
                      onChange={(e) => handleInputChange(e, 'estimatedConsumption', setLocalBatteryValues)}
                      onBlur={() => handleInputBlur('estimatedConsumption', localBatteryValues, batterySettings, onBatteryUpdate, setLocalBatteryValues)}
                    />
                    {validationErrors.estimatedConsumption && (
                      <span className="text-sm text-red-500">{validationErrors.estimatedConsumption}</span>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label>Max Charge/Discharge (kW)</Label>
                    <Input
                      type="text"
                      value={localBatteryValues.maxChargeDischarge}
                      onChange={(e) => handleInputChange(e, 'maxChargeDischarge', setLocalBatteryValues)}
                      onBlur={() => handleInputBlur('maxChargeDischarge', localBatteryValues, batterySettings, onBatteryUpdate, setLocalBatteryValues)}
                    />
                    {validationErrors.maxChargeDischarge && (
                      <span className="text-sm text-red-500">{validationErrors.maxChargeDischarge}</span>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label>Charge Cycle Cost (SEK)</Label>
                    <Input
                      type="text"
                      value={localBatteryValues.chargeCycleCost}
                      onChange={(e) => handleInputChange(e, 'chargeCycleCost', setLocalBatteryValues)}
                      onBlur={() => handleInputBlur('chargeCycleCost', localBatteryValues, batterySettings, onBatteryUpdate, setLocalBatteryValues)}
                    />
                    {validationErrors.chargeCycleCost && (
                      <span className="text-sm text-red-500">{validationErrors.chargeCycleCost}</span>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label>Charging Power Rate (%)</Label>
                    <Input
                      type="text"
                      value={localBatteryValues.chargingPowerRate}
                      onChange={(e) => handleInputChange(e, 'chargingPowerRate', setLocalBatteryValues)}
                      onBlur={() => handleInputBlur('chargingPowerRate', localBatteryValues, batterySettings, onBatteryUpdate, setLocalBatteryValues)}
                    />
                    {validationErrors.chargingPowerRate && (
                      <span className="text-sm text-red-500">{validationErrors.chargingPowerRate}</span>
                    )}
                  </div>
                </div>
              </TabsContent>

              <TabsContent value="electricity" className="space-y-4">
                <div className="space-y-4">
                  <div className="flex items-center space-x-2 py-2">
                    <Switch
                      checked={electricitySettings.useActualPrice}
                      onCheckedChange={(checked) => 
                        onElectricityUpdate({...electricitySettings, useActualPrice: checked})}
                    />
                    <Label>Use Actual Electricity Price</Label>
                  </div>

                  <div className="space-y-2">
                    <Label>Area</Label>
                    <Select 
                      value={electricitySettings.area}
                      onValueChange={(value: AreaCode) => 
                        onElectricityUpdate({...electricitySettings, area: value})}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select area" />
                      </SelectTrigger>
                      <SelectContent>
                        {['SE1', 'SE2', 'SE3', 'SE4'].map((area) => (
                          <SelectItem key={area} value={area}>{area}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label>Markup Rate (SEK/kWh)</Label>
                    <Input
                      type="text"
                      value={localElectricityValues.markupRate}
                      onChange={(e) => handleInputChange(e, 'markupRate', setLocalElectricityValues)}
                      onBlur={() => handleInputBlur('markupRate', localElectricityValues, electricitySettings, onElectricityUpdate, setLocalElectricityValues)}
                      disabled={!electricitySettings.useActualPrice}
                    />
                    {validationErrors.markupRate && (
                      <span className="text-sm text-red-500">{validationErrors.markupRate}</span>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label>VAT Multiplier</Label>
                    <Input
                      type="text"
                      value={localElectricityValues.vatMultiplier}
                      onChange={(e) => handleInputChange(e, 'vatMultiplier', setLocalElectricityValues)}
                      onBlur={() => handleInputBlur('vatMultiplier', localElectricityValues, electricitySettings, onElectricityUpdate, setLocalElectricityValues)}
                      disabled={!electricitySettings.useActualPrice}
                    />
                    {validationErrors.vatMultiplier && (
                      <span className="text-sm text-red-500">{validationErrors.vatMultiplier}</span>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label>Additional Costs (SEK/kWh)</Label>
                    <Input
                      type="text"
                      value={localElectricityValues.additionalCosts}
                      onChange={(e) => handleInputChange(e, 'additionalCosts', setLocalElectricityValues)}
                      onBlur={() => handleInputBlur('additionalCosts', localElectricityValues, electricitySettings, onElectricityUpdate, setLocalElectricityValues)}
                      disabled={!electricitySettings.useActualPrice}
                    />
                    {validationErrors.additionalCosts && (
                      <span className="text-sm text-red-500">{validationErrors.additionalCosts}</span>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label>Tax Reduction (SEK/kWh)</Label>
                    <Input
                      type="text"
                      value={localElectricityValues.taxReduction}
                      onChange={(e) => handleInputChange(e, 'taxReduction', setLocalElectricityValues)}
                      onBlur={() => handleInputBlur('taxReduction', localElectricityValues, electricitySettings, onElectricityUpdate, setLocalElectricityValues)}
                      disabled={!electricitySettings.useActualPrice}
                    />
                    {validationErrors.taxReduction && (
                      <span className="text-sm text-red-500">{validationErrors.taxReduction}</span>
                    )}
                  </div>
                </div>
              </TabsContent>
            </Tabs>
          </div>
        </div>
      )}
    </>
  );
}
// src/types.ts
export interface PriceData {
    timestamp: string;
    price: number;
    buy_price: number;
    sell_price: number;
  }
  
  export interface HourlyData {
    hour: string;
    price: number;
    batteryLevel: number;
    action: number;
    gridUsed: number;
  }
  
  export interface ScheduleSummary {
    baseCost: number;
    optimizedCost: number;
    savings: number;
    cycleCount: number;
  }
  
  export interface ScheduleData {
    hourlyData: HourlyData[];
    summary: ScheduleSummary;
  }
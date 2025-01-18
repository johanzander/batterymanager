
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
    gridCost: number;     
    batteryCost: number; 
    totalCost: number;   
    savings: number;
  }
  
  export interface ScheduleSummary {
    baseCost: number;
    optimizedCost: number;
    savings: number;
    cycleCount: number;
    gridCosts: number;    
    batteryCosts: number;
  }
  
  export interface ScheduleData {
    hourlyData: HourlyData[];
    summary: ScheduleSummary;
  }
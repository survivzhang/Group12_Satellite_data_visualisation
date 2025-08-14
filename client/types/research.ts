export interface Parameter {
  id: string;
  name: string;
  unit: string;
  color: string;
  icon: React.ReactNode;
}

export interface TimeRange {
  start: Date;
  end: Date;
  granularity: 'months' | 'weeks' | 'days' | 'hours';
}

export interface MapInstance {
  id: string;
  parameter: string;
  title: string;
}

export interface DataPoint {
  id: number;
  lat: number;
  lng: number;
  value: number;
  timestamp: Date;
  quality?: 'good' | 'questionable' | 'bad';
}

export interface DataFile {
  parameter: string;
  generatedAt: number;
  count: number;
  data: DataPoint[];
}

export interface DataStore {
  lastUpdate: string;
  filesCount: number;
  totalSize: number;
}
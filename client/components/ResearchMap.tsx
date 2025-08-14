"use client";

import { useState, useEffect } from 'react';
import { Parameter, TimeRange } from '@/types/research';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { MapPin, Layers, Zap } from 'lucide-react';

interface ResearchMapProps {
  parameter: string;
  timeRange: TimeRange;
  availableParameters: Parameter[];
  isFullscreen?: boolean;
}

export function ResearchMap({ parameter, timeRange, availableParameters, isFullscreen }: ResearchMapProps) {
  const [isLoading, setIsLoading] = useState(true);
  const [dataPoints, setDataPoints] = useState<any[]>([]);
  
  const currentParam = availableParameters.find(p => p.id === parameter);

  useEffect(() => {
    // Simulate data loading
    setIsLoading(true);
    const timer = setTimeout(() => {
      // Generate mock data points based on parameter
      const mockData = generateMockData(parameter, timeRange);
      setDataPoints(mockData);
      setIsLoading(false);
    }, 1000);

    return () => clearTimeout(timer);
  }, [parameter, timeRange]);

  const generateMockData = (param: string, range: TimeRange) => {
    // Mock data generation based on parameter type
    const points = [];
    for (let i = 0; i < 20; i++) {
      points.push({
        id: i,
        lat: -22.3 + (Math.random() - 0.5) * 2, // Ningaloo Reef area
        lng: 113.8 + (Math.random() - 0.5) * 2,
        value: getRandomValue(param),
        timestamp: new Date(range.start.getTime() + Math.random() * (range.end.getTime() - range.start.getTime()))
      });
    }
    return points;
  };

  const getRandomValue = (param: string) => {
    switch (param) {
      case 'sst': return 18 + Math.random() * 12; // 18-30°C
      case 'chlorophyll': return Math.random() * 5; // 0-5 mg/m³
      case 'salinity': return 34 + Math.random() * 2; // 34-36 PSU
      case 'bathymetry': return -Math.random() * 200; // 0-200m depth
      default: return Math.random() * 100;
    }
  };

  if (isLoading) {
    return (
      <div className="h-96 bg-slate-100 rounded-lg flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className={`relative ${isFullscreen ? 'h-full' : 'h-96'} bg-gradient-to-br from-blue-900 via-blue-700 to-teal-600 rounded-lg overflow-hidden`}>
      {/* Mock map background with Ningaloo Reef outline */}
      <svg 
        className="absolute inset-0 w-full h-full" 
        viewBox={`0 0 ${isFullscreen ? '800' : '400'} ${isFullscreen ? '600' : '300'}`}
        style={{ filter: 'drop-shadow(0 2px 8px rgba(0,0,0,0.3))' }}
      >
        {/* Coastline outline */}
        <path
          d={isFullscreen 
            ? "M 100 100 Q 200 80 300 120 T 600 160 L 700 240 Q 680 400 640 500 L 560 560 Q 400 540 240 500 Q 160 400 140 300 Q 120 200 100 100 Z"
            : "M 50 50 Q 100 40 150 60 T 300 80 L 350 120 Q 340 200 320 250 L 280 280 Q 200 270 120 250 Q 80 200 70 150 Q 60 100 50 50 Z"
          }
          fill="rgba(139, 69, 19, 0.3)"
          stroke="rgba(139, 69, 19, 0.6)"
          strokeWidth="2"
        />
        
        {/* Reef areas */}
        <ellipse 
          cx={isFullscreen ? "360" : "180"} 
          cy={isFullscreen ? "240" : "120"} 
          rx={isFullscreen ? "120" : "60"} 
          ry={isFullscreen ? "60" : "30"} 
          fill="rgba(34, 197, 94, 0.4)" 
        />
        <ellipse 
          cx={isFullscreen ? "440" : "220"} 
          cy={isFullscreen ? "360" : "180"} 
          rx={isFullscreen ? "80" : "40"} 
          ry={isFullscreen ? "40" : "20"} 
          fill="rgba(34, 197, 94, 0.4)" 
        />
        <ellipse 
          cx={isFullscreen ? "300" : "150"} 
          cy={isFullscreen ? "400" : "200"} 
          rx={isFullscreen ? "60" : "30"} 
          ry={isFullscreen ? "30" : "15"} 
          fill="rgba(34, 197, 94, 0.4)" 
        />

        {/* Data points visualization */}
        {dataPoints.map((point, index) => {
          const scale = isFullscreen ? 2 : 1;
          const x = (100 * scale) + (point.lng - 113) * (50 * scale);
          const y = (100 * scale) + (point.lat + 22.5) * (40 * scale);
          const intensity = Math.abs(point.value) / 100;
          
          return (
            <g key={point.id}>
              <circle
                cx={x}
                cy={y}
                r={(4 + intensity * 6) * scale}
                fill={currentParam?.color}
                fillOpacity={0.7}
                className="animate-pulse"
              />
              <circle
                cx={x}
                cy={y}
                r={2 * scale}
                fill="white"
                fillOpacity={0.9}
              />
            </g>
          );
        })}
      </svg>

      {/* Parameter info overlay */}
      <div className="absolute top-4 left-4 flex flex-col gap-2">
        <Badge className="bg-white/20 backdrop-blur text-white border-white/30">
          <div className="flex items-center gap-1">
            {currentParam?.icon}
            {currentParam?.name}
          </div>
        </Badge>
        <Badge className="bg-white/20 backdrop-blur text-white border-white/30">
          <MapPin className="h-3 w-3 mr-1" />
          {dataPoints.length} data points
        </Badge>
      </div>

      {/* Legend */}
      <div className="absolute bottom-4 right-4 bg-white/90 backdrop-blur rounded-lg p-3">
        <div className="text-xs font-medium text-slate-700 mb-2 flex items-center gap-1">
          <Layers className="h-3 w-3" />
          Range
        </div>
        <div className="flex items-center gap-2">
          <div className="w-16 h-2 rounded-full bg-gradient-to-r from-blue-200 to-red-500"></div>
          <span className="text-xs text-slate-600">
            {currentParam?.unit}
          </span>
        </div>
      </div>

      {/* Live indicator */}
      <div className="absolute top-4 right-4">
        <Badge className="bg-green-500/20 backdrop-blur text-green-100 border-green-400/30 animate-pulse">
          <Zap className="h-3 w-3 mr-1" />
          Live
        </Badge>
      </div>
    </div>
  );
}
"use client";

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { 
  RefreshCw, 
  Map as MapIcon, 
  Plus,
  Calendar,
  Thermometer,
  Waves,
  Eye,
  Activity,
  Maximize2,
  Minimize2,
  X
} from 'lucide-react';
import { ResearchMap } from '@/components/ResearchMap';
import { ParameterSelector } from '@/components/ParameterSelector';
import { TimelineSlider } from '@/components/TimelineSlider';
import { useDataStore } from '@/hooks/useDataStore';
import { Parameter, TimeRange, MapInstance } from '@/types/research';

export default function NingalooResearchApp() {
  const [mapInstances, setMapInstances] = useState<MapInstance[]>([
    { id: '1', parameter: 'sst', title: 'Sea Surface Temperature' }
  ]);
  const [selectedTimeRange, setSelectedTimeRange] = useState<TimeRange>({
    start: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000),
    end: new Date(),
    granularity: 'days'
  });
  const [expandedParams, setExpandedParams] = useState(false);
  const [fullscreenMap, setFullscreenMap] = useState<string | null>(null);
  
  const { lastUpdate, isUpdating, updateData, missingFiles } = useDataStore();

  const availableParameters: Parameter[] = [
    { 
      id: 'sst', 
      name: 'Sea Surface Temperature', 
      unit: '°C', 
      color: '#ef4444',
      icon: <Thermometer className="h-4 w-4" />
    },
    { 
      id: 'chlorophyll', 
      name: 'Chlorophyll-a Concentration', 
      unit: 'mg/m³', 
      color: '#22c55e',
      icon: <Activity className="h-4 w-4" />
    },
    { 
      id: 'salinity', 
      name: 'Sea Surface Salinity', 
      unit: 'PSU', 
      color: '#3b82f6',
      icon: <Waves className="h-4 w-4" />
    },
    { 
      id: 'bathymetry', 
      name: 'Bathymetry', 
      unit: 'm', 
      color: '#8b5cf6',
      icon: <Eye className="h-4 w-4" />
    }
  ];

  const addMapInstance = (parameter: string) => {
    const param = availableParameters.find(p => p.id === parameter);
    if (param) {
      const newInstance: MapInstance = {
        id: Date.now().toString(),
        parameter,
        title: param.name
      };
      setMapInstances([...mapInstances, newInstance]);
    }
  };

  const removeMapInstance = (id: string) => {
    if (mapInstances.length > 1) {
      setMapInstances(mapInstances.filter(instance => instance.id !== id));
    }
  };

  const updateMapParameter = (id: string, parameter: string) => {
    const param = availableParameters.find(p => p.id === parameter);
    if (param) {
      setMapInstances(mapInstances.map(instance => 
        instance.id === id 
          ? { ...instance, parameter, title: param.name }
          : instance
      ));
    }
  };

  const toggleFullscreen = (mapId: string) => {
    setFullscreenMap(fullscreenMap === mapId ? null : mapId);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
      <div className="container mx-auto px-4 py-6 space-y-6">
        {/* Header */}
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-slate-900 flex items-center gap-3">
              <div className="p-2 bg-blue-600 rounded-lg">
                <Waves className="h-6 w-6 text-white" />
              </div>
              Ningaloo Reef Research Cruise
            </h1>
            <p className="text-slate-600 mt-1">
              Marine ecosystem data visualization and analysis platform
            </p>
          </div>
          
          <div className="flex items-center gap-3">
            <div className="text-sm text-slate-600">
              Last update: {lastUpdate ? new Date(lastUpdate).toLocaleString() : 'Never'}
            </div>
            <Button 
              onClick={updateData}
              disabled={isUpdating}
              className="bg-blue-600 hover:bg-blue-700 text-white"
            >
              <RefreshCw className={`h-4 w-4 mr-2 ${isUpdating ? 'animate-spin' : ''}`} />
              Update Data
            </Button>
            {missingFiles > 0 && (
              <Badge variant="destructive">
                {missingFiles} missing files
              </Badge>
            )}
          </div>
        </div>

        {/* Parameter Selector */}
        <ParameterSelector 
          parameters={availableParameters}
          expanded={expandedParams}
          onToggle={() => setExpandedParams(!expandedParams)}
          onAddMap={addMapInstance}
        />

        {/* Maps Grid */}
        <div className="flex gap-6 overflow-x-auto pb-4">
          {mapInstances.map((instance, index) => (
            <Card key={instance.id} className="flex-shrink-0 w-96 overflow-hidden shadow-lg border-0 bg-white/80 backdrop-blur">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-lg font-semibold text-slate-800 flex items-center gap-2">
                    <MapIcon className="h-5 w-5" />
                    {instance.title}
                  </CardTitle>
                  <div className="flex items-center gap-2">
                    <select 
                      value={instance.parameter}
                      onChange={(e) => updateMapParameter(instance.id, e.target.value)}
                      className="text-sm border border-slate-200 rounded px-2 py-1 bg-white"
                    >
                      {availableParameters.map(param => (
                        <option key={param.id} value={param.id}>
                          {param.name}
                        </option>
                      ))}
                    </select>
                    {mapInstances.length > 1 && (
                      <Button 
                        variant="outline" 
                        size="sm"
                        onClick={() => removeMapInstance(instance.id)}
                        className="h-8 w-8 p-0"
                      >
                        ×
                      </Button>
                    )}
                  </div>
                </div>
              </CardHeader>
              <CardContent className="pt-0">
                <ResearchMap 
                  parameter={instance.parameter}
                  timeRange={selectedTimeRange}
                  availableParameters={availableParameters}
                />
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Add Map Button */}
        <div className={`flex justify-center ${fullscreenMap ? 'hidden' : ''}`}>
          <Button 
            variant="outline"
            onClick={() => addMapInstance('sst')}
            className="border-dashed border-2 border-slate-300 hover:border-blue-500 hover:bg-blue-50"
          >
            <Plus className="h-4 w-4 mr-2" />
            Add Map Instance
          </Button>
        </div>

        {/* Timeline Slider */}
        <Card className={`bg-white/80 backdrop-blur border-0 shadow-lg ${fullscreenMap ? 'hidden' : ''}`}>
          <CardHeader className="pb-3">
            <CardTitle className="text-lg font-semibold text-slate-800 flex items-center gap-2">
              <Calendar className="h-5 w-5" />
              Temporal Analysis
            </CardTitle>
          </CardHeader>
          <CardContent>
            <TimelineSlider 
              timeRange={selectedTimeRange}
              onChange={setSelectedTimeRange}
            />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
"use client";

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ChevronDown, ChevronUp, Plus, Filter } from 'lucide-react';
import { Parameter } from '@/types/research';

interface ParameterSelectorProps {
  parameters: Parameter[];
  expanded: boolean;
  onToggle: () => void;
  onAddMap: (parameter: string) => void;
}

export function ParameterSelector({ 
  parameters, 
  expanded, 
  onToggle, 
  onAddMap 
}: ParameterSelectorProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');

  const categories = [
    { id: 'all', name: 'All Parameters', count: parameters.length },
    { id: 'physical', name: 'Physical', count: 2 },
    { id: 'biological', name: 'Biological', count: 1 },
    { id: 'geological', name: 'Geological', count: 1 }
  ];

  const getParameterCategory = (paramId: string) => {
    switch (paramId) {
      case 'sst':
      case 'salinity':
        return 'physical';
      case 'chlorophyll':
        return 'biological';
      case 'bathymetry':
        return 'geological';
      default:
        return 'physical';
    }
  };

  const filteredParameters = parameters.filter(param => {
    const matchesSearch = param.name.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesCategory = selectedCategory === 'all' || getParameterCategory(param.id) === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  return (
    <Card className="bg-white/80 backdrop-blur border-0 shadow-lg">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Filter className="h-5 w-5 text-slate-600" />
            <span className="font-semibold text-slate-800">Data Parameters</span>
            <Badge variant="secondary">{parameters.length} available</Badge>
          </div>
          <Button 
            variant="ghost" 
            size="sm" 
            onClick={onToggle}
            className="hover:bg-slate-100"
          >
            {expanded ? (
              <>
                <ChevronUp className="h-4 w-4 mr-1" />
                Collapse
              </>
            ) : (
              <>
                <ChevronDown className="h-4 w-4 mr-1" />
                Expand
              </>
            )}
          </Button>
        </div>
      </CardHeader>
      
      {expanded && (
        <CardContent className="pt-0">
          <div className="space-y-4">
            {/* Search and Category Filter */}
            <div className="flex flex-col sm:flex-row gap-3">
              <input
                type="text"
                placeholder="Search parameters..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="flex-1 px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <select
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                className="px-3 py-2 border border-slate-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {categories.map(category => (
                  <option key={category.id} value={category.id}>
                    {category.name} ({category.count})
                  </option>
                ))}
              </select>
            </div>

            {/* Parameter Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              {filteredParameters.map(param => (
                <div
                  key={param.id}
                  className="group p-4 rounded-lg border border-slate-200 hover:border-blue-300 hover:bg-blue-50/50 transition-all duration-200 cursor-pointer"
                  onClick={() => onAddMap(param.id)}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div 
                      className="p-2 rounded-full"
                      style={{ backgroundColor: `${param.color}20`, color: param.color }}
                    >
                      {param.icon}
                    </div>
                    <Button 
                      size="sm" 
                      variant="ghost"
                      className="opacity-0 group-hover:opacity-100 transition-opacity h-6 w-6 p-0 hover:bg-blue-100"
                    >
                      <Plus className="h-3 w-3" />
                    </Button>
                  </div>
                  <h4 className="font-medium text-slate-800 text-sm mb-1">
                    {param.name}
                  </h4>
                  <p className="text-xs text-slate-500">
                    Unit: {param.unit}
                  </p>
                  <div className="mt-2">
                    <Badge 
                      variant="outline" 
                      className="text-xs"
                      style={{ borderColor: param.color, color: param.color }}
                    >
                      {getParameterCategory(param.id)}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>

            {filteredParameters.length === 0 && (
              <div className="text-center py-8 text-slate-500">
                <Filter className="h-12 w-12 mx-auto mb-3 opacity-50" />
                <p>No parameters match your search criteria.</p>
              </div>
            )}
          </div>
        </CardContent>
      )}
    </Card>
  );
}
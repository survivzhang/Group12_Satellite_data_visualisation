"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ChevronDown, ChevronUp, Plus, Filter } from "lucide-react";
import { Parameter } from "@/types/research";

interface ParameterSelectorProps {
  parameters: Parameter[];
  expanded: boolean;
  onToggle: () => void;
  onAddMap: (parameter: string) => void;
  mapCount: number;
}

export function ParameterSelector({
  parameters,
  expanded,
  onToggle,
  onAddMap,
  mapCount,
}: ParameterSelectorProps) {
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string>("all");

  const categories = [
    { id: "all", name: "All Parameters", count: parameters.length },
    { id: "physical", name: "Physical", count: 2 },
    { id: "biological", name: "Biological", count: 1 },
    { id: "geological", name: "Geological", count: 1 },
  ];

  const getParameterCategory = (paramId: string) => {
    switch (paramId) {
      case "sst":
      case "salinity":
        return "physical";
      case "chlorophyll":
        return "biological";
      case "bathymetry":
        return "geological";
      default:
        return "physical";
    }
  };

  const filteredParameters = parameters.filter((param) => {
    const matchesSearch = param.name.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesCategory =
      selectedCategory === "all" || getParameterCategory(param.id) === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  return (
    <Card className="bg-transparent border-0 shadow-none text-white">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Filter className="h-5 w-5 text-white/90" />
            <span className="font-semibold text-white">Data Parameters</span>
            <Badge className="bg-white/20 text-white border-white/20">{parameters.length} available</Badge>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => onAddMap("ssth")}
              disabled={mapCount >= 4}
              className="flex items-center gap-1 text-black hover:bg-gray-100"
              title="Add a new map instance (max 4)"
            >
              <Plus className="h-4 w-4" />
              Add Map ({mapCount}/4)
            </Button>

            <Button variant="ghost" size="sm" onClick={onToggle} className="hover:bg-white/10">
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
        </div>
      </CardHeader>

      {expanded && (
        <CardContent className="pt-0">
          <div className="space-y-4">
            {/* Search + filter */}
            <div className="flex flex-col sm:flex-row gap-3">
              <input
                type="text"
                placeholder="Search parameters..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="flex-1 px-3 py-2 rounded-lg text-sm
                           bg-white/10 text-white placeholder:text-white/60
                           border border-white/20 focus:outline-none focus:ring-2 focus:ring-cyan-400"
              />
              <select
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                className="px-3 py-2 rounded-lg text-sm bg-white/10 text-white
                           border border-white/20 focus:outline-none focus:ring-2 focus:ring-cyan-400"
              >
                {categories.map((category) => (
                  <option key={category.id} value={category.id} className="text-black">
                    {category.name} ({category.count})
                  </option>
                ))}
              </select>
            </div>

            {/* Parameter Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              {filteredParameters.map((param) => (
                <div
                  key={param.id}
                  className="group p-4 rounded-lg border border-white/20 bg-white/5
                             hover:border-cyan-300/50 hover:bg-cyan-300/10
                             transition-all duration-200 cursor-pointer"
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
                      className="opacity-0 group-hover:opacity-100 transition-opacity h-6 w-6 p-0 hover:bg-white/10"
                    >
                      <Plus className="h-3 w-3" />
                    </Button>
                  </div>
                  <h4 className="font-medium text-white text-sm mb-1">{param.name}</h4>
                  <p className="text-xs text-gray-200">Unit: {param.unit}</p>
                  <div className="mt-2">
                    <Badge
                      variant="outline"
                      className="text-xs bg-transparent"
                      style={{ borderColor: param.color, color: param.color }}
                    >
                      {getParameterCategory(param.id)}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>

            {filteredParameters.length === 0 && (
              <div className="text-center py-8 text-gray-300">
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

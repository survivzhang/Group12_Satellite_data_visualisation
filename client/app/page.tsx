"use client";

import Image from "next/image";
import { useMemo, useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  RefreshCw,
  Map as MapIcon,
  Calendar,
  Thermometer,
  Waves,
  Eye,
  Activity,
  Maximize2,
  Minimize2,
  X,
} from "lucide-react";
import { ResearchMap } from "@/components/ResearchMap";
import { ParameterSelector } from "@/components/ParameterSelector";
import { TimelineSlider } from "@/components/TimelineSlider";
import { useDataStore } from "@/hooks/useDataStore";
import { Parameter, TimeRange, MapInstance } from "@/types/research";

export default function NingalooResearchApp() {
  // Initialize with default values to avoid hydration mismatch
  const [mapInstances, setMapInstances] = useState<MapInstance[]>([
    { id: "1", parameter: "ssth", title: "Sea Surface Temperature (Himawari)" },
  ]);

  const [selectedTimeRange, setSelectedTimeRange] = useState<TimeRange>({
    start: new Date("2025-09-12T00:00:00Z"),
    end: new Date("2025-09-12T12:00:00Z"), // 设置为12小时后，避免水合错误
    granularity: "day",
  });

  const [expandedParams, setExpandedParams] = useState(false);
  const [fullscreenMap, setFullscreenMap] = useState<string | null>(null);
  const [isHydrated, setIsHydrated] = useState(false);

  // Global range state for all maps
  const [globalRange, setGlobalRange] = useState<{
    [parameter: string]: {
      min: string;
      max: string;
      appliedMin: string;
      appliedMax: string;
    };
  }>({});

  const {
    lastUpdate,
    isUpdating,
    updateData,
    missingFiles,
    getParameterFiles,
  } = useDataStore();

  // Load saved state from localStorage after hydration
  useEffect(() => {
    setIsHydrated(true);

    // Load map instances
    const storedMaps = localStorage.getItem("ningaloo-map-instances");
    if (storedMaps) {
      try {
        const parsedMaps = JSON.parse(storedMaps);
        setMapInstances(parsedMaps);
      } catch (error) {
        console.error("Failed to parse stored map instances:", error);
      }
    }

    // Load time range
    const storedTimeRange = localStorage.getItem("ningaloo-time-range");
    if (storedTimeRange) {
      try {
        const parsed = JSON.parse(storedTimeRange);
        setSelectedTimeRange({
          start: new Date(parsed.start),
          end: new Date(parsed.end),
          granularity: parsed.granularity,
        });
      } catch (error) {
        console.error("Failed to parse stored time range:", error);
        // 如果解析失败，设置默认时间范围
        setSelectedTimeRange({
          start: new Date("2025-09-12T00:00:00Z"),
          end: new Date(),
          granularity: "day",
        });
      }
    } else {
      // 如果没有存储的时间范围，设置默认时间范围
      setSelectedTimeRange({
        start: new Date("2025-09-12T00:00:00Z"),
        end: new Date(),
        granularity: "day",
      });
    }
  }, []);

  // Save map instances to localStorage whenever they change (only after hydration)
  useEffect(() => {
    if (isHydrated) {
      localStorage.setItem(
        "ningaloo-map-instances",
        JSON.stringify(mapInstances)
      );
    }
  }, [mapInstances, isHydrated]);

  // Save time range to localStorage whenever it changes (only after hydration)
  useEffect(() => {
    if (isHydrated) {
      localStorage.setItem(
        "ningaloo-time-range",
        JSON.stringify({
          start: selectedTimeRange.start.toISOString(),
          end: selectedTimeRange.end.toISOString(),
          granularity: selectedTimeRange.granularity,
        })
      );
    }
  }, [selectedTimeRange, isHydrated]);

  const availableParameters: Parameter[] = [
    {
      id: "ssth",
      name: "Sea Surface Temperature (Himawari)",
      unit: "°C",
      color: "#ef4444",
      icon: <Thermometer className="h-4 w-4" />,
    },
    {
      id: "sst-s3a",
      name: "Sea Surface Temperature (Sentinel-3A)",
      unit: "°C",
      color: "#ef4444",
      icon: <Thermometer className="h-4 w-4" />,
    },
    {
      id: "sst-s3b",
      name: "Sea Surface Temperature (Sentinel-3B)",
      unit: "°C",
      color: "#ef4444",
      icon: <Thermometer className="h-4 w-4" />,
    },
    {
      id: "chl-s3a",
      name: "Chlorophyll-a (Sentinel-3A)",
      unit: "mg/m³",
      color: "#22c55e",
      icon: <Activity className="h-4 w-4" />,
    },
    {
      id: "chl-s3b",
      name: "Chlorophyll-a (Sentinel-3B)",
      unit: "mg/m³",
      color: "#22c55e",
      icon: <Activity className="h-4 w-4" />,
    },
    {
      id: "b02-s2a",
      name: "B02 Reflectance (Sentinel-2A L2A)",
      unit: "reflectance",
      color: "#8b5cf6",
      icon: <Eye className="h-4 w-4" />,
    },
    {
      id: "b02-s2b",
      name: "B02 Reflectance (Sentinel-2B L2A)",
      unit: "reflectance",
      color: "#8b5cf6",
      icon: <Eye className="h-4 w-4" />,
    },
    {
      id: "ssha-swot",
      name: "Sea Surface Height Anomaly (SWOT, ssha_filtered)",
      unit: "m",
      color: "#3b82f6",
      icon: <Waves className="h-4 w-4" />,
    },
  ];

  // Cap at 4 instances
  const addMapInstance = (parameter: string) => {
    if (mapInstances.length >= 4) return;
    const param = availableParameters.find((p) => p.id === parameter);
    if (!param) return;
    const newInstance: MapInstance = {
      id: Date.now().toString(),
      parameter,
      title: param.name,
    };
    setMapInstances((prev) => [...prev, newInstance]);
  };

  const removeMapInstance = (id: string) => {
    if (mapInstances.length <= 1) return;
    setMapInstances((prev) => prev.filter((m) => m.id !== id));
    if (fullscreenMap === id) setFullscreenMap(null);
  };

  const updateMapParameter = (id: string, parameter: string) => {
    const param = availableParameters.find((p) => p.id === parameter);
    if (!param) return;
    setMapInstances((prev) =>
      prev.map((m) =>
        m.id === id ? { ...m, parameter, title: param.name } : m
      )
    );
  };

  const toggleFullscreen = (mapId: string) => {
    setFullscreenMap((cur) => (cur === mapId ? null : mapId));
  };

  // Range management functions
  const updateRange = (parameter: string, min: string, max: string) => {
    setGlobalRange((prev) => ({
      ...prev,
      [parameter]: {
        ...prev[parameter],
        min,
        max,
      },
    }));
  };

  const applyRange = (
    parameter: string,
    appliedMin: string,
    appliedMax: string
  ) => {
    setGlobalRange((prev) => ({
      ...prev,
      [parameter]: {
        ...prev[parameter],
        appliedMin,
        appliedMax,
      },
    }));
  };

  const resetRange = (parameter: string) => {
    setGlobalRange((prev) => ({
      ...prev,
      [parameter]: {
        min: "",
        max: "",
        appliedMin: "",
        appliedMax: "",
      },
    }));
  };

  const getRangeForParameter = (parameter: string) => {
    const range = globalRange[parameter] || {
      min: "",
      max: "",
      appliedMin: "",
      appliedMax: "",
    };
    console.log(`Getting range for ${parameter}:`, range);
    return range;
  };

  // ===== Layout helpers =====
  const gridClass = useMemo(() => {
    const n = mapInstances.length;
    if (n <= 1) return "grid grid-cols-1 gap-6";
    if (n === 2) return "grid grid-cols-2 gap-6";
    if (n === 3) return "grid grid-cols-2 grid-rows-2 gap-6";
    return "grid grid-cols-2 grid-rows-2 gap-6"; // 4 maps in 2x2 grid
  }, [mapInstances.length]);

  // For 3 maps: first map spans both columns in first row, next two in second row
  const cellSpan = (n: number, idx: number) => {
    if (n === 3 && idx === 0) return "col-span-2 row-span-1";
    return "";
  };

  return (
    <div
      className="min-h-screen"
      style={{
        background: `
          radial-gradient(ellipse at top, #0a1a2e 0%, #16213e 30%, #1e3a8a 60%, #1e40af 100%),
          linear-gradient(135deg, #0f172a 0%, #1e3a8a 25%, #3b82f6 50%, #60a5fa 75%, #fbbf24 100%),
          linear-gradient(45deg, #0f172a 0%, #1e3a8a 50%, #3b82f6 100%)
        `,
        backgroundAttachment: "fixed",
        backgroundSize: "100% 100%, 100% 100%, 100% 100%",
        backgroundPosition: "center, center, center",
        backgroundBlendMode: "multiply, overlay, normal",
      }}
    >
      {/* Fullscreen Overlay */}
      {fullscreenMap && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-6">
          <Card className="w-full h-full max-w-7xl overflow-hidden bg-white/85 backdrop-blur-md border border-white/20 shadow-xl flex flex-col">
            <CardHeader className="relative pb-4 flex items-center justify-center border-b">
              <CardTitle className="text-xl font-semibold text-white flex items-center gap-3">
                <MapIcon className="h-6 w-6 flex-shrink-0" />
                <span className="truncate">
                  {mapInstances.find((m) => m.id === fullscreenMap)?.title}
                </span>
              </CardTitle>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setFullscreenMap(null)}
                className="absolute right-4 top-3 h-9 w-9 p-0 hover:bg-gray-100"
                title="Exit Fullscreen"
              >
                <Minimize2 className="h-4 w-4" />
              </Button>
            </CardHeader>
            <CardContent className="flex-1 flex flex-col p-4">
              {mapInstances
                .filter((m) => m.id === fullscreenMap)
                .map((m) => (
                  <div
                    key={m.id}
                    className="h-full rounded-lg border border-slate-300 shadow-sm overflow-hidden"
                  >
                    <ResearchMap
                      parameter={m.parameter}
                      timeRange={selectedTimeRange}
                      availableParameters={availableParameters}
                      isFullscreen={true}
                      getParameterFiles={getParameterFiles}
                      range={getRangeForParameter(m.parameter)}
                      onRangeUpdate={updateRange}
                      onRangeApply={applyRange}
                      onRangeReset={resetRange}
                    />
                  </div>
                ))}
            </CardContent>
          </Card>
        </div>
      )}

      <div className="container mx-auto px-4 py-6 space-y-6">
        {/* Header */}
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
              <Image
                src="/uwa-logo.jpg"
                alt="App Logo"
                width={150}
                height={50}
                className="rounded-md shadow-md ring-1 ring-white/30"
                priority
              />
              <div>
                <span className="text-2xl sm:text-3xl font-bold text-white block">
                  Ningaloo Reef Research Cruise
                </span>
                <p className="text-gray-200 mt-1">
                  Marine ecosystem data visualization and analysis platform
                </p>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="text-sm text-slate-600">
              Last update:{" "}
              {lastUpdate ? new Date(lastUpdate).toLocaleString() : "Never"}
            </div>
            <Button
              onClick={updateData}
              disabled={isUpdating}
              className="bg-cyan-600 hover:bg-cyan-700 text-white shadow-sm"
            >
              <RefreshCw
                className={`h-4 w-4 mr-2 ${isUpdating ? "animate-spin" : ""}`}
              />
              Update Data
            </Button>
            {missingFiles > 0 && (
              <Badge variant="destructive">{missingFiles} missing files</Badge>
            )}
          </div>
        </div>

        {/* Data Parameters (transparent glass + light text) */}
        <Card className="bg-white/10 backdrop-blur-md border border-white/20 shadow-xl text-white">
          <CardContent className="p-0">
            <ParameterSelector
              parameters={availableParameters}
              expanded={expandedParams}
              onToggle={() => setExpandedParams((v) => !v)}
              onAddMap={addMapInstance}
              mapCount={mapInstances.length}
            />
          </CardContent>
        </Card>

        {/* Maps Grid */}
        <div className={gridClass}>
          {mapInstances.map((instance, index) => (
            <div
              key={instance.id}
              className={cellSpan(mapInstances.length, index)}
            >
              <Card className="w-full h-full overflow-hidden bg-white/10 backdrop-blur-md border border-white/20 shadow-xl text-white flex flex-col">
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between gap-2">
                    <CardTitle className="flex items-center gap-2 min-w-0">
                      <MapIcon className="h-5 w-5 flex-shrink-0" />
                      <select
                        value={instance.parameter}
                        onChange={(e) =>
                          updateMapParameter(instance.id, e.target.value)
                        }
                        className="text-sm font-semibold border-0 bg-white/10 text-white rounded px-2 py-1 truncate outline-none focus:ring-2 focus:ring-cyan-400"
                        aria-label="Select parameter"
                      >
                        {availableParameters.map((p) => (
                          <option
                            key={p.id}
                            value={p.id}
                            className="text-black"
                          >
                            {p.name}
                          </option>
                        ))}
                      </select>
                    </CardTitle>

                    <div className="flex items-center gap-2 shrink-0">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => toggleFullscreen(instance.id)}
                        className="h-8 w-8 p-0 bg-gray-800 border-gray-600 text-white hover:bg-gray-700 hover:text-white hover:border-gray-500"
                        title="Fullscreen"
                      >
                        <Maximize2 className="h-4 w-4" />
                      </Button>
                      {mapInstances.length > 1 && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => removeMapInstance(instance.id)}
                          className="h-8 w-8 p-0 bg-gray-800 border-gray-600 text-white hover:bg-gray-700 hover:text-white hover:border-gray-500"
                          title="Remove Map"
                        >
                          <X className="h-4 w-4" />
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
                    getParameterFiles={getParameterFiles}
                    range={getRangeForParameter(instance.parameter)}
                    onRangeUpdate={updateRange}
                    onRangeApply={applyRange}
                    onRangeReset={resetRange}
                  />
                </CardContent>
              </Card>
            </div>
          ))}
        </div>

        {/* Timeline */}
        <Card className="bg-white/10 backdrop-blur-md border border-white/20 shadow-xl text-white">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg font-semibold flex items-center gap-2">
              <Calendar className="h-5 w-5" />
              Temporal Analysis
            </CardTitle>
          </CardHeader>
          <CardContent>
            {/* new prop to theme the slider/buttons */}
            <TimelineSlider
              timeRange={selectedTimeRange}
              onChange={setSelectedTimeRange}
              variant="glass"
            />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

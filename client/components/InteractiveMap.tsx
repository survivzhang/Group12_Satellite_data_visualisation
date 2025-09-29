"use client";

import { useState, useEffect, useMemo, useCallback } from "react";
import dynamic from "next/dynamic";
import { Parameter, TimeRange } from "@/types/research";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  MapPin,
  Layers,
  Zap,
  Settings,
  RotateCcw,
  Info,
  Globe,
} from "lucide-react";

// Dynamic import to avoid SSR issues with Leaflet
const MapContainer = dynamic(
  () => import("react-leaflet").then((mod) => mod.MapContainer),
  { ssr: false }
);
const TileLayer = dynamic(
  () => import("react-leaflet").then((mod) => mod.TileLayer),
  { ssr: false }
);
const CircleMarker = dynamic(
  () => import("react-leaflet").then((mod) => mod.CircleMarker),
  { ssr: false }
);
const Popup = dynamic(
  () => import("react-leaflet").then((mod) => mod.Popup),
  { ssr: false }
);

interface InteractiveMapProps {
  parameter: string;
  timeRange: TimeRange;
  availableParameters: Parameter[];
  isFullscreen?: boolean;
  getParameterFiles?: (
    paramId: string,
    fileType: "nc" | "png"
  ) => Promise<any[]>;
}

interface DataPoint {
  lat: number;
  lon: number;
  value: number;
}

interface MapData {
  satellite: string;
  parameter: string;
  filename: string;
  data_points: DataPoint[];
  bounds: {
    north: number;
    south: number;
    east: number;
    west: number;
  };
  statistics: {
    min: number;
    max: number;
    mean: number;
    count: number;
    units: string;
  };
  metadata: {
    downsampled: boolean;
    downsample_factor: number;
    original_size: number;
    processed_size: number;
  };
}

// 卫星参数映射
const SATELLITE_MAPPING = {
  ssth: {
    satellite: "himawari",
    parameter: "sst",
  },
  "sst-s3a": {
    satellite: "sentinel3a",
    parameter: "sst",
  },
  "sst-s3b": {
    satellite: "sentinel3b",
    parameter: "sst",
  },
  "chl-s3a": {
    satellite: "sentinel3a",
    parameter: "chl",
  },
  "chl-s3b": {
    satellite: "sentinel3b",
    parameter: "chl",
  },
  "ssha-swot": {
    satellite: "swot",
    parameter: "ssha",
  },
};

// 获取Sentinel-3的fallback文件名
const getSentinel3FallbackFilename = (param: string): string => {
  switch (param) {
    case "sst-s3a":
      return "20250923_211031.nc";
    case "sst-s3b":
      return "20250923_211028.nc";
    case "chl-s3a":
      return "20250923_211036.nc";
    case "chl-s3b":
      return "20250923_211040.nc";
    case "ssha-swot":
      return "subset_SWOT_L3_LR_SSH_Expert_029_062_20250226T145417_20250226T154543_v2.0.1.nc";
    default:
      return "20250923_211031.nc";
  }
};

// 颜色映射函数
const getColorForValue = (value: number, min: number, max: number, parameter: string): string => {
  const normalized = (value - min) / (max - min);
  
  if (parameter.includes("sst") || parameter === "ssth") {
    // 海温：蓝色(冷) -> 红色(热)
    const r = Math.round(normalized * 255);
    const g = Math.round((1 - Math.abs(normalized - 0.5) * 2) * 255);
    const b = Math.round((1 - normalized) * 255);
    return `rgb(${r}, ${g}, ${b})`;
  } else if (parameter.includes("chl")) {
    // 叶绿素：深蓝 -> 绿色 -> 黄色
    if (normalized < 0.5) {
      const r = 0;
      const g = Math.round(normalized * 2 * 255);
      const b = Math.round((1 - normalized * 2) * 255);
      return `rgb(${r}, ${g}, ${b})`;
    } else {
      const r = Math.round((normalized - 0.5) * 2 * 255);
      const g = 255;
      const b = 0;
      return `rgb(${r}, ${g}, ${b})`;
    }
  } else if (parameter.includes("ssha") || parameter === "ssha-swot") {
    // 海面高度异常：深蓝 -> 绿色 -> 黄色
    if (normalized < 0.5) {
      const r = 0;
      const g = Math.round(normalized * 2 * 255);
      const b = Math.round((1 - normalized * 2) * 255);
      return `rgb(${r}, ${g}, ${b})`;
    } else {
      const r = Math.round((normalized - 0.5) * 2 * 255);
      const g = 255;
      const b = 0;
      return `rgb(${r}, ${g}, ${b})`;
    }
  }
  
  // 默认颜色方案
  const r = Math.round(normalized * 255);
  const g = Math.round((1 - normalized) * 255);
  const b = 128;
  return `rgb(${r}, ${g}, ${b})`;
};

export function InteractiveMap({
  parameter,
  timeRange,
  availableParameters,
  isFullscreen,
  getParameterFiles,
}: InteractiveMapProps): JSX.Element {
  const [mapData, setMapData] = useState<MapData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isInfoDialogOpen, setIsInfoDialogOpen] = useState(false);

  const currentParam = availableParameters.find((p) => p.id === parameter);
  const satelliteMapping = SATELLITE_MAPPING[parameter as keyof typeof SATELLITE_MAPPING];

  // 获取当前时间戳和文件名
  const currentTimestamp = useMemo(() => {
    if (!satelliteMapping) return null;

    const utcDate = new Date(timeRange.start.getTime());
    utcDate.setUTCMinutes(0, 0, 0);

    if (parameter === "ssth") {
      // Himawari格式: YYYYMMDDHHMMSS
      const year = utcDate.getUTCFullYear();
      const month = String(utcDate.getUTCMonth() + 1).padStart(2, "0");
      const day = String(utcDate.getUTCDate()).padStart(2, "0");
      const hour = String(utcDate.getUTCHours()).padStart(2, "0");
      return `${year}${month}${day}${hour}0000`;
    } else {
      // Sentinel-3格式
      const year = utcDate.getUTCFullYear();
      const month = String(utcDate.getUTCMonth() + 1).padStart(2, "0");
      const day = String(utcDate.getUTCDate()).padStart(2, "0");
      const hour = String(utcDate.getUTCHours()).padStart(2, "0");
      const minute = String(utcDate.getUTCMinutes()).padStart(2, "0");
      const second = String(utcDate.getUTCSeconds()).padStart(2, "0");
      return `${year}${month}${day}_${hour}${minute}${second}`;
    }
  }, [parameter, timeRange.start, satelliteMapping]);

  // 获取NC文件名
  const getNcFilename = useCallback(async (): Promise<string | null> => {
    if (!satelliteMapping || !getParameterFiles) return null;

    try {
      if (parameter === "ssth") {
        // Himawari: 直接使用时间戳构造文件名
        return `${currentTimestamp}.nc`;
      } else if (parameter === "ssha-swot") {
        // SWOT: 获取可用的NC文件
        const ncFiles = await getParameterFiles(parameter, "nc");
        if (ncFiles && ncFiles.length > 0) {
          return ncFiles[0].filename;
        } else {
          return getSentinel3FallbackFilename(parameter);
        }
      } else {
        // Sentinel-3: 获取可用的NC文件
        const ncFiles = await getParameterFiles(parameter, "nc");
        if (ncFiles && ncFiles.length > 0) {
          return ncFiles[0].filename;
        } else {
          return getSentinel3FallbackFilename(parameter);
        }
      }
    } catch (error) {
      console.warn("Failed to get NC filename:", error);
      if (parameter === "ssth") {
        return `${currentTimestamp}.nc`;
      } else {
        return getSentinel3FallbackFilename(parameter);
      }
    }
  }, [parameter, satelliteMapping, getParameterFiles, currentTimestamp]);

  // 加载地图数据
  const loadMapData = useCallback(async () => {
    if (!satelliteMapping) {
      setError("Unsupported parameter for interactive map");
      setIsLoading(false);
      return;
    }

    try {
      setIsLoading(true);
      setError(null);

      const ncFilename = await getNcFilename();
      if (!ncFilename) {
        throw new Error("Could not determine NC filename");
      }

      const targetTime = timeRange.start.toISOString();
      const apiUrl = `http://localhost:8000/api/v1/satellites/${satelliteMapping.satellite}/${satelliteMapping.parameter}/data/${ncFilename}?target_time=${encodeURIComponent(targetTime)}`;

      console.log(`Loading interactive map data from: ${apiUrl}`);

      const response = await fetch(apiUrl);
      if (!response.ok) {
        throw new Error(`Failed to load map data: ${response.statusText}`);
      }

      const data = await response.json();
      setMapData(data);
      console.log("Interactive map data loaded:", data);
    } catch (error) {
      console.error("Error loading map data:", error);
      setError(error instanceof Error ? error.message : "Failed to load map data");
    } finally {
      setIsLoading(false);
    }
  }, [satelliteMapping, getNcFilename, timeRange.start]);

  // 当参数或时间变化时重新加载数据
  useEffect(() => {
    loadMapData();
  }, [loadMapData]);

  // 计算地图中心和边界
  const mapCenter = useMemo(() => {
    if (!mapData) return [-22.0, 114.0]; // 默认中心点

    const { bounds } = mapData;
    
    // Check for valid bounds
    if (isNaN(bounds.north) || isNaN(bounds.south) || isNaN(bounds.east) || isNaN(bounds.west)) {
      console.warn("Invalid bounds found, using default center");
      return [-22.0, 114.0];
    }
    
    const centerLat = (bounds.north + bounds.south) / 2;
    const centerLon = (bounds.east + bounds.west) / 2;
    return [centerLat, centerLon];
  }, [mapData]);

  const mapBounds = useMemo(() => {
    if (!mapData) return undefined;

    const { bounds } = mapData;
    
    // Check for valid bounds
    if (isNaN(bounds.north) || isNaN(bounds.south) || isNaN(bounds.east) || isNaN(bounds.west)) {
      return undefined;
    }
    
    return [
      [bounds.south, bounds.west],
      [bounds.north, bounds.east],
    ];
  }, [mapData]);

  if (isLoading) {
    return (
      <div className="h-96 bg-slate-100 rounded-lg flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div
        className={`relative ${
          isFullscreen ? "h-full" : "h-96"
        } rounded-lg overflow-hidden`}
        style={{
          background: `
          radial-gradient(ellipse at 20% 30%, #0a1a2e 0%, #16213e 40%, #1e3a8a 80%, #3b82f6 100%),
          linear-gradient(135deg, #0f172a 0%, #1e3a8a 30%, #3b82f6 60%, #60a5fa 100%)
        `,
          backgroundBlendMode: "multiply, normal",
        }}
      >
        <div className="h-full flex items-center justify-center">
          <div className="text-center text-white/80">
            <div className="text-lg font-medium mb-2">Interactive Map Error</div>
            <div className="text-sm opacity-75 mb-4">{error}</div>
            <Button
              onClick={loadMapData}
              variant="outline"
              size="sm"
              className="bg-white/20 backdrop-blur text-white border-white/30 hover:bg-white/30"
            >
              <RotateCcw className="h-4 w-4 mr-2" />
              Retry
            </Button>
          </div>
        </div>
      </div>
    );
  }

  if (!mapData || !satelliteMapping) {
    return (
      <div
        className={`relative ${
          isFullscreen ? "h-full" : "h-96"
        } rounded-lg overflow-hidden`}
        style={{
          background: `
          radial-gradient(ellipse at 20% 30%, #0a1a2e 0%, #16213e 40%, #1e3a8a 80%, #3b82f6 100%),
          linear-gradient(135deg, #0f172a 0%, #1e3a8a 30%, #3b82f6 60%, #60a5fa 100%)
        `,
          backgroundBlendMode: "multiply, normal",
        }}
      >
        <div className="h-full flex items-center justify-center">
          <div className="text-center text-white/80">
            <div className="text-lg font-medium mb-2">Interactive Map</div>
            <div className="text-sm opacity-75">
              {satelliteMapping
                ? "No data available for selected time"
                : "Parameter not supported for interactive mapping"}
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      className={`relative ${
        isFullscreen ? "h-full" : "h-96"
      } rounded-lg overflow-hidden`}
    >
      {/* 参数信息覆盖层 */}
      <div className="absolute top-4 left-4 flex flex-col gap-2 max-w-xs z-[1000]">
        <Badge className="bg-white/20 backdrop-blur text-white border-white/30 whitespace-nowrap">
          <div className="flex items-center gap-1">
            <Globe className="h-3 w-3" />
            <span className="truncate">Interactive Map</span>
          </div>
        </Badge>
        <Badge className="bg-white/20 backdrop-blur text-white border-white/30 whitespace-nowrap">
          <div className="flex items-center gap-1">
            {currentParam?.icon}
            <span className="truncate">{currentParam?.name}</span>
          </div>
        </Badge>
        <Badge className="bg-white/20 backdrop-blur text-white border-white/30 whitespace-nowrap">
          <div className="text-xs truncate">
            {timeRange.start.toLocaleString()}
          </div>
        </Badge>

        {/* 地图信息按钮 */}
        <Dialog open={isInfoDialogOpen} onOpenChange={setIsInfoDialogOpen}>
          <DialogTrigger asChild>
            <Button
              variant="outline"
              size="sm"
              className="bg-white/20 backdrop-blur text-white border-white/30 hover:bg-white/30 w-fit"
              title="View map information"
            >
              <Info className="h-3 w-3 mr-1" />
              Map Info
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle>Interactive Map Information</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <div className="space-y-3">
                <div>
                  <label className="text-sm font-medium text-gray-700">
                    Parameter
                  </label>
                  <div className="mt-1 p-2 bg-gray-50 rounded border text-sm">
                    {currentParam?.name} ({mapData.statistics.units})
                  </div>
                </div>

                <div>
                  <label className="text-sm font-medium text-gray-700">
                    Data Statistics
                  </label>
                  <div className="mt-1 p-2 bg-gray-50 rounded border text-sm space-y-1">
                    <div>Min: {mapData.statistics.min.toFixed(3)} {mapData.statistics.units}</div>
                    <div>Max: {mapData.statistics.max.toFixed(3)} {mapData.statistics.units}</div>
                    <div>Mean: {mapData.statistics.mean.toFixed(3)} {mapData.statistics.units}</div>
                    <div>Data Points: {mapData.statistics.count.toLocaleString()}</div>
                  </div>
                </div>

                <div>
                  <label className="text-sm font-medium text-gray-700">
                    Map Coverage
                  </label>
                  <div className="mt-1 p-2 bg-gray-50 rounded border text-sm space-y-1">
                    <div>North: {mapData.bounds.north.toFixed(3)}°</div>
                    <div>South: {mapData.bounds.south.toFixed(3)}°</div>
                    <div>East: {mapData.bounds.east.toFixed(3)}°</div>
                    <div>West: {mapData.bounds.west.toFixed(3)}°</div>
                  </div>
                </div>

                {mapData.metadata.downsampled && (
                  <div className="p-3 bg-blue-50 rounded border border-blue-200">
                    <p className="text-xs text-blue-700 font-medium mb-1">
                      Performance Note:
                    </p>
                    <div className="text-xs text-blue-600 space-y-1">
                      <p>Data downsampled for performance</p>
                      <p>Factor: {mapData.metadata.downsample_factor}x</p>
                      <p>
                        Original: {mapData.metadata.original_size.toLocaleString()} points
                      </p>
                      <p>
                        Displayed: {mapData.metadata.processed_size.toLocaleString()} points
                      </p>
                    </div>
                  </div>
                )}
              </div>

              <div className="flex justify-end">
                <Button
                  variant="outline"
                  onClick={() => setIsInfoDialogOpen(false)}
                >
                  Close
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {/* Live 指示器 */}
      <div className="absolute top-4 right-16 z-[1000]">
        <Badge className="bg-green-500/20 backdrop-blur text-green-100 border-green-400/30 animate-pulse">
          <Zap className="h-3 w-3 mr-1" />
          Interactive
        </Badge>
      </div>

      {/* Leaflet 地图 */}
      <MapContainer
        center={mapCenter as [number, number]}
        zoom={8}
        bounds={mapBounds as [[number, number], [number, number]]}
        style={{ height: "100%", width: "100%" }}
        scrollWheelZoom={true}
        className="rounded-lg"
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        
        {/* 渲染数据点 */}
        {mapData.data_points.map((point, index) => {
          const color = getColorForValue(
            point.value,
            mapData.statistics.min,
            mapData.statistics.max,
            parameter
          );
          
          return (
            <CircleMarker
              key={index}
              center={[point.lat, point.lon]}
              radius={3}
              fillColor={color}
              color="transparent"
              fillOpacity={0.7}
              weight={0}
            >
              <Popup>
                <div className="text-sm">
                  <div className="font-medium">{currentParam?.name}</div>
                  <div>Value: {point.value.toFixed(3)} {mapData.statistics.units}</div>
                  <div>Lat: {point.lat.toFixed(4)}°</div>
                  <div>Lon: {point.lon.toFixed(4)}°</div>
                </div>
              </Popup>
            </CircleMarker>
          );
        })}
      </MapContainer>
    </div>
  );
}



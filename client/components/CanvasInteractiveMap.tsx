"use client";

import { useState, useEffect, useMemo, useCallback, useRef } from "react";
import dynamic from "next/dynamic";
import { Parameter, TimeRange } from "@/types/research";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { MapPin, Zap, Settings, RotateCcw, Info, Globe } from "lucide-react";

// Dynamic import to avoid SSR issues with Leaflet
const MapContainer = dynamic(
  () => import("react-leaflet").then((mod) => mod.MapContainer),
  { ssr: false }
);
const TileLayer = dynamic(
  () => import("react-leaflet").then((mod) => mod.TileLayer),
  { ssr: false }
);
const useMapEvents = dynamic(
  () => import("react-leaflet").then((mod) => mod.useMapEvents),
  { ssr: false }
);
const useMap = dynamic(
  () => import("react-leaflet").then((mod) => mod.useMap),
  { ssr: false }
);
const ImageOverlay = dynamic(
  () => import("react-leaflet").then((mod) => mod.ImageOverlay),
  { ssr: false }
);

interface CanvasInteractiveMapProps {
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

interface SimpleNCData {
  data: (number | null)[][];
  lons: number[];
  lats: number[];
  min_value: number;
  max_value: number;
  mean_value: number;
  units: string;
  shape: [number, number];
  satellite: string;
  parameter: string;
  filename: string;
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
};

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
    default:
      return "20250923_211031.nc";
  }
};

// Turbo 色彩映射函数 - 匹配matplotlib的turbo colormap
const getTurboColor = (
  value: number,
  min: number,
  max: number
): [number, number, number] => {
  const normalized = Math.max(0, Math.min(1, (value - min) / (max - min)));

  // Turbo colormap的RGB值（简化版本，与matplotlib的turbo接近）
  const turboColors = [
    [0.18995, 0.07176, 0.23217], // 深紫
    [0.25107, 0.25237, 0.63374], // 蓝紫
    [0.19308, 0.42742, 0.81005], // 蓝色
    [0.15844, 0.5781, 0.83226], // 青蓝
    [0.17423, 0.71895, 0.7913], // 青色
    [0.25862, 0.8359, 0.67178], // 青绿
    [0.42956, 0.91471, 0.47662], // 绿色
    [0.64362, 0.94276, 0.23267], // 黄绿
    [0.86581, 0.86482, 0.01048], // 黄色
    [0.98517, 0.64499, 0.0163], // 橙色
    [0.95593, 0.39466, 0.13098], // 橙红
    [0.84071, 0.18056, 0.18024], // 红色
  ];

  // 插值计算
  const segments = turboColors.length - 1;
  const segment = Math.floor(normalized * segments);
  const t = normalized * segments - segment;

  const idx1 = Math.min(segment, segments - 1);
  const idx2 = Math.min(segment + 1, segments);

  const color1 = turboColors[idx1];
  const color2 = turboColors[idx2];

  const r = Math.round((color1[0] + (color2[0] - color1[0]) * t) * 255);
  const g = Math.round((color1[1] + (color2[1] - color1[1]) * t) * 255);
  const b = Math.round((color1[2] + (color2[2] - color1[2]) * t) * 255);

  return [r, g, b];
};

// Viridis 色彩映射函数 - 匹配matplotlib的viridis colormap
const getViridisColor = (
  value: number,
  min: number,
  max: number
): [number, number, number] => {
  const normalized = Math.max(0, Math.min(1, (value - min) / (max - min)));

  const viridisColors = [
    [0.267004, 0.004874, 0.329415], // 深紫
    [0.282623, 0.140926, 0.457517], // 紫色
    [0.253935, 0.265254, 0.529983], // 蓝紫
    [0.206756, 0.371758, 0.553117], // 蓝色
    [0.163625, 0.471133, 0.558148], // 青蓝
    [0.127568, 0.566949, 0.550556], // 青色
    [0.134692, 0.658636, 0.517649], // 青绿
    [0.266941, 0.748751, 0.440573], // 绿色
    [0.477504, 0.821444, 0.318195], // 黄绿
    [0.741388, 0.873449, 0.149561], // 黄色
  ];

  const segments = viridisColors.length - 1;
  const segment = Math.floor(normalized * segments);
  const t = normalized * segments - segment;

  const idx1 = Math.min(segment, segments - 1);
  const idx2 = Math.min(segment + 1, segments);

  const color1 = viridisColors[idx1];
  const color2 = viridisColors[idx2];

  const r = Math.round((color1[0] + (color2[0] - color1[0]) * t) * 255);
  const g = Math.round((color1[1] + (color2[1] - color1[1]) * t) * 255);
  const b = Math.round((color1[2] + (color2[2] - color1[2]) * t) * 255);

  return [r, g, b];
};

// 主颜色映射函数 - 匹配静态PNG的色彩方案
const getColorForValue = (
  value: number,
  min: number,
  max: number,
  parameter: string
): [number, number, number] => {
  if (parameter.includes("sst") || parameter === "ssth") {
    // SST使用turbo colormap（和静态PNG一样）
    return getTurboColor(value, min, max);
  } else if (parameter.includes("chl")) {
    // 叶绿素使用viridis colormap
    return getViridisColor(value, min, max);
  }

  // 默认使用turbo
  return getTurboColor(value, min, max);
};

// 这些函数不再需要，因为我们使用网格渲染而不是点扩散
// const calculateSpreadRadius = ...
// const gaussianKernel = ...

// Canvas热力图生成器组件 - 按照你的成功实现方法
function CanvasHeatmapOverlay({
  ncData,
  parameter,
  onPointHover,
}: {
  ncData: SimpleNCData;
  parameter: string;
  onPointHover: (point: DataPoint | null, x: number, y: number) => void;
}) {
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [imageBounds, setImageBounds] = useState<
    [[number, number], [number, number]] | null
  >(null);

  // 生成热力图图片的核心函数
  const generateHeatmapImage = useCallback(() => {
    if (!ncData) return;

    console.log("Generating heatmap image...");

    // 创建临时canvas
    const canvas = document.createElement("canvas");
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const { data, lats, lons, min_value, max_value } = ncData;
    const rows = data.length;
    const cols = data[0].length;

    // 根据数据密度调整Canvas大小
    const density = Math.max(1, Math.min(4, Math.sqrt((rows * cols) / 50000))); // 自动调整密度
    canvas.width = cols * density;
    canvas.height = rows * density;

    console.log(
      `Canvas size: ${canvas.width}x${canvas.height}, density: ${density}, data: ${rows}x${cols}`
    );

    // 调试数据范围
    console.log(`Data range: ${min_value} to ${max_value} ${ncData.units}`);
    console.log(`Lat range: ${Math.min(...lats)} to ${Math.max(...lats)}`);
    console.log(`Lon range: ${Math.min(...lons)} to ${Math.max(...lons)}`);
    console.log(
      `Data file: ${ncData.filename} (${ncData.satellite}/${ncData.parameter})`
    );

    // 清空画布
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    let validCells = 0;

    // 遍历数据并绘制像素块 - 匹配pcolormesh(LON, LAT, data)的索引方式
    for (let i = 0; i < rows; i++) {
      for (let j = 0; j < cols; j++) {
        const value = data[i][j];
        if (value === null || isNaN(value)) continue;

        validCells++;

        // 获取颜色 - 使用和静态图一样的色调映射
        const [r, g, b] = getColorForValue(
          value,
          min_value,
          max_value,
          parameter
        );

        ctx.fillStyle = `rgb(${r}, ${g}, ${b})`;

        // 绘制像素块 - 注意：Canvas的y轴是从上到下，需要翻转
        // pcolormesh的数据矩阵：data[i][j] 对应 lat[i], lon[j]
        const x = j * density;
        const y = (rows - 1 - i) * density; // 翻转Y轴以匹配地理坐标
        ctx.fillRect(x, y, density, density);
      }
    }

    console.log(`Generated heatmap with ${validCells} valid cells`);

    // 转换为图片URL
    const dataUrl = canvas.toDataURL("image/png");
    setImageUrl(dataUrl);

    // 计算地理边界
    const minLat = Math.min(...lats);
    const maxLat = Math.max(...lats);
    const minLon = Math.min(...lons);
    const maxLon = Math.max(...lons);

    setImageBounds([
      [minLat, minLon],
      [maxLat, maxLon],
    ]);

    console.log(
      `Image bounds: lat(${minLat}, ${maxLat}), lon(${minLon}, ${maxLon})`
    );
  }, [ncData, parameter]);

  // 当数据改变时生成新的热力图
  useEffect(() => {
    generateHeatmapImage();
  }, [generateHeatmapImage]);

  // 地图事件监听器 - 用于交互
  function MapEventHandler() {
    useMapEvents({
      click: (e) => {
        // 处理点击事件，查找最近的数据点
        if (!ncData) return;

        const { data, lats, lons } = ncData;
        const clickLat = e.latlng.lat;
        const clickLon = e.latlng.lng;

        let closestPoint: DataPoint | null = null;
        let minDistance = Infinity;

        for (let i = 0; i < data.length; i++) {
          for (let j = 0; j < data[0].length; j++) {
            const value = data[i][j];
            if (value === null || isNaN(value)) continue;

            const lat = lats[i];
            const lon = lons[j];
            const distance = Math.sqrt(
              Math.pow(lat - clickLat, 2) + Math.pow(lon - clickLon, 2)
            );

            if (distance < minDistance) {
              minDistance = distance;
              closestPoint = { lat, lon, value };
            }
          }
        }

        if (closestPoint && minDistance < 0.1) {
          // 点击阈值
          console.log("Clicked data point:", closestPoint);
          onPointHover(closestPoint, e.containerPoint.x, e.containerPoint.y);
        }
      },
    });

    return null;
  }

  if (!imageUrl || !imageBounds) {
    return <MapEventHandler />;
  }

  return (
    <>
      <MapEventHandler />
      <ImageOverlay
        url={imageUrl}
        bounds={imageBounds}
        opacity={0.7}
        interactive={false}
      />
    </>
  );
}

export function CanvasInteractiveMap({
  parameter,
  timeRange,
  availableParameters,
  isFullscreen,
  getParameterFiles,
}: CanvasInteractiveMapProps): JSX.Element {
  const [ncData, setNCData] = useState<SimpleNCData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isInfoDialogOpen, setIsInfoDialogOpen] = useState(false);
  const [hoveredPoint, setHoveredPoint] = useState<DataPoint | null>(null);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });

  const currentParam = availableParameters.find((p) => p.id === parameter);
  const satelliteMapping =
    SATELLITE_MAPPING[parameter as keyof typeof SATELLITE_MAPPING];

  // 获取当前时间戳和文件名 (与之前相同的逻辑)
  const currentTimestamp = useMemo(() => {
    if (!satelliteMapping) return null;

    // all 模式不生成时间戳
    if (timeRange.granularity === "all") {
      return null;
    }

    const utcDate = new Date(timeRange.start.getTime());
    utcDate.setUTCMinutes(0, 0, 0);

    if (parameter === "ssth") {
      const year = utcDate.getUTCFullYear();
      const month = String(utcDate.getUTCMonth() + 1).padStart(2, "0");
      const day = String(utcDate.getUTCDate()).padStart(2, "0");
      const hour = String(utcDate.getUTCHours()).padStart(2, "0");
      return `${year}${month}${day}${hour}0000`;
    } else {
      const year = utcDate.getUTCFullYear();
      const month = String(utcDate.getUTCMonth() + 1).padStart(2, "0");
      const day = String(utcDate.getUTCDate()).padStart(2, "0");
      const hour = String(utcDate.getUTCHours()).padStart(2, "0");
      const minute = String(utcDate.getUTCMinutes()).padStart(2, "0");
      const second = String(utcDate.getUTCSeconds()).padStart(2, "0");
      return `${year}${month}${day}_${hour}${minute}${second}`;
    }
  }, [parameter, timeRange.start, timeRange.granularity, satelliteMapping]);

  const getNcFilename = useCallback(async (): Promise<string | null> => {
    if (!satelliteMapping || !getParameterFiles) return null;

    try {
      if (parameter === "ssth") {
        return `${currentTimestamp}.nc`;
      } else {
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

  // 加载地图数据 (与之前相同的逻辑)
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

      const targetTime =
        timeRange.granularity === "all" ? "all" : timeRange.start.toISOString();
      let apiUrl = `http://localhost:8000/api/v1/satellites/${
        satelliteMapping.satellite
      }/${
        satelliteMapping.parameter
      }/simple-data/${ncFilename}?target_time=${encodeURIComponent(
        targetTime
      )}&mode=${encodeURIComponent(timeRange.granularity)}`;

      // 如果是all模式，添加时间范围参数
      if (timeRange.granularity === "all") {
        apiUrl += `&start_time=${encodeURIComponent(
          timeRange.start.toISOString()
        )}&end_time=${encodeURIComponent(timeRange.end.toISOString())}`;
      }

      console.log(
        `Loading simple data for canvas from: ${apiUrl} (Sentinel-3 will use closest time <= target)`
      );

      const response = await fetch(apiUrl);
      if (!response.ok) {
        throw new Error(`Failed to load map data: ${response.statusText}`);
      }

      const data = await response.json();
      setNCData(data);
      console.log("Simple NC data loaded:", data);
    } catch (error) {
      console.error("Error loading canvas map data:", error);
      setError(
        error instanceof Error ? error.message : "Failed to load map data"
      );
    } finally {
      setIsLoading(false);
    }
  }, [satelliteMapping, getNcFilename, timeRange.start]);

  useEffect(() => {
    loadMapData();
  }, [loadMapData]);

  // 计算地图中心和边界
  const mapCenter = useMemo(() => {
    if (!ncData) return [-22.0, 114.0];
    const minLat = Math.min(...ncData.lats);
    const maxLat = Math.max(...ncData.lats);
    const minLon = Math.min(...ncData.lons);
    const maxLon = Math.max(...ncData.lons);
    const centerLat = (minLat + maxLat) / 2;
    const centerLon = (minLon + maxLon) / 2;
    console.log(
      `Map center: [${centerLat}, ${centerLon}], bounds: lat(${minLat}, ${maxLat}), lon(${minLon}, ${maxLon})`
    );
    return [centerLat, centerLon];
  }, [ncData]);

  const mapBounds = useMemo(() => {
    if (!ncData) return undefined;
    const minLat = Math.min(...ncData.lats);
    const maxLat = Math.max(...ncData.lats);
    const minLon = Math.min(...ncData.lons);
    const maxLon = Math.max(...ncData.lons);
    return [
      [minLat, minLon],
      [maxLat, maxLon],
    ];
  }, [ncData]);

  const handlePointHover = useCallback(
    (point: DataPoint | null, x: number, y: number) => {
      setHoveredPoint(point);
      setTooltipPos({ x, y });
    },
    []
  );

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
            <div className="text-lg font-medium mb-2">Canvas Map Error</div>
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

  if (!ncData || !satelliteMapping) {
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
            <div className="text-lg font-medium mb-2">
              Canvas Interactive Map
            </div>
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
            <span className="truncate">Canvas Heatmap</span>
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
            {timeRange.end.toLocaleString("en-US", {
              timeZone: "UTC",
              year: "numeric",
              month: "2-digit",
              day: "2-digit",
              hour: "2-digit",
              minute: "2-digit",
              second: "2-digit",
              hour12: false,
            })}
          </div>
        </Badge>

        {/* 地图信息按钮 */}
        <Dialog open={isInfoDialogOpen} onOpenChange={setIsInfoDialogOpen}>
          <DialogTrigger asChild>
            <Button
              variant="outline"
              size="sm"
              className="bg-white/20 backdrop-blur text-white border-white/30 hover:bg-white/30 w-fit"
              title="View canvas map information"
            >
              <Info className="h-3 w-3 mr-1" />
              Canvas Info
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle>Canvas Heatmap Information</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <div className="space-y-3">
                <div>
                  <label className="text-sm font-medium text-gray-700">
                    Rendering Method
                  </label>
                  <div className="mt-1 p-2 bg-gray-50 rounded border text-sm">
                    Canvas → ImageURL → ImageOverlay
                  </div>
                </div>

                <div>
                  <label className="text-sm font-medium text-gray-700">
                    Parameter
                  </label>
                  <div className="mt-1 p-2 bg-gray-50 rounded border text-sm">
                    {currentParam?.name} ({ncData.units})
                  </div>
                </div>

                <div>
                  <label className="text-sm font-medium text-gray-700">
                    Data Statistics
                  </label>
                  <div className="mt-1 p-2 bg-gray-50 rounded border text-sm space-y-1">
                    <div>
                      Min: {ncData.min_value.toFixed(3)} {ncData.units}
                    </div>
                    <div>
                      Max: {ncData.max_value.toFixed(3)} {ncData.units}
                    </div>
                    <div>
                      Mean: {ncData.mean_value.toFixed(3)} {ncData.units}
                    </div>
                    <div>
                      Total Pixels:{" "}
                      {(ncData.shape[0] * ncData.shape[1]).toLocaleString()}
                    </div>
                  </div>
                </div>

                <div>
                  <label className="text-sm font-medium text-gray-700">
                    Grid Information
                  </label>
                  <div className="mt-1 p-2 bg-gray-50 rounded border text-sm space-y-1">
                    <div>Data Source: Direct NC file read</div>
                    <div>
                      Data Size: {ncData.shape[0]} × {ncData.shape[1]}
                    </div>
                    <div>
                      Coordinate Arrays: {ncData.lats.length} latitudes,{" "}
                      {ncData.lons.length} longitudes
                    </div>
                  </div>
                </div>

                <div className="p-3 bg-green-50 rounded border border-green-200">
                  <p className="text-xs text-green-700 font-medium mb-1">
                    Rendering Method:
                  </p>
                  <div className="text-xs text-green-600 space-y-1">
                    <p>Temporary Canvas → toDataURL → ImageOverlay</p>
                    <p>Automatic density adjustment</p>
                    <p>Same color mapping as static PNG</p>
                    <p>True map coordinate integration</p>
                  </div>
                </div>
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
        <Badge className="bg-purple-500/20 backdrop-blur text-purple-100 border-purple-400/30 animate-pulse">
          <Zap className="h-3 w-3 mr-1" />
          Canvas Heatmap
        </Badge>
      </div>

      {/* Tooltip */}
      {hoveredPoint && (
        <div
          className="absolute z-[1001] pointer-events-none"
          style={{
            left: tooltipPos.x + 10,
            top: tooltipPos.y - 10,
          }}
        >
          <div className="bg-black/80 text-white text-xs p-2 rounded shadow-lg">
            <div className="font-medium">{currentParam?.name}</div>
            <div>
              Value: {hoveredPoint.value.toFixed(3)} {ncData.units}
            </div>
            <div>Lat: {hoveredPoint.lat.toFixed(4)}°</div>
            <div>Lon: {hoveredPoint.lon.toFixed(4)}°</div>
          </div>
        </div>
      )}

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

        {/* Canvas热力图叠加层 */}
        <CanvasHeatmapOverlay
          ncData={ncData}
          parameter={parameter}
          onPointHover={handlePointHover}
        />
      </MapContainer>
    </div>
  );
}

"use client";

import { useState, useEffect, useMemo } from "react";
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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  MapPin,
  Layers,
  Zap,
  Image as ImageIcon,
  Settings,
} from "lucide-react";
import { useDataStore } from "@/hooks/useDataStore";

interface ResearchMapProps {
  parameter: string;
  timeRange: TimeRange;
  availableParameters: Parameter[];
  isFullscreen?: boolean;
  getParameterFiles?: (
    paramId: string,
    fileType: "nc" | "png"
  ) => Promise<any[]>;
  range?: {
    min: string;
    max: string;
    appliedMin: string;
    appliedMax: string;
  };
  onRangeUpdate?: (parameter: string, min: string, max: string) => void;
  onRangeApply?: (
    parameter: string,
    appliedMin: string,
    appliedMax: string
  ) => void;
  onRangeReset?: (parameter: string) => void;
}

// 卫星参数映射 - 更新为统一数据结构
const SATELLITE_MAPPING = {
  ssth: {
    satellite: "himawari",
    parameter: "sst",
    staticPath: "/static/himawari/sst/png",
  },
  "sst-s3a": {
    satellite: "sentinel3a",
    parameter: "sst",
    staticPath: "/static/sentinel3a/sst/png",
  },
  "sst-s3b": {
    satellite: "sentinel3b",
    parameter: "sst",
    staticPath: "/static/sentinel3b/sst/png",
  },
  "chl-s3a": {
    satellite: "sentinel3a",
    parameter: "chl",
    staticPath: "/static/sentinel3a/chl/png",
  },
  "chl-s3b": {
    satellite: "sentinel3b",
    parameter: "chl",
    staticPath: "/static/sentinel3b/chl/png",
  },
};

// 辅助函数：获取参数值的占位符（仅作为fallback）
const getPlaceholderValue = (param: string, type: "min" | "max"): string => {
  switch (param) {
    case "ssth":
      return type === "min" ? "290" : "310"; // SST in Kelvin
    case "sst-s3a":
    case "sst-s3b":
      return type === "min" ? "15" : "35"; // SST in Celsius
    case "chl-s3a":
    case "chl-s3b":
      return type === "min" ? "0.01" : "10"; // Chl in mg/m³
    default:
      return type === "min" ? "0" : "100";
  }
};

// 辅助函数：获取实际的数据范围（优先使用API数据）
const getDataRange = (
  param: string,
  type: "min" | "max",
  dataStats: any
): string => {
  if (dataStats && dataStats[type] !== undefined) {
    return dataStats[type].toFixed(2);
  }
  return getPlaceholderValue(param, type);
};

// 辅助函数：获取参数的典型范围
const getTypicalRange = (param: string): string => {
  switch (param) {
    case "ssth":
      return "290-310 K (Sea Surface Temperature)";
    case "sst-s3a":
    case "sst-s3b":
      return "15-35°C (Sea Surface Temperature)";
    case "chl-s3a":
    case "chl-s3b":
      return "0.01-10 mg/m³ (Chlorophyll-a)";
    default:
      return "Check parameter documentation";
  }
};

export function ResearchMap({
  parameter,
  timeRange,
  availableParameters,
  isFullscreen,
  getParameterFiles,
  range,
  onRangeUpdate,
  onRangeApply,
  onRangeReset,
}: ResearchMapProps): JSX.Element {
  // Use props for range state, fallback to local state for backward compatibility
  const parameterMin = range?.min || "";
  const parameterMax = range?.max || "";
  const appliedMin = range?.appliedMin || "";
  const appliedMax = range?.appliedMax || "";

  // Local state for dialog inputs (temporary values before applying)
  const [tempMin, setTempMin] = useState<string>("");
  const [tempMax, setTempMax] = useState<string>("");
  const [isRangeDialogOpen, setIsRangeDialogOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [filteredImageUrl, setFilteredImageUrl] = useState<string | null>(null);
  const [imageError, setImageError] = useState(false);
  const [availableFiles, setAvailableFiles] = useState<any[]>([]);
  const [dataStats, setDataStats] = useState<{
    min: number;
    max: number;
    mean: number;
    units: string;
  } | null>(null);
  const [isLoadingStats, setIsLoadingStats] = useState(false);
  const [isGeneratingFilteredImage, setIsGeneratingFilteredImage] =
    useState(false);

  // 如果没有传入getParameterFiles，则使用useDataStore（向后兼容）
  const dataStore = !getParameterFiles ? useDataStore() : null;
  const getFiles = getParameterFiles || dataStore?.getParameterFiles;

  const currentParam = availableParameters.find((p) => p.id === parameter);
  const satelliteMapping =
    SATELLITE_MAPPING[parameter as keyof typeof SATELLITE_MAPPING];

  // 获取当前时间戳和文件名
  const currentTimestamp = useMemo(() => {
    if (!satelliteMapping) return null;

    // Ensure UTC time and round down to the nearest hour
    const utcDate = new Date(timeRange.start.getTime());
    utcDate.setUTCMinutes(0, 0, 0);

    // 不同卫星使用不同的时间戳格式
    if (parameter === "ssth") {
      // Himawari格式: YYYYMMDDHHMMSS
      const year = utcDate.getUTCFullYear();
      const month = String(utcDate.getUTCMonth() + 1).padStart(2, "0");
      const day = String(utcDate.getUTCDate()).padStart(2, "0");
      const hour = String(utcDate.getUTCHours()).padStart(2, "0");
      return `${year}${month}${day}${hour}0000`;
    } else {
      // Sentinel-3格式: YYYYMMDD_HHMMSS格式用于匹配
      const year = utcDate.getUTCFullYear();
      const month = String(utcDate.getUTCMonth() + 1).padStart(2, "0");
      const day = String(utcDate.getUTCDate()).padStart(2, "0");
      const hour = String(utcDate.getUTCHours()).padStart(2, "0");
      const minute = String(utcDate.getUTCMinutes()).padStart(2, "0");
      const second = String(utcDate.getUTCSeconds()).padStart(2, "0");
      return `${year}${month}${day}_${hour}${minute}${second}`;
    }
  }, [parameter, timeRange.start, satelliteMapping]);

  // Sync temp values with current range when dialog opens
  useEffect(() => {
    if (isRangeDialogOpen) {
      setTempMin(parameterMin);
      setTempMax(parameterMax);
    }
  }, [isRangeDialogOpen, parameterMin, parameterMax]);

  // Generate filtered image when range changes
  useEffect(() => {
    console.log(`Range effect triggered for ${parameter}:`, {
      appliedMin,
      appliedMax,
      availableFiles: availableFiles.length,
      currentTimestamp,
    });

    if (appliedMin || appliedMax) {
      // Only generate filtered image if we have a current file and range is applied
      if (availableFiles.length > 0 && currentTimestamp) {
        const currentFile = findBestFileForTime(
          availableFiles,
          timeRange.start
        );

        if (currentFile) {
          // 根据参数类型选择正确的NC文件名
          let ncFilename;
          if (parameter === "ssth") {
            ncFilename = currentFile.filename.replace(".png", ".nc");
          } else {
            // 对于Sentinel-3，根据参数类型选择正确的NC文件名
            if (parameter === "sst-s3a" || parameter === "sst-s3b") {
              ncFilename = "20250910_145048.nc"; // SST NC文件
            } else if (parameter === "chl-s3a" || parameter === "chl-s3b") {
              ncFilename = "20250910_145052.nc"; // Chl NC文件
            } else {
              ncFilename = "20250910_145048.nc"; // 默认SST文件
            }
          }

          const minNum = appliedMin ? parseFloat(appliedMin) : undefined;
          const maxNum = appliedMax ? parseFloat(appliedMax) : undefined;
          console.log(
            `Generating filtered image for ${parameter} with range:`,
            { minNum, maxNum, ncFilename }
          );
          generateFilteredImage(ncFilename, minNum, maxNum);
        }
      }
    } else {
      // Clear filtered image if no range is applied
      console.log(`Clearing filtered image for ${parameter}`);
      setFilteredImageUrl(null);
    }
  }, [appliedMin, appliedMax, availableFiles, currentTimestamp, parameter]);

  // 获取数据统计信息的函数
  const fetchDataStats = async (filename: string, targetTime?: string) => {
    if (!satelliteMapping) return;

    setIsLoadingStats(true);
    try {
      // 构建API URL，包含target_time参数
      let apiUrl = `http://localhost:8000/api/v1/satellites/${satelliteMapping.satellite}/${satelliteMapping.parameter}/stats/${filename}`;
      if (targetTime) {
        apiUrl += `?target_time=${encodeURIComponent(targetTime)}`;
      }

      const response = await fetch(apiUrl);

      if (response.ok) {
        const stats = await response.json();
        setDataStats({
          min: stats.min,
          max: stats.max,
          mean: stats.mean,
          units: stats.units,
        });
        console.log(`Data stats for ${filename}:`, stats);
      } else {
        console.warn(
          `Failed to get data stats for ${filename}:`,
          response.statusText
        );
      }
    } catch (error) {
      console.error(`Error fetching data stats for ${filename}:`, error);
    } finally {
      setIsLoadingStats(false);
    }
  };

  // 生成过滤图片的函数
  const generateFilteredImage = async (
    filename: string,
    minValue?: number,
    maxValue?: number
  ) => {
    if (!satelliteMapping) return;

    setIsGeneratingFilteredImage(true);
    try {
      const params = new URLSearchParams();
      if (minValue !== undefined)
        params.append("min_value", minValue.toString());
      if (maxValue !== undefined)
        params.append("max_value", maxValue.toString());

      // 添加target_time参数用于Sentinel-3
      const targetTime = timeRange.start.toISOString();
      params.append("target_time", targetTime);

      const response = await fetch(
        `http://localhost:8000/api/v1/satellites/${
          satelliteMapping.satellite
        }/${
          satelliteMapping.parameter
        }/filtered-image/${filename}?${params.toString()}`
      );

      if (response.ok) {
        const result = await response.json();
        setFilteredImageUrl(result.image);
        console.log(`Generated filtered image for ${filename}:`, result);
      } else {
        console.warn(
          `Failed to generate filtered image for ${filename}:`,
          response.statusText
        );
        setFilteredImageUrl(null);
      }
    } catch (error) {
      console.error(`Error generating filtered image for ${filename}:`, error);
      setFilteredImageUrl(null);
    } finally {
      setIsGeneratingFilteredImage(false);
    }
  };

  // 获取可用文件列表
  useEffect(() => {
    if (satelliteMapping && getFiles) {
      getFiles(parameter, "png").then((files) => {
        setAvailableFiles(files);
        console.log(`Available PNG files for ${parameter}:`, files);
        console.log(`Current timestamp: ${currentTimestamp}`);
      });
    }
  }, [parameter, satelliteMapping, getFiles, currentTimestamp]);

  // 辅助函数：从Sentinel-3文件名提取时间
  const extractTimeFromSentinel3Filename = (filename: string): Date | null => {
    // Sentinel-3 PNG文件格式: YYYYMMDD_HHMMSS.png
    const timeMatch = filename.match(/(\d{8})_(\d{6})\.png$/);
    if (timeMatch) {
      const dateStr = timeMatch[1]; // YYYYMMDD
      const timeStr = timeMatch[2]; // HHMMSS

      const year = dateStr.substring(0, 4);
      const month = dateStr.substring(4, 6);
      const day = dateStr.substring(6, 8);
      const hour = timeStr.substring(0, 2);
      const minute = timeStr.substring(2, 4);
      const second = timeStr.substring(4, 6);

      return new Date(`${year}-${month}-${day}T${hour}:${minute}:${second}Z`);
    }
    return null;
  };

  // 通用文件查找函数：根据时间查找最合适的文件
  const findBestFileForTime = (files: any[], selectedTime: Date) => {
    if (parameter === "ssth") {
      // Himawari 文件查找 - 查找包含时间戳的文件
      return files.find(
        (file) => file.filename && file.filename.startsWith(currentTimestamp)
      );
    } else {
      // Sentinel-3 文件查找 - 寻找选中时间点之前最近的那张图
      let bestFile = null;
      let bestTimeDiff = Infinity;

      for (const file of files) {
        const fileTime = extractTimeFromSentinel3Filename(file.filename);
        if (fileTime && fileTime.getTime() <= selectedTime.getTime()) {
          const timeDiff = selectedTime.getTime() - fileTime.getTime();
          if (timeDiff < bestTimeDiff) {
            bestTimeDiff = timeDiff;
            bestFile = file;
          }
        }
      }
      return bestFile;
    }
  };

  useEffect(() => {
    if (satelliteMapping && currentTimestamp && availableFiles.length > 0) {
      // 寻找最匹配的文件
      let targetFile: any = null;

      // 使用通用文件查找函数
      targetFile = findBestFileForTime(availableFiles, timeRange.start);

      console.log(`Looking for file with timestamp: ${currentTimestamp}`);
      console.log(
        `Available files:`,
        availableFiles.map((f) => f.filename)
      );

      if (targetFile) {
        const pngUrl = `http://localhost:8000${targetFile.url}`;

        // 获取对应的NC文件名来获取数据统计信息（移到条件判断之前）
        let ncFilename;
        if (parameter === "ssth") {
          ncFilename = targetFile.filename.replace(".png", ".nc");
        } else {
          // 对于Sentinel-3，根据参数类型选择正确的NC文件名
          if (parameter === "sst-s3a" || parameter === "sst-s3b") {
            ncFilename = "20250910_145048.nc"; // SST NC文件
          } else if (parameter === "chl-s3a" || parameter === "chl-s3b") {
            ncFilename = "20250910_145052.nc"; // Chl NC文件
          } else {
            ncFilename = "20250910_145048.nc"; // 默认SST文件
          }
        }

        // 传递目标时间给API
        const targetTime = timeRange.start.toISOString();
        console.log(
          `Fetching stats for ${parameter} using NC file: ${ncFilename} at time: ${targetTime}`
        );
        fetchDataStats(ncFilename, targetTime);

        // 避免重复加载相同的图片
        if (imageUrl === pngUrl) {
          return;
        }

        setIsLoading(true);
        setImageError(false);

        console.log(`Loading ${parameter} image:`, targetFile.filename);
        console.log(`Image URL: ${pngUrl}`);

        // Check if image exists
        const img = new Image();
        img.onload = () => {
          setImageUrl(pngUrl);
          setIsLoading(false);
        };
        img.onerror = () => {
          console.warn(`PNG failed to load: ${targetFile.filename}`);
          setImageError(true);
          setImageUrl(null);
          setIsLoading(false);
        };
        img.src = pngUrl;
      } else {
        console.warn(
          `No suitable PNG file found for ${parameter} at ${currentTimestamp}`
        );
        setImageError(true);
        setImageUrl(null);
        setIsLoading(false);
      }
    } else if (satelliteMapping) {
      // 参数支持但没有可用文件
      setIsLoading(false);
      setImageUrl(null);
      setImageError(true);
    } else {
      // 不支持的参数，显示占位符
      setIsLoading(false);
      setImageUrl(null);
      setImageError(false);
    }
  }, [satelliteMapping, currentTimestamp, availableFiles, parameter, imageUrl]);

  if (isLoading) {
    return (
      <div className="h-96 bg-slate-100 rounded-lg flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

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
      {(imageUrl || filteredImageUrl) && satelliteMapping ? (
        <div
          className="absolute inset-0 w-full h-full flex items-center justify-center"
          style={{
            background: `
            radial-gradient(ellipse at center, #0a1a2e 0%, #16213e 30%, #1e3a8a 70%, #3b82f6 100%),
            linear-gradient(135deg, #0f172a 0%, #1e3a8a 50%, #3b82f6 100%)
          `,
            backgroundBlendMode: "multiply, normal",
          }}
        >
          <div className="relative w-full h-full">
            {/* Show filtered image if available, otherwise show original */}
            <img
              src={filteredImageUrl || imageUrl}
              alt={`${currentParam?.name} visualization`}
              className={`${
                isFullscreen ? "max-w-full max-h-full" : "w-full h-full"
              } object-contain rounded-lg`}
              style={{
                filter: "contrast(1.1) brightness(1.1)",
              }}
            />

            {/* Loading indicator for filtered image generation */}
            {isGeneratingFilteredImage && (
              <div className="absolute inset-0 flex items-center justify-center bg-black/50 rounded-lg">
                <div className="text-white text-center">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-white mx-auto mb-2"></div>
                  <div className="text-sm">Generating filtered image...</div>
                </div>
              </div>
            )}

            {/* Range indicator */}
            {(appliedMin || appliedMax) && dataStats && (
              <div className="absolute top-2 right-2 bg-black/50 text-white text-xs px-2 py-1 rounded">
                Range: {appliedMin || dataStats.min.toFixed(3)} -{" "}
                {appliedMax || dataStats.max.toFixed(3)}
                {filteredImageUrl && " (Filtered)"}
              </div>
            )}
          </div>
          {/* Overlay for better text readability */}
          <div className="absolute inset-0 bg-black/10"></div>
        </div>
      ) : (
        <div className="h-full flex items-center justify-center">
          <div className="text-center text-white/80">
            <div className="text-lg font-medium mb-2">
              {satelliteMapping && imageError
                ? "Image not available"
                : `${currentParam?.name} Data`}
            </div>
            <div className="text-sm opacity-75">
              {satelliteMapping && imageError
                ? `No satellite data for ${currentTimestamp || "selected time"}`
                : satelliteMapping
                ? "Loading satellite data..."
                : "Visualization coming soon"}
            </div>
          </div>
        </div>
      )}

      {/* Parameter info overlay */}
      <div className="absolute top-4 left-4 flex flex-col gap-2 max-w-xs">
        <Badge className="bg-white/20 backdrop-blur text-white border-white/30 whitespace-nowrap">
          <div className="flex items-center gap-1">
            {currentParam?.icon}
            <span className="truncate">{currentParam?.name}</span>
          </div>
        </Badge>
        <Badge className="bg-white/20 backdrop-blur text-white border-white/30 whitespace-nowrap">
          {imageUrl && satelliteMapping ? (
            <>
              <ImageIcon className="h-3 w-3 mr-1" />
              <span className="truncate">
                {satelliteMapping.satellite.toUpperCase()} Image
              </span>
            </>
          ) : (
            <>
              <MapPin className="h-3 w-3 mr-1" />
              <span className="truncate">
                {satelliteMapping ? "No data available" : "Coming soon"}
              </span>
            </>
          )}
        </Badge>
        {imageUrl && satelliteMapping && (
          <Badge className="bg-white/20 backdrop-blur text-white border-white/30 whitespace-nowrap">
            <div className="text-xs truncate">
              {timeRange.start.toLocaleString()}
            </div>
          </Badge>
        )}

        {/* Applied Range Display */}
        {(appliedMin || appliedMax) && (
          <Badge className="bg-blue-500/20 backdrop-blur text-blue-100 border-blue-400/30 whitespace-nowrap">
            <div className="text-xs">
              Range: {appliedMin || "auto"} - {appliedMax || "auto"}
              {currentParam?.unit && ` ${currentParam.unit}`}
            </div>
          </Badge>
        )}

        {/* Parameter Value Range Selector Button */}
        <Dialog open={isRangeDialogOpen} onOpenChange={setIsRangeDialogOpen}>
          <DialogTrigger asChild>
            <Button
              variant="outline"
              size="sm"
              className="bg-white/20 backdrop-blur text-white border-white/30 hover:bg-white/30 w-fit"
            >
              <Settings className="h-3 w-3 mr-1" />
              Range
              {(appliedMin || appliedMax) && (
                <Badge className="ml-1 bg-green-500/20 text-green-100 border-green-400/30 text-xs">
                  ✓
                </Badge>
              )}
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle>Select {currentParam?.name} Range</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              {/* Parameter Range Input */}
              <div className="space-y-3">
                <h4 className="text-sm font-medium text-gray-700">
                  {currentParam?.name} Value Range
                  {currentParam?.unit && ` (${currentParam.unit})`}
                </h4>

                {/* Current Applied Range Display */}
                {(appliedMin || appliedMax) && (
                  <div className="p-2 bg-blue-50 rounded-md border border-blue-200">
                    <p className="text-xs text-blue-700 font-medium mb-1">
                      Currently Applied:
                    </p>
                    <p className="text-xs text-blue-600">
                      {appliedMin || "auto"} - {appliedMax || "auto"}
                      {currentParam?.unit && ` ${currentParam.unit}`}
                    </p>
                  </div>
                )}

                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <Label htmlFor="param-min" className="text-xs">
                      Minimum
                      {dataStats && (
                        <span className="text-gray-500 ml-1">
                          (min: {dataStats.min.toFixed(3)})
                        </span>
                      )}
                    </Label>
                    <Input
                      id="param-min"
                      type="number"
                      step="0.01"
                      placeholder={
                        dataStats
                          ? `${dataStats.min.toFixed(3)}`
                          : getPlaceholderValue(parameter, "min")
                      }
                      value={tempMin}
                      onChange={(e) => setTempMin(e.target.value)}
                      min={dataStats ? dataStats.min : undefined}
                      max={dataStats ? dataStats.max : undefined}
                      className="text-sm"
                    />
                  </div>
                  <div className="space-y-1">
                    <Label htmlFor="param-max" className="text-xs">
                      Maximum
                      {dataStats && (
                        <span className="text-gray-500 ml-1">
                          (max: {dataStats.max.toFixed(3)})
                        </span>
                      )}
                    </Label>
                    <Input
                      id="param-max"
                      type="number"
                      step="0.01"
                      placeholder={
                        dataStats
                          ? `${dataStats.max.toFixed(3)}`
                          : getPlaceholderValue(parameter, "max")
                      }
                      value={tempMax}
                      onChange={(e) => setTempMax(e.target.value)}
                      min={dataStats ? dataStats.min : undefined}
                      max={dataStats ? dataStats.max : undefined}
                      className="text-sm"
                    />
                  </div>
                </div>
              </div>

              {/* Data Statistics Display */}
              {dataStats ? (
                <div className="p-3 bg-blue-50 rounded-md border border-blue-200">
                  <p className="text-xs text-blue-700 font-medium mb-2">
                    Current Image Data Range:
                  </p>
                  <div className="text-xs text-blue-600 space-y-1">
                    <p>
                      Min: {dataStats.min.toFixed(3)} {dataStats.units}
                    </p>
                    <p>
                      Max: {dataStats.max.toFixed(3)} {dataStats.units}
                    </p>
                    <p>
                      Mean: {dataStats.mean.toFixed(3)} {dataStats.units}
                    </p>
                  </div>
                </div>
              ) : isLoadingStats ? (
                <div className="p-3 bg-gray-50 rounded-md">
                  <p className="text-xs text-gray-600">
                    Loading data statistics...
                  </p>
                </div>
              ) : (
                <div className="p-3 bg-gray-50 rounded-md">
                  <p className="text-xs text-gray-600 mb-2">
                    Typical range for {currentParam?.name}:
                  </p>
                  <div className="text-xs text-gray-500">
                    <p>{getTypicalRange(parameter)}</p>
                  </div>
                </div>
              )}

              <div className="flex justify-between">
                <div className="flex space-x-2">
                  {(appliedMin || appliedMax) && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        if (onRangeReset) {
                          onRangeReset(parameter);
                        }
                        setTempMin("");
                        setTempMax("");
                        setFilteredImageUrl(null);
                        console.log("Parameter range reset");
                      }}
                      className="text-red-600 border-red-300 hover:bg-red-50"
                    >
                      Reset
                    </Button>
                  )}
                </div>
                <div className="flex space-x-2">
                  <Button
                    variant="outline"
                    onClick={() => setIsRangeDialogOpen(false)}
                  >
                    Cancel
                  </Button>
                  <Button
                    onClick={() => {
                      // Apply the parameter range settings
                      const minValue = tempMin.trim();
                      const maxValue = tempMax.trim();

                      // Validate range values
                      if (minValue && maxValue) {
                        const minNum = parseFloat(minValue);
                        const maxNum = parseFloat(maxValue);

                        if (minNum >= maxNum) {
                          alert(
                            "Minimum value must be less than maximum value"
                          );
                          return;
                        }

                        // Validate against actual data range
                        if (dataStats) {
                          if (minNum < dataStats.min) {
                            alert(
                              `Minimum value (${minNum}) cannot be less than data minimum (${dataStats.min.toFixed(
                                3
                              )})`
                            );
                            return;
                          }
                          if (maxNum > dataStats.max) {
                            alert(
                              `Maximum value (${maxNum}) cannot be greater than data maximum (${dataStats.max.toFixed(
                                3
                              )})`
                            );
                            return;
                          }
                        }
                      }

                      // Update the global range state
                      if (onRangeUpdate) {
                        onRangeUpdate(parameter, minValue, maxValue);
                      }
                      if (onRangeApply) {
                        onRangeApply(parameter, minValue, maxValue);
                      }

                      console.log("Parameter range applied:", {
                        parameter: currentParam?.name,
                        min: minValue,
                        max: maxValue,
                      });

                      // The filtered image will be generated automatically by the useEffect
                      setIsRangeDialogOpen(false);
                    }}
                  >
                    Apply Range
                  </Button>
                </div>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {/* Live indicator */}
      <div className="absolute top-4 right-16">
        <Badge className="bg-green-500/20 backdrop-blur text-green-100 border-green-400/30 animate-pulse">
          <Zap className="h-3 w-3 mr-1" />
          Live
        </Badge>
      </div>
    </div>
  );
}

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
import { Slider } from "@/components/ui/slider";
import {
  MapPin,
  Layers,
  Zap,
  Image as ImageIcon,
  Settings,
  FolderOpen,
  Copy,
  Info,
  Globe,
  Camera,
  RotateCcw,
} from "lucide-react";
import { useDataStore } from "@/hooks/useDataStore";
import { InteractiveMap } from "@/components/InteractiveMap";
import { CanvasInteractiveMap } from "@/components/CanvasInteractiveMap";

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

// 辅助函数：获取Sentinel-3的fallback文件名
const getSentinel3FallbackFilename = (param: string): string => {
  switch (param) {
    case "sst-s3a":
      return "20250923_211031.nc"; // Sentinel-3A SST NC文件
    case "sst-s3b":
      return "20250923_211028.nc"; // Sentinel-3B SST NC文件
    case "chl-s3a":
      return "20250923_211036.nc"; // Sentinel-3A Chl NC文件
    case "chl-s3b":
      return "20250923_211040.nc"; // Sentinel-3B Chl NC文件
    default:
      return "20250923_211031.nc"; // 默认SST文件
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

  // State for current image path display functionality
  const [currentImageInfo, setCurrentImageInfo] = useState<{
    filename: string;
    url: string;
    localPath?: string;
  } | null>(null);
  const [isImageInfoDialogOpen, setIsImageInfoDialogOpen] = useState(false);

  // State for map view mode
  const [viewMode, setViewMode] = useState<"static" | "interactive" | "canvas">(
    "static"
  );

  // Interactive map states (from main branch)
  const [zoomLevel, setZoomLevel] = useState(1);
  const [panPosition, setPanPosition] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [imageContainer, setImageContainer] = useState<HTMLDivElement | null>(
    null
  );
  const [imageDimensions, setImageDimensions] = useState({
    width: 0,
    height: 0,
  });
  const [containerDimensions, setContainerDimensions] = useState({
    width: 0,
    height: 0,
  });
  const [baseScale, setBaseScale] = useState(1);

  // 如果没有传入getParameterFiles，则使用useDataStore（向后兼容）
  const dataStore = !getParameterFiles ? useDataStore() : null;
  const getFiles = getParameterFiles || dataStore?.getParameterFiles;

  const currentParam = availableParameters.find((p) => p.id === parameter);
  const satelliteMapping =
    SATELLITE_MAPPING[parameter as keyof typeof SATELLITE_MAPPING];

  // 获取当前时间戳和文件名
  const currentTimestamp = useMemo(() => {
    if (!satelliteMapping) return null;

    // all 模式不生成时间戳
    if (timeRange.granularity === "all") {
      return null;
    }

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
  }, [
    parameter,
    timeRange.start,
    timeRange.end,
    timeRange.granularity,
    satelliteMapping,
  ]);

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
          // 创建异步函数来处理NC文件名获取
          const handleNCFilename = async () => {
            let ncFilename;
            if (parameter === "ssth") {
              ncFilename = currentFile.filename.replace(".png", ".nc");
            } else {
              // 对于Sentinel-3，获取唯一的NC文件（包含所有时间范围数据）
              try {
                if (!getFiles) {
                  console.warn("getFiles function not available");
                  ncFilename = getSentinel3FallbackFilename(parameter);
                } else {
                  const ncFiles = await getFiles?.(parameter, "nc");
                  if (ncFiles && ncFiles.length > 0) {
                    // Sentinel-3通常只有一个NC文件包含整个查询时间范围的数据
                    ncFilename = ncFiles[0].filename;
                    console.log(
                      `Using Sentinel-3 NC file for ${parameter}: ${ncFilename}`
                    );
                  } else {
                    console.warn(
                      `No NC files found for ${parameter}, using fallback`
                    );
                    ncFilename = getSentinel3FallbackFilename(parameter);
                  }
                }
              } catch (error) {
                console.warn(
                  "Failed to get NC files list, using fallback:",
                  error
                );
                ncFilename = getSentinel3FallbackFilename(parameter);
              }
            }

            const minNum = appliedMin ? parseFloat(appliedMin) : undefined;
            const maxNum = appliedMax ? parseFloat(appliedMax) : undefined;
            console.log(
              `Generating filtered image for ${parameter} with range:`,
              { minNum, maxNum, ncFilename }
            );
            generateFilteredImage(ncFilename, minNum, maxNum);
          };

          // 执行异步函数
          handleNCFilename();
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

      // 添加target_time参数
      const targetTime =
        timeRange.granularity === "all" ? "all" : timeRange.start.toISOString();
      params.append("target_time", targetTime);

      // 添加模式参数
      params.append("mode", timeRange.granularity);

      // 如果是all模式，添加时间范围参数
      if (timeRange.granularity === "all") {
        params.append("start_time", timeRange.start.toISOString());
        params.append("end_time", timeRange.end.toISOString());
      }

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
    if (timeRange.granularity === "all") {
      // all 模式：返回时间范围内最接近endTime的文件
      const endTime = timeRange.end;
      console.log("All mode - endTime:", endTime, "files count:", files.length);
      let bestFile = null;
      let bestTimeDiff = Infinity;

      for (const file of files) {
        let fileTime: Date | null = null;

        if (parameter === "ssth") {
          // Himawari 文件时间提取
          const timeMatch = file.filename.match(/(\d{8})(\d{6})\.png$/);
          if (timeMatch) {
            const dateStr = timeMatch[1];
            const timeStr = timeMatch[2];
            const year = dateStr.substring(0, 4);
            const month = dateStr.substring(4, 6);
            const day = dateStr.substring(6, 8);
            const hour = timeStr.substring(0, 2);
            const minute = timeStr.substring(2, 4);
            const second = timeStr.substring(4, 6);
            fileTime = new Date(
              `${year}-${month}-${day}T${hour}:${minute}:${second}Z`
            );
            console.log(
              "Himawari file time:",
              file.filename,
              "->",
              fileTime,
              "endTime:",
              endTime
            );
          }
        } else {
          // Sentinel-3 文件时间提取
          fileTime = extractTimeFromSentinel3Filename(file.filename);
        }

        // 查找最接近endTime的文件（允许文件时间稍晚于endTime）
        if (fileTime) {
          const timeDiff = Math.abs(endTime.getTime() - fileTime.getTime());
          if (timeDiff < bestTimeDiff) {
            bestTimeDiff = timeDiff;
            bestFile = file;
          }
        }
      }

      console.log(
        "All mode - selected file:",
        bestFile?.filename,
        "timeDiff:",
        bestTimeDiff
      );
      return bestFile || files[0]; // 如果没有找到合适的，返回最新文件
    }

    // Day和Week模式：使用精确时间戳匹配
    if (timeRange.granularity === "day") {
      // Day模式：使用类似Week模式的动态选择，选择最接近selectedTime的文件
      let bestFile = null;
      let bestTimeDiff = Infinity;

      for (const file of files) {
        let fileTime: Date | null = null;

        if (parameter === "ssth") {
          // Himawari 文件时间提取
          const timeMatch = file.filename.match(/(\d{8})(\d{6})\.png$/);
          if (timeMatch) {
            const dateStr = timeMatch[1];
            const timeStr = timeMatch[2];
            const year = dateStr.substring(0, 4);
            const month = dateStr.substring(4, 6);
            const day = dateStr.substring(6, 8);
            const hour = timeStr.substring(0, 2);
            const minute = timeStr.substring(2, 4);
            const second = timeStr.substring(4, 6);
            fileTime = new Date(
              `${year}-${month}-${day}T${hour}:${minute}:${second}Z`
            );
          }
        } else {
          // Sentinel-3 文件时间提取
          fileTime = extractTimeFromSentinel3Filename(file.filename);
        }

        // 查找最接近selectedTime的文件
        if (fileTime) {
          const timeDiff = Math.abs(
            selectedTime.getTime() - fileTime.getTime()
          );
          if (timeDiff < bestTimeDiff) {
            bestTimeDiff = timeDiff;
            bestFile = file;
          }
        }
      }

      return bestFile || files[0];
    } else if (timeRange.granularity === "week") {
      // Week模式：使用类似All模式的逻辑，选择最接近selectedTime的文件
      let bestFile = null;
      let bestTimeDiff = Infinity;

      for (const file of files) {
        let fileTime: Date | null = null;

        if (parameter === "ssth") {
          // Himawari 文件时间提取
          const timeMatch = file.filename.match(/(\d{8})(\d{6})\.png$/);
          if (timeMatch) {
            const dateStr = timeMatch[1];
            const timeStr = timeMatch[2];
            const year = dateStr.substring(0, 4);
            const month = dateStr.substring(4, 6);
            const day = dateStr.substring(6, 8);
            const hour = timeStr.substring(0, 2);
            const minute = timeStr.substring(2, 4);
            const second = timeStr.substring(4, 6);
            fileTime = new Date(
              `${year}-${month}-${day}T${hour}:${minute}:${second}Z`
            );
          }
        } else {
          // Sentinel-3 文件时间提取
          fileTime = extractTimeFromSentinel3Filename(file.filename);
        }

        // 查找最接近selectedTime的文件
        if (fileTime) {
          const timeDiff = Math.abs(
            selectedTime.getTime() - fileTime.getTime()
          );
          if (timeDiff < bestTimeDiff) {
            bestTimeDiff = timeDiff;
            bestFile = file;
          }
        }
      }

      return bestFile || files[0];
    }
  };

  useEffect(() => {
    if (satelliteMapping && availableFiles.length > 0) {
      console.log("All mode - timeRange changed:", {
        start: timeRange.start,
        end: timeRange.end,
        granularity: timeRange.granularity,
      });
      // 寻找最匹配的文件
      let targetFile: any = null;

      // 使用通用文件查找函数
      // 所有模式都使用timeRange.end（当前滑动位置时间）
      const selectedTime = timeRange.end;
      targetFile = findBestFileForTime(availableFiles, selectedTime);

      console.log(
        `Looking for file with timestamp: ${currentTimestamp || "all"}`
      );
      console.log(
        `Available files:`,
        availableFiles.map((f) => f.filename)
      );

      if (targetFile) {
        const pngUrl = `http://localhost:8000${targetFile.url}`;

        // 获取对应的NC文件名来获取数据统计信息
        const handleStatsRetrieval = async () => {
          let ncFilename;
          if (parameter === "ssth") {
            ncFilename = targetFile.filename.replace(".png", ".nc");
          } else {
            // 对于Sentinel-3，动态获取NC文件（类似Himawari的方式）
            try {
              const ncFiles = await getFiles?.(parameter, "nc");
              if (ncFiles && ncFiles.length > 0) {
                // 使用最新的NC文件（按修改时间排序）
                ncFilename = ncFiles[0].filename;
                console.log(
                  `Using latest NC file for stats ${parameter}: ${ncFilename}`
                );
              } else {
                console.warn(
                  `No NC files found for stats ${parameter}, using fallback`
                );
                ncFilename = getSentinel3FallbackFilename(parameter);
              }
            } catch (error) {
              console.warn(
                "Failed to get NC files list for stats, using fallback:",
                error
              );
              ncFilename = getSentinel3FallbackFilename(parameter);
            }
          }

          // 传递目标时间给API
          const targetTime =
            timeRange.granularity === "all"
              ? "all"
              : timeRange.start.toISOString();
          console.log(
            `Fetching stats for ${parameter} using NC file: ${ncFilename} at time: ${targetTime}`
          );
          fetchDataStats(ncFilename, targetTime);
        };

        // 执行异步函数
        handleStatsRetrieval();

        // 避免重复加载相同的图片
        if (imageUrl === pngUrl) {
          return;
        }

        setIsLoading(true);
        setImageError(false);

        console.log(`Loading ${parameter} image:`, targetFile.filename);
        console.log(`Image URL: ${pngUrl}`);

        // Check if image exists and update image info
        const img = new Image();
        img.onload = () => {
          setImageUrl(pngUrl);
          setIsLoading(false);

          // Update current image info for path display functionality
          // Use absolute directory path from backend if available
          const absolutePath = targetFile.directory
            ? `${targetFile.directory}${
                targetFile.directory.includes("\\") ? "\\" : "/"
              }${targetFile.filename}`
            : `data/${satelliteMapping.satellite}/${satelliteMapping.parameter}/png/${targetFile.filename}`;

          const imageInfo = {
            filename: targetFile.filename,
            url: pngUrl,
            localPath: absolutePath,
          };
          setCurrentImageInfo(imageInfo);
          console.log("Current image info updated:", imageInfo);
        };
        img.onerror = () => {
          console.warn(`PNG failed to load: ${targetFile.filename}`);
          setImageError(true);
          setImageUrl(null);
          setIsLoading(false);
          setCurrentImageInfo(null); // Clear image info on error
        };
        img.src = pngUrl;
      } else {
        console.warn(
          `No suitable PNG file found for ${parameter} at ${currentTimestamp}`
        );
        setImageError(true);
        setImageUrl(null);
        setIsLoading(false);
        setCurrentImageInfo(null); // Clear image info when no file found
      }
    } else if (satelliteMapping) {
      // Parameter supported but no available files
      setIsLoading(false);
      setImageUrl(null);
      setImageError(true);
      setCurrentImageInfo(null); // Clear image info when no files available
    } else {
      // Unsupported parameter, show placeholder
      setIsLoading(false);
      setImageUrl(null);
      setImageError(false);
      setCurrentImageInfo(null); // Clear image info for unsupported parameters
    }
  }, [
    satelliteMapping,
    currentTimestamp,
    availableFiles,
    parameter,
    imageUrl,
    timeRange.end,
    timeRange.granularity,
  ]);

  // Interactive map functions (from main branch)
  // ResizeObserver to track container dimensions and calculate base scale
  useEffect(() => {
    if (!imageContainer) return;

    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect;
        setContainerDimensions({ width, height });
      }
    });

    resizeObserver.observe(imageContainer);

    return () => {
      resizeObserver.disconnect();
    };
  }, [imageContainer]);

  // Calculate base scale when image dimensions or container dimensions change
  useEffect(() => {
    if (
      imageDimensions.width &&
      imageDimensions.height &&
      containerDimensions.width &&
      containerDimensions.height
    ) {
      const scaleX = containerDimensions.width / imageDimensions.width;
      const scaleY = containerDimensions.height / imageDimensions.height;
      const newBaseScale = Math.min(scaleX, scaleY); // fit inside container

      setBaseScale(newBaseScale);

      // Reset pan position when base scale changes (e.g., when entering/leaving fullscreen)
      setPanPosition({ x: 0, y: 0 });
    }
  }, [imageDimensions, containerDimensions]);

  // Zoom handlers with proper origin point and boundaries
  const constrainPan = (
    x: number,
    y: number,
    zoom: number,
    containerWidth: number,
    containerHeight: number
  ) => {
    if (zoom <= 1) return { x: 0, y: 0 };

    // Calculate the actual displayed size using baseScale * zoom
    const displayScale = baseScale * zoom;
    const displayedWidth = imageDimensions.width * displayScale;
    const displayedHeight = imageDimensions.height * displayScale;

    // Calculate maximum pan distances to keep image in view
    const maxPanX = Math.max(0, (displayedWidth - containerWidth) / 2);
    const maxPanY = Math.max(0, (displayedHeight - containerHeight) / 2);

    return {
      x: Math.max(-maxPanX, Math.min(maxPanX, x)),
      y: Math.max(-maxPanY, Math.min(maxPanY, y)),
    };
  };

  const handleZoomChange = (value: number[]) => {
    const newZoom = value[0];

    if (!imageContainer) {
      setZoomLevel(newZoom);
      setPanPosition({ x: 0, y: 0 });
      return;
    }

    const containerRect = imageContainer.getBoundingClientRect();
    const containerCenterX = containerRect.width / 2;
    const containerCenterY = containerRect.height / 2;

    // Calculate scale factor
    const scaleFactor = newZoom / zoomLevel;

    // For zoom from slider, always zoom from center
    const newPanX = panPosition.x * scaleFactor;
    const newPanY = panPosition.y * scaleFactor;

    // Apply constraints
    const constrainedPan = constrainPan(
      newPanX,
      newPanY,
      newZoom,
      containerRect.width,
      containerRect.height
    );

    setZoomLevel(newZoom);
    setPanPosition(constrainedPan);
  };

  const handleZoomAtPoint = (
    clientX: number,
    clientY: number,
    newZoom: number
  ) => {
    if (!imageContainer) return;

    const containerRect = imageContainer.getBoundingClientRect();
    const pointX = clientX - containerRect.left;
    const pointY = clientY - containerRect.top;

    // Calculate scale factor
    const scaleFactor = newZoom / zoomLevel;

    // Calculate new pan position to zoom towards the point
    const newPanX = pointX - (pointX - panPosition.x) * scaleFactor;
    const newPanY = pointY - (pointY - panPosition.y) * scaleFactor;

    // Apply constraints
    const constrainedPan = constrainPan(
      newPanX,
      newPanY,
      newZoom,
      containerRect.width,
      containerRect.height
    );

    setZoomLevel(newZoom);
    setPanPosition(constrainedPan);
  };

  const handleReset = () => {
    setZoomLevel(1);
    setPanPosition({ x: 0, y: 0 });
  };

  // Handle image load to get dimensions
  const handleImageLoad = (e: React.SyntheticEvent<HTMLImageElement>) => {
    const img = e.currentTarget;
    setImageDimensions({
      width: img.naturalWidth,
      height: img.naturalHeight,
    });
  };

  // Mouse handlers for panning
  const handleMouseDown = (e: React.MouseEvent) => {
    if (zoomLevel > 1) {
      setIsDragging(true);
      setDragStart({
        x: e.clientX - panPosition.x,
        y: e.clientY - panPosition.y,
      });
    }
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (isDragging && zoomLevel > 1 && imageContainer) {
      const containerRect = imageContainer.getBoundingClientRect();
      const newPan = {
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y,
      };

      const constrainedPan = constrainPan(
        newPan.x,
        newPan.y,
        zoomLevel,
        containerRect.width,
        containerRect.height
      );
      setPanPosition(constrainedPan);
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const handleMouseLeave = () => {
    setIsDragging(false);
  };

  // Wheel zoom handler
  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? -0.1 : 0.1;
    const newZoom = Math.max(0.5, Math.min(5, zoomLevel + delta));

    if (newZoom !== zoomLevel) {
      handleZoomAtPoint(e.clientX, e.clientY, newZoom);
    }
  };

  if (isLoading) {
    return (
      <div className="h-96 bg-slate-100 rounded-lg flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  // 选择要渲染的内容
  if (viewMode === "interactive") {
    return (
      <div
        className={`relative ${
          isFullscreen ? "h-full" : "h-96"
        } rounded-lg overflow-hidden`}
      >
        {/* 视图切换按钮 */}
        <div className="absolute top-4 right-4 z-[1000] flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setViewMode("canvas")}
            className="bg-white/20 backdrop-blur text-white border-white/30 hover:bg-white/30"
            title="Switch to canvas heatmap view"
          >
            <Globe className="h-3 w-3 mr-1" />
            Canvas
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setViewMode("static")}
            className="bg-white/20 backdrop-blur text-white border-white/30 hover:bg-white/30"
            title="Switch to static image view"
          >
            <Camera className="h-3 w-3 mr-1" />
            Static
          </Button>
        </div>

        <InteractiveMap
          parameter={parameter}
          timeRange={timeRange}
          availableParameters={availableParameters}
          isFullscreen={isFullscreen}
          getParameterFiles={getFiles}
        />
      </div>
    );
  }

  if (viewMode === "canvas") {
    return (
      <div
        className={`relative ${
          isFullscreen ? "h-full" : "h-96"
        } rounded-lg overflow-hidden`}
      >
        {/* 视图切换按钮 */}
        <div className="absolute top-4 right-4 z-[1000] flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setViewMode("interactive")}
            className="bg-white/20 backdrop-blur text-white border-white/30 hover:bg-white/30"
            title="Switch to point interactive view"
          >
            <MapPin className="h-3 w-3 mr-1" />
            Points
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setViewMode("static")}
            className="bg-white/20 backdrop-blur text-white border-white/30 hover:bg-white/30"
            title="Switch to static image view"
          >
            <Camera className="h-3 w-3 mr-1" />
            Static
          </Button>
        </div>

        <CanvasInteractiveMap
          parameter={parameter}
          timeRange={timeRange}
          availableParameters={availableParameters}
          isFullscreen={isFullscreen}
          getParameterFiles={getFiles}
        />
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
          ref={setImageContainer}
          className="absolute inset-0 w-full h-full flex items-center justify-center overflow-hidden cursor-grab"
          style={{
            background: `
            radial-gradient(ellipse at center, #0a1a2e 0%, #16213e 30%, #1e3a8a 70%, #3b82f6 100%),
            linear-gradient(135deg, #0f172a 0%, #1e3a8a 50%, #3b82f6 100%)
          `,
            backgroundBlendMode: "multiply, normal",
            cursor: isDragging
              ? "grabbing"
              : zoomLevel > 1
              ? "grab"
              : "default",
          }}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseLeave}
          onWheel={handleWheel}
        >
          <div
            style={{
              transform: `translate(${panPosition.x}px, ${
                panPosition.y
              }px) scale(${baseScale * zoomLevel})`,
              transition: isDragging ? "none" : "transform 0.2s ease-out",
            }}
          >
            <img
              src={filteredImageUrl || imageUrl || ""}
              alt={`${currentParam?.name} visualization`}
              className="max-w-none rounded-lg"
              style={{ filter: "contrast(1.1) brightness(1.1)" }}
              draggable={false}
              onLoad={handleImageLoad}
            />
          </div>
          {/* Overlay for better text readability */}
          <div className="absolute inset-0 bg-black/10 pointer-events-none"></div>

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

        {/* Image Path Display Button */}
        {imageUrl && currentImageInfo && (
          <Dialog
            open={isImageInfoDialogOpen}
            onOpenChange={setIsImageInfoDialogOpen}
          >
            <DialogTrigger asChild>
              <Button
                variant="outline"
                size="sm"
                className="bg-white/20 backdrop-blur text-white border-white/30 hover:bg-white/30 w-fit"
                title="View image file information"
              >
                <Info className="h-3 w-3 mr-1" />
                Image Info
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-md">
              <DialogHeader>
                <DialogTitle>Current Image Information</DialogTitle>
              </DialogHeader>
              <div className="space-y-4">
                <div className="space-y-3">
                  <div>
                    <Label className="text-sm font-medium text-gray-700">
                      Filename
                    </Label>
                    <div className="mt-1 p-2 bg-gray-50 rounded border text-sm font-mono">
                      {currentImageInfo.filename}
                    </div>
                  </div>

                  <div>
                    <Label className="text-sm font-medium text-gray-700">
                      Local Path
                    </Label>
                    <div className="mt-1 p-2 bg-gray-50 rounded border text-sm font-mono break-all">
                      {currentImageInfo.localPath}
                    </div>
                    <div className="flex gap-2 mt-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={async () => {
                          try {
                            // 尝试通过后端API打开文件管理器
                            const response = await fetch(
                              "http://localhost:8000/api/v1/open-path",
                              {
                                method: "POST",
                                headers: {
                                  "Content-Type": "application/json",
                                },
                                body: JSON.stringify({
                                  path: currentImageInfo.localPath,
                                }),
                              }
                            );

                            if (response.ok) {
                              console.log("File manager opened successfully");
                            } else {
                              throw new Error("Backend API failed");
                            }
                          } catch (error) {
                            console.error(
                              "Failed to open path via backend:",
                              error
                            );

                            // 后备方案：尝试使用浏览器原生方法
                            try {
                              // 对于Windows系统，尝试使用file:// protocol
                              const fileUrl = `file:///${currentImageInfo.localPath?.replace(
                                /\\/g,
                                "/"
                              )}`;
                              window.open(fileUrl, "_blank");
                            } catch (fallbackError) {
                              console.error(
                                "Fallback method also failed:",
                                fallbackError
                              );
                              // 最后的后备方案：复制路径到剪贴板
                              navigator.clipboard
                                .writeText(currentImageInfo.localPath || "")
                                .then(() => {
                                  alert(
                                    "Cannot open file manager. Path copied to clipboard instead."
                                  );
                                })
                                .catch(() => {
                                  alert(
                                    "Cannot open file manager or copy path. Please manually navigate to: " +
                                      currentImageInfo.localPath
                                  );
                                });
                            }
                          }
                        }}
                      >
                        <FolderOpen className="h-3 w-3 mr-1" />
                        Open Path
                      </Button>

                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          navigator.clipboard
                            .writeText(currentImageInfo.localPath || "")
                            .then(() => {
                              console.log("Path copied to clipboard");
                              // 可以添加toast通知
                            })
                            .catch((err) => {
                              console.error("Failed to copy path:", err);
                              alert("Failed to copy path to clipboard");
                            });
                        }}
                      >
                        <Copy className="h-3 w-3 mr-1" />
                        Copy Path
                      </Button>
                    </div>
                  </div>

                  <div>
                    <Label className="text-sm font-medium text-gray-700">
                      Server URL
                    </Label>
                    <div className="mt-1 p-2 bg-gray-50 rounded border text-sm font-mono break-all">
                      {currentImageInfo.url}
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      className="mt-2"
                      onClick={() => {
                        window.open(currentImageInfo.url, "_blank");
                      }}
                    >
                      <FolderOpen className="h-3 w-3 mr-1" />
                      Open in Browser
                    </Button>
                  </div>

                  <div className="p-3 bg-blue-50 rounded border border-blue-200">
                    <p className="text-xs text-blue-700 font-medium mb-1">
                      Image Details:
                    </p>
                    <div className="text-xs text-blue-600">
                      <p>
                        Satellite: {satelliteMapping?.satellite.toUpperCase()}
                      </p>
                      <p>Parameter: {currentParam?.name}</p>
                      <p>Timestamp: {timeRange.start.toLocaleString()}</p>
                    </div>
                  </div>
                </div>

                <div className="flex justify-end">
                  <Button
                    variant="outline"
                    onClick={() => setIsImageInfoDialogOpen(false)}
                  >
                    Close
                  </Button>
                </div>
              </div>
            </DialogContent>
          </Dialog>
        )}

        {/* View Mode Toggle Buttons */}
        <div className="flex flex-col gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setViewMode("canvas")}
            className="bg-white/20 backdrop-blur text-white border-white/30 hover:bg-white/30 w-fit"
            title="Switch to canvas view"
          >
            <Globe className="h-3 w-3 mr-1" />
            Canvas
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setViewMode("interactive")}
            className="bg-white/20 backdrop-blur text-white border-white/30 hover:bg-white/30 w-fit"
            title="Switch to point interactive view"
          >
            <MapPin className="h-3 w-3 mr-1" />
            Interactive
          </Button>
        </div>

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

      {/* Zoom Controls */}
      <div className="absolute top-4 right-4 flex flex-col gap-3 z-10">
        <div className="bg-white/20 backdrop-blur border border-white/30 rounded-lg p-3 min-w-[160px]">
          {/* Zoom Level Display */}
          <div className="text-white text-xs text-center mb-2 font-medium">
            Zoom: {Math.round(zoomLevel * 100)}%
          </div>

          {/* Zoom Slider */}
          <Slider
            value={[zoomLevel]}
            onValueChange={handleZoomChange}
            min={0.5}
            max={5}
            step={0.1}
            className="w-full"
          />

          {/* Zoom Range Labels */}
          <div className="flex justify-between text-white text-xs mt-1 opacity-75">
            <span>0.5x</span>
            <span>5x</span>
          </div>

          {/* Reset Button */}
          {(zoomLevel !== 1 || panPosition.x !== 0 || panPosition.y !== 0) && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleReset}
              className="w-full mt-2 h-7 text-xs bg-gray-800/90 border-gray-600 text-white hover:bg-gray-700 hover:text-white"
              title="Reset Zoom and Position"
            >
              <RotateCcw className="h-3 w-3 mr-1" />
              Reset
            </Button>
          )}
        </div>
      </div>

      {/* Live indicator */}
      <div className="absolute top-4 right-20">
        <Badge className="bg-green-500/20 backdrop-blur text-green-100 border-green-400/30 animate-pulse">
          <Zap className="h-3 w-3 mr-1" />
          Live
        </Badge>
      </div>
    </div>
  );
}

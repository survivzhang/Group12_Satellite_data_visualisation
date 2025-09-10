"use client";

import { useState, useEffect, useMemo } from "react";
import { Parameter, TimeRange } from "@/types/research";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { MapPin, Layers, Zap, Image as ImageIcon } from "lucide-react";
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

export function ResearchMap({
  parameter,
  timeRange,
  availableParameters,
  isFullscreen,
  getParameterFiles,
}: ResearchMapProps): JSX.Element {
  const [isLoading, setIsLoading] = useState(true);
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [imageError, setImageError] = useState(false);
  const [availableFiles, setAvailableFiles] = useState<any[]>([]);

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
      // Sentinel-3格式: ISO时间戳
      return utcDate.toISOString().replace(/[:.]/g, "-").replace("Z", "");
    }
  }, [parameter, timeRange.start, satelliteMapping]);

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

  useEffect(() => {
    if (satelliteMapping && currentTimestamp && availableFiles.length > 0) {
      // 寻找最匹配的文件
      let targetFile: any = null;

      // 根据参数类型查找匹配的文件
      if (parameter === "ssth") {
        // Himawari 文件查找 - 查找包含时间戳的文件
        targetFile = availableFiles.find(
          (file) => file.filename && file.filename.startsWith(currentTimestamp)
        );
      } else {
        // Sentinel-3 文件查找
        targetFile = availableFiles.find(
          (file) =>
            file.filename &&
            file.filename.includes(currentTimestamp.substring(0, 19))
        );
      }

      console.log(`Looking for file with timestamp: ${currentTimestamp}`);
      console.log(
        `Available files:`,
        availableFiles.map((f) => f.filename)
      );

      if (targetFile) {
        const pngUrl = `http://localhost:8000${targetFile.url}`;

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

  // 辅助函数：解析Himawari时间戳
  const parseHimawariTimestamp = (timeStr: string): Date | null => {
    if (timeStr.length >= 14) {
      const year = timeStr.substring(0, 4);
      const month = timeStr.substring(4, 6);
      const day = timeStr.substring(6, 8);
      const hour = timeStr.substring(8, 10);
      const minute = timeStr.substring(10, 12);
      const second = timeStr.substring(12, 14);

      return new Date(`${year}-${month}-${day}T${hour}:${minute}:${second}Z`);
    }
    return null;
  };

  // 辅助函数：检查时间是否接近
  const isTimeClose = (
    fileTime: Date,
    targetTime: Date,
    toleranceHours: number = 1
  ): boolean => {
    const diff = Math.abs(fileTime.getTime() - targetTime.getTime());
    return diff <= toleranceHours * 60 * 60 * 1000; // 1小时容差
  };

  if (isLoading) {
    return (
      <div className="h-96 bg-slate-100 rounded-lg flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="relative h-full w-full bg-slate-900 rounded-lg overflow-hidden">
      {imageUrl && satelliteMapping ? (
        <div className="relative h-full">
          <img
            src={imageUrl}
            alt={`${currentParam?.name} visualization`}
            className="w-full h-full object-cover"
            style={{ filter: "contrast(1.1) brightness(1.1)" }}
          />
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
      <div className="absolute top-4 left-4 flex flex-col gap-2">
        <Badge className="bg-white/20 backdrop-blur text-white border-white/30">
          <div className="flex items-center gap-1">
            {currentParam?.icon}
            {currentParam?.name}
          </div>
        </Badge>
        <Badge className="bg-white/20 backdrop-blur text-white border-white/30">
          {imageUrl && satelliteMapping ? (
            <>
              <ImageIcon className="h-3 w-3 mr-1" />
              {satelliteMapping.satellite.toUpperCase()} Image
            </>
          ) : (
            <>
              <MapPin className="h-3 w-3 mr-1" />
              {satelliteMapping ? "No data available" : "Coming soon"}
            </>
          )}
        </Badge>
        {imageUrl && satelliteMapping && currentTimestamp && (
          <Badge className="bg-white/20 backdrop-blur text-white border-white/30">
            <div className="text-xs">
              {parameter === "ssth"
                ? new Date(
                    `${currentTimestamp.substring(
                      0,
                      4
                    )}-${currentTimestamp.substring(
                      4,
                      6
                    )}-${currentTimestamp.substring(
                      6,
                      8
                    )}T${currentTimestamp.substring(8, 10)}:00:00Z`
                  ).toLocaleString()
                : timeRange.start.toLocaleString()}
            </div>
          </Badge>
        )}
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

"use client";

import { useState, useEffect, useMemo } from "react";
import { Parameter, TimeRange } from "@/types/research";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { MapPin, Layers, Zap, Image as ImageIcon, Settings } from "lucide-react";
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
  const [rangeFrom, setRangeFrom] = useState<string>("");
  const [rangeTo, setRangeTo] = useState<string>("");
  const [isRangeDialogOpen, setIsRangeDialogOpen] = useState(false);
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
        // Sentinel-3 文件查找 - 寻找选中时间点之前最近的那张图
        const selectedTime = timeRange.start.getTime();
        let bestFile = null;
        let bestTimeDiff = Infinity;
        
        for (const file of availableFiles) {
          const fileTime = extractTimeFromSentinel3Filename(file.filename);
          if (fileTime && fileTime.getTime() <= selectedTime) {
            const timeDiff = selectedTime - fileTime.getTime();
            if (timeDiff < bestTimeDiff) {
              bestTimeDiff = timeDiff;
              bestFile = file;
            }
          }
        }
        targetFile = bestFile;
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
      {imageUrl && satelliteMapping ? (
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
          <img
            src={imageUrl}
            alt={`${currentParam?.name} visualization`}
            className={`${
              isFullscreen ? "max-w-full max-h-full" : "w-full h-full"
            } object-contain rounded-lg`}
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
              <span className="truncate">{satelliteMapping.satellite.toUpperCase()} Image</span>
            </>
          ) : (
            <>
              <MapPin className="h-3 w-3 mr-1" />
              <span className="truncate">{satelliteMapping ? "No data available" : "Coming soon"}</span>
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
        
        {/* Range Selector Button */}
        <Dialog open={isRangeDialogOpen} onOpenChange={setIsRangeDialogOpen}>
          <DialogTrigger asChild>
            <Button 
              variant="outline" 
              size="sm" 
              className="bg-white/20 backdrop-blur text-white border-white/30 hover:bg-white/30 w-fit"
            >
              <Settings className="h-3 w-3 mr-1" />
              Range
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle>Select Data Range</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="range-from">From</Label>
                <Input
                  id="range-from"
                  type="text"
                  placeholder="Enter start value"
                  value={rangeFrom}
                  onChange={(e) => setRangeFrom(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="range-to">To</Label>
                <Input
                  id="range-to"
                  type="text"
                  placeholder="Enter end value"
                  value={rangeTo}
                  onChange={(e) => setRangeTo(e.target.value)}
                />
              </div>
              <div className="flex justify-end space-x-2">
                <Button 
                  variant="outline" 
                  onClick={() => setIsRangeDialogOpen(false)}
                >
                  Cancel
                </Button>
                <Button 
                  onClick={() => {
                    // Handle range selection logic here
                    console.log("Range selected:", { from: rangeFrom, to: rangeTo });
                    setIsRangeDialogOpen(false);
                  }}
                >
                  Apply
                </Button>
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

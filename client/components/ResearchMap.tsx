"use client";

import { useState, useEffect, useMemo } from "react";
import { Parameter, TimeRange } from "@/types/research";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import { MapPin, Layers, Zap, Image as ImageIcon, RotateCcw } from "lucide-react";
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
  const [zoomLevel, setZoomLevel] = useState(1);
  const [panPosition, setPanPosition] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [imageContainer, setImageContainer] = useState<HTMLDivElement | null>(null);
  const [imageDimensions, setImageDimensions] = useState({ width: 0, height: 0 });
  const [containerDimensions, setContainerDimensions] = useState({ width: 0, height: 0 });
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
    if (imageDimensions.width && imageDimensions.height && containerDimensions.width && containerDimensions.height) {
      const scaleX = containerDimensions.width / imageDimensions.width;
      const scaleY = containerDimensions.height / imageDimensions.height;
      const newBaseScale = Math.min(scaleX, scaleY); // fit inside container
      
      setBaseScale(newBaseScale);
      
      // Reset pan position when base scale changes (e.g., when entering/leaving fullscreen)
      setPanPosition({ x: 0, y: 0 });
    }
  }, [imageDimensions, containerDimensions]);

  // Zoom handlers with proper origin point and boundaries
  const constrainPan = (x: number, y: number, zoom: number, containerWidth: number, containerHeight: number) => {
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
      y: Math.max(-maxPanY, Math.min(maxPanY, y))
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
    const constrainedPan = constrainPan(newPanX, newPanY, newZoom, containerRect.width, containerRect.height);
    
    setZoomLevel(newZoom);
    setPanPosition(constrainedPan);
  };

  const handleZoomAtPoint = (clientX: number, clientY: number, newZoom: number) => {
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
    const constrainedPan = constrainPan(newPanX, newPanY, newZoom, containerRect.width, containerRect.height);
    
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
      height: img.naturalHeight
    });
  };

  // Mouse handlers for panning
  const handleMouseDown = (e: React.MouseEvent) => {
    if (zoomLevel > 1) {
      setIsDragging(true);
      setDragStart({ x: e.clientX - panPosition.x, y: e.clientY - panPosition.y });
    }
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (isDragging && zoomLevel > 1 && imageContainer) {
      const containerRect = imageContainer.getBoundingClientRect();
      const newPan = {
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y,
      };
      
      const constrainedPan = constrainPan(newPan.x, newPan.y, zoomLevel, containerRect.width, containerRect.height);
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
          ref={setImageContainer}
          className="absolute inset-0 w-full h-full flex items-center justify-center overflow-hidden cursor-grab"
          style={{
            background: `
            radial-gradient(ellipse at center, #0a1a2e 0%, #16213e 30%, #1e3a8a 70%, #3b82f6 100%),
            linear-gradient(135deg, #0f172a 0%, #1e3a8a 50%, #3b82f6 100%)
          `,
            backgroundBlendMode: "multiply, normal",
            cursor: isDragging ? 'grabbing' : zoomLevel > 1 ? 'grab' : 'default',
          }}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseLeave}
          onWheel={handleWheel}
        >
          <div
            style={{
              transform: `translate(${panPosition.x}px, ${panPosition.y}px) scale(${baseScale * zoomLevel})`,
              transition: isDragging ? 'none' : 'transform 0.2s ease-out',
            }}
          >
            <img
              src={imageUrl}
              alt={`${currentParam?.name} visualization`}
              className="max-w-none rounded-lg"
              style={{ filter: "contrast(1.1) brightness(1.1)" }}
              draggable={false}
              onLoad={handleImageLoad}
            />
          </div>
          {/* Overlay for better text readability */}
          <div className="absolute inset-0 bg-black/10 pointer-events-none"></div>
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
        {imageUrl && satelliteMapping && (
          <Badge className="bg-white/20 backdrop-blur text-white border-white/30">
            <div className="text-xs">
              {timeRange.start.toLocaleString()}
            </div>
          </Badge>
        )}
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

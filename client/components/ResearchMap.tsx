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
  const [dataStats, setDataStats] = useState<{
    min: number;
    max: number;
    mean: number;
    units: string;
  } | null>(null);
  const [isLoadingStats, setIsLoadingStats] = useState(false);
  const [isGeneratingFilteredImage, setIsGeneratingFilteredImage] =
    useState(false);
  const [filteredImageUrl, setFilteredImageUrl] = useState<string | null>(null);
  const [parameterMin, setParameterMin] = useState<string>("");
  const [parameterMax, setParameterMax] = useState<string>("");
  const [appliedMin, setAppliedMin] = useState<string>("");
  const [appliedMax, setAppliedMax] = useState<string>("");
  const [tempMin, setTempMin] = useState<string>("");
  const [tempMax, setTempMax] = useState<string>("");
  const [isRangeDialogOpen, setIsRangeDialogOpen] = useState(false);
  const [currentImageInfo, setCurrentImageInfo] = useState<{
    filename: string;
    url: string;
    localPath?: string;
  } | null>(null);
  const [isImageInfoDialogOpen, setIsImageInfoDialogOpen] = useState(false);
  const [viewMode, setViewMode] = useState<"static" | "interactive" | "canvas">(
    "static"
  );
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

  const dataStore = !getParameterFiles ? useDataStore() : null;
  const getFiles = getParameterFiles || dataStore?.getParameterFiles;
  const currentParam = availableParameters.find((p) => p.id === parameter);
  const satelliteMapping =
    SATELLITE_MAPPING[parameter as keyof typeof SATELLITE_MAPPING];

  const getSentinel3FallbackFilename = (param: string) => {
    if (param === "sst-s3a") return "sentinel3a_sst.nc";
    if (param === "sst-s3b") return "sentinel3b_sst.nc";
    if (param === "chl-s3a") return "sentinel3a_chl.nc";
    if (param === "chl-s3b") return "sentinel3b_chl.nc";
    return "data.nc";
  };

  const currentTimestamp = useMemo(() => {
    if (!satelliteMapping) return null;
    if (timeRange.granularity === "all") return null;

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
  }, [
    parameter,
    timeRange.start,
    timeRange.end,
    timeRange.granularity,
    satelliteMapping,
  ]);

  useEffect(() => {
    if (isRangeDialogOpen) {
      setTempMin(parameterMin);
      setTempMax(parameterMax);
    }
  }, [isRangeDialogOpen, parameterMin, parameterMax]);

  const fetchDataStats = async (filename: string, targetTime?: string) => {
    if (!satelliteMapping) return;
    setIsLoadingStats(true);
    try {
      let apiUrl = `http://localhost:8000/api/v1/satellites/${satelliteMapping.satellite}/${satelliteMapping.parameter}/stats/${filename}`;
      if (targetTime)
        apiUrl += `?target_time=${encodeURIComponent(targetTime)}`;
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
      const targetTime =
        timeRange.granularity === "all" ? "all" : timeRange.start.toISOString();
      params.append("target_time", targetTime);
      params.append("mode", timeRange.granularity);
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

  const extractTimeFromSentinel3Filename = (filename: string): Date | null => {
    const timeMatch = filename.match(/(\d{8})_(\d{6})\.png$/);
    if (timeMatch) {
      const dateStr = timeMatch[1];
      const timeStr = timeMatch[2];
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

  const findBestFileForTime = (files: any[], selectedTime: Date) => {
    if (timeRange.granularity === "all") {
      const endTime = timeRange.end;
      console.log("All mode - endTime:", endTime, "files count:", files.length);
      let bestFile = null;
      let bestTimeDiff = Infinity;
      for (const file of files) {
        let fileTime: Date | null = null;
        if (parameter === "ssth") {
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
          fileTime = extractTimeFromSentinel3Filename(file.filename);
        }
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
      return bestFile || files[0];
    }

    if (timeRange.granularity === "day" || timeRange.granularity === "week") {
      let bestFile = null;
      let bestTimeDiff = Infinity;
      for (const file of files) {
        let fileTime: Date | null = null;
        if (parameter === "ssth") {
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
          fileTime = extractTimeFromSentinel3Filename(file.filename);
        }
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
    console.log(`Range effect triggered for ${parameter}:`, {
      appliedMin,
      appliedMax,
      availableFiles: availableFiles.length,
      currentTimestamp,
    });
    if (appliedMin || appliedMax) {
      if (availableFiles.length > 0 && currentTimestamp) {
        const currentFile = findBestFileForTime(
          availableFiles,
          timeRange.start
        );
        if (currentFile) {
          const handleNCFilename = async () => {
            let ncFilename;
            if (parameter === "ssth") {
              ncFilename = currentFile.filename.replace(".png", ".nc");
            } else {
              try {
                if (!getFiles) {
                  console.warn("getFiles function not available");
                  ncFilename = getSentinel3FallbackFilename(parameter);
                } else {
                  const ncFiles = await getFiles?.(parameter, "nc");
                  if (ncFiles && ncFiles.length > 0) {
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
          handleNCFilename();
        }
      }
    } else {
      console.log(`Clearing filtered image for ${parameter}`);
      setFilteredImageUrl(null);
    }
  }, [appliedMin, appliedMax, availableFiles, currentTimestamp, parameter]);

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
    if (satelliteMapping && availableFiles.length > 0) {
      console.log("All mode - timeRange changed:", {
        start: timeRange.start,
        end: timeRange.end,
        granularity: timeRange.granularity,
      });
      let targetFile: any = null;
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
        const handleStatsRetrieval = async () => {
          let ncFilename;
          if (parameter === "ssth") {
            ncFilename = targetFile.filename.replace(".png", ".nc");
          } else {
            try {
              const ncFiles = await getFiles?.(parameter, "nc");
              if (ncFiles && ncFiles.length > 0) {
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
          const targetTime =
            timeRange.granularity === "all"
              ? "all"
              : timeRange.start.toISOString();
          console.log(
            `Fetching stats for ${parameter} using NC file: ${ncFilename} at time: ${targetTime}`
          );
          fetchDataStats(ncFilename, targetTime);
        };
        handleStatsRetrieval();

        if (imageUrl === pngUrl) return;
        setIsLoading(true);
        setImageError(false);
        console.log(`Loading ${parameter} image:`, targetFile.filename);
        console.log(`Image URL: ${pngUrl}`);

        const img = new Image();
        img.onload = () => {
          setImageUrl(pngUrl);
          setIsLoading(false);
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
      setIsLoading(false);
      setImageUrl(null);
      setImageError(true);
    } else {
      setIsLoading(false);
      setImageUrl(null);
      setImageError(false);
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

  useEffect(() => {
    if (
      imageDimensions.width &&
      imageDimensions.height &&
      containerDimensions.width &&
      containerDimensions.height
    ) {
      const scaleX = containerDimensions.width / imageDimensions.width;
      const scaleY = containerDimensions.height / imageDimensions.height;
      const newBaseScale = Math.min(scaleX, scaleY);
      setBaseScale(newBaseScale);
      setPanPosition({ x: 0, y: 0 });
    }
  }, [imageDimensions, containerDimensions]);

  const constrainPan = (
    x: number,
    y: number,
    zoom: number,
    containerWidth: number,
    containerHeight: number
  ) => {
    if (zoom <= 1) return { x: 0, y: 0 };
    const displayScale = baseScale * zoom;
    const displayedWidth = imageDimensions.width * displayScale;
    const displayedHeight = imageDimensions.height * displayScale;
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
    const scaleFactor = newZoom / zoomLevel;
    const newPanX = panPosition.x * scaleFactor;
    const newPanY = panPosition.y * scaleFactor;
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
    const scaleFactor = newZoom / zoomLevel;
    const newPanX = pointX - (pointX - panPosition.x) * scaleFactor;
    const newPanY = pointY - (pointY - panPosition.y) * scaleFactor;
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

  const handleImageLoad = (e: React.SyntheticEvent<HTMLImageElement>) => {
    const img = e.currentTarget;
    setImageDimensions({
      width: img.naturalWidth,
      height: img.naturalHeight,
    });
  };

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
        background: `radial-gradient(ellipse at 20% 30%, #0a1a2e 0%, #16213e 40%, #1e3a8a 80%, #3b82f6 100%), linear-gradient(135deg, #0f172a 0%, #1e3a8a 30%, #3b82f6 60%, #60a5fa 100%)`,
        backgroundBlendMode: "multiply, normal",
      }}
    >
      {imageUrl && satelliteMapping ? (
        <div
          ref={setImageContainer}
          className="absolute inset-0 w-full h-full flex items-center justify-center overflow-hidden cursor-grab"
          style={{
            background: `radial-gradient(ellipse at center, #0a1a2e 0%, #16213e 30%, #1e3a8a 70%, #3b82f6 100%), linear-gradient(135deg, #0f172a 0%, #1e3a8a 50%, #3b82f6 100%)`,
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
          <div className="absolute inset-0 bg-black/10 pointer-events-none"></div>
          {isGeneratingFilteredImage && (
            <div className="absolute inset-0 flex items-center justify-center bg-black/50 rounded-lg">
              <div className="text-white text-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-white mx-auto mb-2"></div>
                <div className="text-sm">Generating filtered image...</div>
              </div>
            </div>
          )}
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
        {(appliedMin || appliedMax) && (
          <Badge className="bg-blue-500/20 backdrop-blur text-blue-100 border-blue-400/30 whitespace-nowrap">
            <div className="text-xs">
              Filtered: {appliedMin || "min"} - {appliedMax || "max"}
            </div>
          </Badge>
        )}
      </div>

      <div className="absolute bottom-4 left-4 flex flex-col gap-2">
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
                            const response = await fetch(
                              "http://localhost:8000/api/v1/open-path",
                              {
                                method: "POST",
                                headers: { "Content-Type": "application/json" },
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
                            try {
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
        <Dialog open={isRangeDialogOpen} onOpenChange={setIsRangeDialogOpen}>
          <DialogTrigger asChild>
            <Button
              variant="outline"
              size="sm"
              className="bg-white/20 backdrop-blur text-white border-white/30 hover:bg-white/30 w-fit"
              title="Set parameter value range"
            >
              <Settings className="h-3 w-3 mr-1" />
              Filter Range
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle>Set Parameter Value Range</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              {isLoadingStats ? (
                <div className="flex items-center justify-center py-8">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                </div>
              ) : dataStats ? (
                <>
                  <div className="p-3 bg-blue-50 rounded border border-blue-200">
                    <p className="text-xs text-blue-700 font-medium mb-1">
                      Data Statistics:
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
                  <div className="space-y-3">
                    <div>
                      <Label
                        htmlFor="min-value"
                        className="text-sm font-medium"
                      >
                        Minimum Value ({dataStats.units})
                      </Label>
                      <Input
                        id="min-value"
                        type="number"
                        placeholder={dataStats.min.toFixed(3)}
                        value={tempMin}
                        onChange={(e) => setTempMin(e.target.value)}
                        className="mt-1"
                        step="0.001"
                      />
                    </div>
                    <div>
                      <Label
                        htmlFor="max-value"
                        className="text-sm font-medium"
                      >
                        Maximum Value ({dataStats.units})
                      </Label>
                      <Input
                        id="max-value"
                        type="number"
                        placeholder={dataStats.max.toFixed(3)}
                        value={tempMax}
                        onChange={(e) => setTempMax(e.target.value)}
                        className="mt-1"
                        step="0.001"
                      />
                    </div>
                  </div>
                </>
              ) : (
                <div className="text-center text-gray-500 py-4">
                  No statistics available for this parameter
                </div>
              )}
              <div className="flex justify-between gap-2">
                <Button
                  variant="outline"
                  onClick={() => {
                    setTempMin("");
                    setTempMax("");
                    setParameterMin("");
                    setParameterMax("");
                    setAppliedMin("");
                    setAppliedMax("");
                    setIsRangeDialogOpen(false);
                  }}
                >
                  Clear
                </Button>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    onClick={() => setIsRangeDialogOpen(false)}
                  >
                    Cancel
                  </Button>
                  <Button
                    onClick={() => {
                      setParameterMin(tempMin);
                      setParameterMax(tempMax);
                      setAppliedMin(tempMin);
                      setAppliedMax(tempMax);
                      setIsRangeDialogOpen(false);
                    }}
                  >
                    Apply
                  </Button>
                </div>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      <div className="absolute top-4 right-4 flex flex-col gap-3 z-10">
        <div className="bg-white/20 backdrop-blur border border-white/30 rounded-lg p-3 min-w-[160px]">
          <div className="text-white text-xs text-center mb-2 font-medium">
            Zoom: {Math.round(zoomLevel * 100)}%
          </div>
          <Slider
            value={[zoomLevel]}
            onValueChange={handleZoomChange}
            min={0.5}
            max={5}
            step={0.1}
            className="w-full"
          />
          <div className="flex justify-between text-white text-xs mt-1 opacity-75">
            <span>0.5x</span>
            <span>5x</span>
          </div>
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

      <div className="absolute top-4 right-20">
        <Badge className="bg-green-500/20 backdrop-blur text-green-100 border-green-400/30 animate-pulse">
          <Zap className="h-3 w-3 mr-1" />
          Live
        </Badge>
      </div>
    </div>
  );
}

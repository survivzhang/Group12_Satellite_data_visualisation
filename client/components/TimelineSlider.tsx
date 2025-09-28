"use client";

import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Clock,
  Calendar,
  Play,
  Pause,
  ChevronLeft,
  ChevronRight,
  SkipBack,
  SkipForward,
} from "lucide-react";
import { TimeRange } from "@/types/research";

interface TimelineSliderProps {
  timeRange: TimeRange;
  onChange: (range: TimeRange) => void;
  variant?: "glass";
}

export function TimelineSlider({
  timeRange,
  onChange,
  variant = "glass",
}: TimelineSliderProps) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentPosition, setCurrentPosition] = useState(0);
  const lastTimeRef = useRef<number>(0);

  const granularityOptions = [
    { id: "day", label: "Day (24h)", duration: 24 * 60 * 60 * 1000 },
    { id: "week", label: "Week (7 days)", duration: 7 * 24 * 60 * 60 * 1000 },
    { id: "all", label: "All Data", duration: null },
  ];

  const currentGranularity =
    granularityOptions.find((g) => g.id === timeRange.granularity) ||
    granularityOptions[0];

  // 动态获取数据时间范围
  const [dataTimeRange, setDataTimeRange] = useState<{
    start: Date;
    end: Date;
  } | null>(null);

  // 获取数据时间范围的函数 - 获取所有参数的并集时间范围
  const fetchDataTimeRange = async () => {
    try {
      // 定义所有参数
      const allParameters = [
        { satellite: "himawari", parameter: "sst" },
        { satellite: "sentinel3a", parameter: "sst" },
        { satellite: "sentinel3b", parameter: "sst" },
        { satellite: "sentinel3a", parameter: "chl" },
        { satellite: "sentinel3b", parameter: "chl" },
      ];

      const allTimes: Date[] = [];

      // 获取所有参数的时间范围
      for (const param of allParameters) {
        try {
          const response = await fetch(
            `http://localhost:8000/api/v1/satellites/${param.satellite}/${param.parameter}/files`
          );
          if (response.ok) {
            const files = await response.json();
            if (files && files.length > 0) {
              // 解析文件名获取时间
              const times = files
                .map((file: any) => {
                  let fileTime: Date | null = null;

                  if (param.satellite === "himawari") {
                    // Himawari 文件格式: YYYYMMDDHHMMSS.png
                    const timeMatch =
                      file.filename.match(/(\d{8})(\d{6})\.png$/);
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
                    // Sentinel-3 文件格式: YYYYMMDD_HHMMSS.png
                    const timeMatch = file.filename.match(
                      /(\d{8})_(\d{6})\.png$/
                    );
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
                  }
                  return fileTime;
                })
                .filter((time: Date | null) => time !== null);

              allTimes.push(...times);
            }
          }
        } catch (error) {
          console.warn(
            `Failed to fetch files for ${param.satellite} ${param.parameter}:`,
            error
          );
        }
      }

      // 计算并集时间范围
      if (allTimes.length > 0) {
        allTimes.sort((a: Date, b: Date) => a.getTime() - b.getTime());
        setDataTimeRange({
          start: allTimes[0],
          end: allTimes[allTimes.length - 1],
        });
        console.log(
          `Data time range: ${allTimes[0].toISOString()} to ${allTimes[
            allTimes.length - 1
          ].toISOString()}`
        );
      } else {
        // 如果没有获取到任何数据，使用默认时间范围
        setDataTimeRange({
          start: new Date("2025-09-12T00:00:00Z"),
          end: new Date(),
        });
      }
    } catch (error) {
      console.error("Failed to fetch data time range:", error);
      // 使用默认时间范围作为fallback
      setDataTimeRange({
        start: new Date("2025-09-12T00:00:00Z"),
        end: new Date(),
      });
    }
  };

  // 在组件挂载时获取数据时间范围
  useEffect(() => {
    fetchDataTimeRange();
  }, []);

  // 使用数据时间范围或默认值
  const fixedStartDate =
    dataTimeRange?.start || new Date("2025-09-12T00:00:00Z");
  const fixedEndDate = dataTimeRange?.end || new Date();
  const fullDuration = fixedEndDate.getTime() - fixedStartDate.getTime();

  // 根据当前模式计算时间轴范围
  const getTimeRange = () => {
    if (timeRange.granularity === "day") {
      // Day 模式：显示当天的24小时（00:00-23:59 UTC）
      const today = new Date();
      const dayStart = new Date(today);
      dayStart.setUTCHours(0, 0, 0, 0);
      const dayEnd = new Date(dayStart);
      dayEnd.setUTCHours(23, 59, 59, 999);
      return { start: dayStart, end: dayEnd };
    } else if (timeRange.granularity === "week") {
      // Week 模式：基于当前时间显示7天范围（UTC）
      const today = new Date();
      const weekEnd = new Date(today);
      const weekStart = new Date(weekEnd);
      weekStart.setDate(weekStart.getDate() - 6); // 改为6天，包含今天
      return { start: weekStart, end: weekEnd };
    } else {
      // All 模式：显示完整时间范围
      return { start: fixedStartDate, end: fixedEndDate };
    }
  };

  const timeRange_actual = getTimeRange();
  const totalDuration =
    timeRange_actual.end.getTime() - timeRange_actual.start.getTime();

  // Auto-play functionality
  useEffect(() => {
    if (!isPlaying) return;
    const interval = setInterval(() => {
      setCurrentPosition((prev) => {
        const next = prev + 1;
        if (next > 100) {
          setIsPlaying(false);
          return 100;
        }
        return next;
      });
    }, 500);
    return () => clearInterval(interval);
  }, [isPlaying]);

  // Update time range based on position
  useEffect(() => {
    let currentTime;

    if (timeRange.granularity === "all") {
      // All模式：基于完整时间范围计算当前时间
      currentTime = new Date(
        fixedStartDate.getTime() + (fullDuration * currentPosition) / 1000
      );
    } else {
      // Day和Week模式：基于各自的时间范围计算当前时间
      currentTime = new Date(
        timeRange_actual.start.getTime() +
          (totalDuration * currentPosition) / 1000
      );
    }

    const currentTimeMs = currentTime.getTime();

    // Only call onChange if time really changed (avoid repeat calls)
    if (Math.abs(currentTimeMs - lastTimeRef.current) > 1000) {
      lastTimeRef.current = currentTimeMs;

      if (timeRange.granularity === "all") {
        // all 模式：显示所有数据，但时间范围基于当前时间轴位置
        console.log(
          "All mode - currentPosition:",
          currentPosition,
          "currentTime:",
          currentTime,
          "startTime:",
          fixedStartDate,
          "endTime:",
          currentTime
        );
        onChange({
          start: fixedStartDate,
          end: currentTime, // 从开始到当前时间轴位置
          granularity: "all",
        });
      } else if (timeRange.granularity === "day") {
        // day 模式：基于当前滑动位置显示当天24小时
        const dayStart = new Date(currentTime);
        dayStart.setUTCHours(0, 0, 0, 0);
        const dayEnd = new Date(dayStart);
        dayEnd.setUTCHours(23, 59, 59, 999);

        onChange({
          start: dayStart,
          end: currentTime, // 使用当前滑动位置时间，而不是固定的23:59
          granularity: "day",
        });
      } else if (timeRange.granularity === "week") {
        // week 模式：基于当前滑动位置显示7天范围
        const weekEnd = new Date(currentTime);
        const weekStart = new Date(weekEnd);
        weekStart.setDate(weekStart.getDate() - 6); // 当前时间往前推6天，包含当前时间

        onChange({
          start: weekStart,
          end: weekEnd,
          granularity: "week",
        });
      }
    }
    // eslint-disable-next-line
  }, [currentPosition, timeRange.granularity, totalDuration, onChange]);

  const handleGranularityChange = (granularity: string) => {
    // 获取当前滑动位置对应的时间
    const currentTime = getCurrentDateTime();

    if (granularity === "all") {
      // all 模式：显示所有数据，时间范围设为整个数据范围
      onChange({
        start: fixedStartDate,
        end: currentTime, // 使用当前滑动位置时间
        granularity: "all",
      });
    } else if (granularity === "day") {
      // day 模式：基于当前滑动位置显示当天24小时数据
      const dayStart = new Date(currentTime);
      dayStart.setUTCHours(0, 0, 0, 0);
      const dayEnd = new Date(dayStart);
      dayEnd.setUTCHours(23, 59, 59, 999);

      onChange({
        start: dayStart,
        end: currentTime, // 使用当前滑动位置时间
        granularity: "day",
      });
    } else if (granularity === "week") {
      // week 模式：基于当前滑动位置显示7天范围
      const weekEnd = new Date(currentTime);
      const weekStart = new Date(weekEnd);
      weekStart.setDate(weekStart.getDate() - 6); // 当前时间往前推6天，包含当前时间

      onChange({
        start: weekStart,
        end: currentTime, // 使用当前滑动位置时间
        granularity: "week",
      });
    }
  };

  const getCurrentDateTime = () => {
    const currentTime = new Date(
      timeRange_actual.start.getTime() +
        (totalDuration * currentPosition) / 1000
    );
    return currentTime;
  };

  const formatDateRange = () => {
    const currentTime = getCurrentDateTime();

    switch (timeRange.granularity) {
      case "day":
        return currentTime.toLocaleString("en-US", {
          weekday: "long",
          month: "long",
          day: "numeric",
          year: "numeric",
          hour: "2-digit",
          minute: "2-digit",
          timeZone: "UTC",
        });
      case "week":
        return `Week of ${currentTime.toLocaleDateString("en-US", {
          month: "short",
          day: "numeric",
          year: "numeric",
          timeZone: "UTC",
        })}`;
      case "all":
        // 显示所有数据的实际时间范围
        const startDate = fixedStartDate.toLocaleDateString("en-US", {
          month: "short",
          day: "numeric",
          year: "numeric",
          timeZone: "UTC",
        });
        const endDate = fixedEndDate.toLocaleDateString("en-US", {
          month: "short",
          day: "numeric",
          year: "numeric",
          timeZone: "UTC",
        });
        return `All Data (${startDate} - ${endDate})`;
      default:
        return currentTime.toLocaleDateString();
    }
  };

  // Styling classes for glass effect
  const glassClass =
    "space-y-6 bg-white/10 backdrop-blur-md border border-white/20 rounded-xl p-6 shadow-xl text-white";

  return (
    <div className={variant === "glass" ? glassClass : ""}>
      {/* Granularity Selection */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2 text-sm text-cyan-200">
          <Clock className="h-4 w-4" />
          Time Resolution:
        </div>
        <div className="flex gap-2">
          {granularityOptions.map((option) => (
            <Button
              key={option.id}
              variant={
                timeRange.granularity === option.id ? "default" : "outline"
              }
              size="sm"
              onClick={() => handleGranularityChange(option.id)}
              className={`h-8 ${
                timeRange.granularity === option.id
                  ? "bg-cyan-600 hover:bg-cyan-700 text-white border-none"
                  : "bg-white/10 text-cyan-200 border-white/20 hover:bg-cyan-900/20"
              }`}
            >
              {option.label}
            </Button>
          ))}
        </div>
      </div>

      {/* Current Time Display */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Calendar className="h-5 w-5 text-cyan-200" />
          <div>
            <div className="font-medium text-white">{formatDateRange()}</div>
            <div className="text-sm text-cyan-200">
              Viewing {currentGranularity.label.toLowerCase()} resolution •
              September 12, 2025 to now (Local Time)
            </div>
          </div>
        </div>
        <Badge
          variant="outline"
          className="bg-cyan-600/20 border-cyan-400 text-cyan-100"
        >
          {(() => {
            const currentTime = getCurrentDateTime();
            const currentDuration =
              currentTime.getTime() - timeRange_actual.start.getTime();
            const progressPercent = Math.round(
              (currentDuration / totalDuration) * 100
            );
            return `Progress: ${Math.min(progressPercent, 100)}%`;
          })()}
        </Badge>
      </div>

      {/* Timeline Slider */}
      <div className="space-y-8">
        <div className="relative">
          <input
            type="range"
            min="0"
            max="1000"
            value={currentPosition}
            onChange={(e) => setCurrentPosition(Number(e.target.value))}
            className="w-full h-2 bg-cyan-900/30 rounded-lg appearance-none cursor-pointer slider"
            style={{
              background: `linear-gradient(to right, #06b6d4 0%, #06b6d4 ${
                currentPosition / 10
              }%, #0e374a ${currentPosition / 10}%, #0e374a 100%)`,
            }}
          />

          {/* Timeline markers */}
          <div className="absolute -bottom-6 left-0 right-0 flex justify-between text-xs text-cyan-200">
            {Array.from({ length: 7 }, (_, i) => {
              const markerTime = new Date(
                timeRange_actual.start.getTime() + (totalDuration * i) / 6
              );
              const utcTime = markerTime.toLocaleDateString("en-US", {
                month: "short",
                day: "numeric",
                hour: "2-digit",
                minute: "2-digit",
                timeZone: "UTC",
              });
              return <span key={i}>{utcTime}</span>;
            })}
          </div>
        </div>

        {/* Playback Controls */}
        <div className="flex items-center justify-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setCurrentPosition(0)}
            className="h-8 w-8 p-0 bg-white/10 text-cyan-200 border-white/20 hover:bg-cyan-900/20"
            title="Start"
          >
            <SkipBack className="h-3 w-3" />
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={() => setCurrentPosition(Math.max(0, currentPosition - 5))}
            className="h-8 w-8 p-0 bg-white/10 text-cyan-200 border-white/20 hover:bg-cyan-900/20"
            title="Step Back"
          >
            <ChevronLeft className="h-3 w-3" />
          </Button>

          <Button
            variant={isPlaying ? "secondary" : "default"}
            size="sm"
            onClick={() => setIsPlaying(!isPlaying)}
            className={`h-8 w-16 ${
              isPlaying
                ? "bg-orange-100 hover:bg-orange-200 text-orange-800"
                : "bg-cyan-600 hover:bg-cyan-700 text-white"
            }`}
            title={isPlaying ? "Pause" : "Play"}
          >
            {isPlaying ? (
              <Pause className="h-3 w-3" />
            ) : (
              <Play className="h-3 w-3" />
            )}
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={() =>
              setCurrentPosition(Math.min(100, currentPosition + 5))
            }
            className="h-8 w-8 p-0 bg-white/10 text-cyan-200 border-white/20 hover:bg-cyan-900/20"
            title="Step Forward"
          >
            <ChevronRight className="h-3 w-3" />
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={() => setCurrentPosition(100)}
            className="h-8 w-8 p-0 bg-white/10 text-cyan-200 border-white/20 hover:bg-cyan-900/20"
            title="End"
          >
            <SkipForward className="h-3 w-3" />
          </Button>
        </div>
      </div>

      <style jsx>{`
        .slider::-webkit-slider-thumb {
          appearance: none;
          width: 20px;
          height: 20px;
          border-radius: 50%;
          background: #06b6d4;
          cursor: pointer;
          border: 2px solid white;
          box-shadow: 0 2px 6px rgba(6, 182, 212, 0.3);
        }

        .slider::-moz-range-thumb {
          width: 20px;
          height: 20px;
          border-radius: 50%;
          background: #06b6d4;
          cursor: pointer;
          border: 2px solid white;
          box-shadow: 0 2px 6px rgba(6, 182, 212, 0.3);
        }
      `}</style>
    </div>
  );
}

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

export function TimelineSlider({ timeRange, onChange, variant = "glass" }: TimelineSliderProps) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentPosition, setCurrentPosition] = useState(0);
  const lastTimeRef = useRef<number>(0);

  const granularityOptions = [
    { id: "months", label: "Months", duration: 30 * 24 * 60 * 60 * 1000 },
    { id: "weeks", label: "Weeks", duration: 7 * 24 * 60 * 60 * 1000 },
    { id: "days", label: "Days", duration: 24 * 60 * 60 * 1000 },
    { id: "hours", label: "Hours", duration: 60 * 60 * 1000 },
  ];

  const currentGranularity =
    granularityOptions.find((g) => g.id === timeRange.granularity) || granularityOptions[3];

  // Fixed date range: August 10, 2025 to now
  const fixedStartDate = new Date("2025-08-10T00:00:00Z");
  const fixedEndDate = new Date();
  const totalDuration = fixedEndDate.getTime() - fixedStartDate.getTime();

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
    const currentTime = new Date(
      fixedStartDate.getTime() + (totalDuration * currentPosition) / 100
    );
    const currentTimeMs = currentTime.getTime();

    // Only call onChange if time really changed (avoid repeat calls)
    if (Math.abs(currentTimeMs - lastTimeRef.current) > 1000) {
      lastTimeRef.current = currentTimeMs;

      // For PNG display, we want the exact current time as the start time
      const windowSize = currentGranularity.duration;
      const windowEnd = new Date(currentTime.getTime() + windowSize / 2);

      onChange({
        start: currentTime,
        end:
          Math.min(windowEnd.getTime(), fixedEndDate.getTime()) < fixedEndDate.getTime()
            ? windowEnd
            : fixedEndDate,
        granularity: timeRange.granularity,
      });
    }
    // eslint-disable-next-line
  }, [currentPosition, currentGranularity.duration, totalDuration, onChange]);

  const handleGranularityChange = (granularity: string) => {
    const option = granularityOptions.find((g) => g.id === granularity);
    if (option) {
      const currentTime = new Date(
        fixedStartDate.getTime() + (totalDuration * currentPosition) / 100
      );
      const center = currentTime;
      const newStart = new Date(center.getTime() - option.duration / 2);
      const newEnd = new Date(center.getTime() + option.duration / 2);

      onChange({
        start:
          Math.max(newStart.getTime(), fixedStartDate.getTime()) > fixedStartDate.getTime()
            ? newStart
            : fixedStartDate,
        end:
          Math.min(newEnd.getTime(), fixedEndDate.getTime()) < fixedEndDate.getTime()
            ? newEnd
            : fixedEndDate,
        granularity: granularity as any,
      });
    }
  };

  const getCurrentDateTime = () => {
    const currentTime = new Date(
      fixedStartDate.getTime() + (totalDuration * currentPosition) / 100
    );
    return currentTime;
  };

  const formatDateRange = () => {
    const currentTime = getCurrentDateTime();

    switch (timeRange.granularity) {
      case "months":
        return currentTime.toLocaleDateString("en-US", { month: "long", year: "numeric" });
      case "weeks":
        return `Week of ${currentTime.toLocaleDateString("en-US", {
          month: "short",
          day: "numeric",
          year: "numeric",
        })}`;
      case "days":
        return currentTime.toLocaleDateString("en-US", {
          weekday: "long",
          month: "long",
          day: "numeric",
          year: "numeric",
        });
      case "hours":
        return currentTime.toLocaleString("en-US", {
          weekday: "long",
          month: "long",
          day: "numeric",
          year: "numeric",
          hour: "2-digit",
          minute: "2-digit",
        });
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
              variant={timeRange.granularity === option.id ? "default" : "outline"}
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
              Viewing {currentGranularity.label.toLowerCase()} resolution • August 10, 2025 to now (Local Time)
            </div>
          </div>
        </div>
        <Badge variant="outline" className="bg-cyan-600/20 border-cyan-400 text-cyan-100">
          {(() => {
            const currentTime = getCurrentDateTime();
            const startLocal = new Date("2025-08-10T00:00:00Z");
            const endLocal = new Date();
            const totalHours = 12;
            const currentHour =
              Math.floor((currentTime.getTime() - fixedStartDate.getTime()) / (1000 * 60 * 60)) + 1;
            return `Hour ${Math.min(currentHour, totalHours)} of ${totalHours}`;
          })()}
        </Badge>
      </div>

      {/* Timeline Slider */}
      <div className="space-y-8">
        <div className="relative">
          <input
            type="range"
            min="0"
            max="100"
            value={currentPosition}
            onChange={(e) => setCurrentPosition(Number(e.target.value))}
            className="w-full h-2 bg-cyan-900/30 rounded-lg appearance-none cursor-pointer slider"
            style={{
              background: `linear-gradient(to right, #06b6d4 0%, #06b6d4 ${currentPosition}%, #0e374a ${currentPosition}%, #0e374a 100%)`,
            }}
          />

          {/* Timeline markers */}
          <div className="absolute -bottom-6 left-0 right-0 flex justify-between text-xs text-cyan-200">
            {Array.from({ length: 7 }, (_, i) => {
              const utcTime = new Date("2025-08-10T00:00:00Z");
              utcTime.setUTCHours(i * 2);
              const localTime = utcTime.toLocaleTimeString("en-US", {
                hour: "2-digit",
                minute: "2-digit",
                hour12: false,
              });
              return <span key={i}>{localTime}</span>;
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
            {isPlaying ? <Pause className="h-3 w-3" /> : <Play className="h-3 w-3" />}
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={() => setCurrentPosition(Math.min(100, currentPosition + 5))}
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

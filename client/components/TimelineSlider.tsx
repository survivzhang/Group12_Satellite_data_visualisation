"use client";

import { useState, useEffect, useCallback, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { 
  Calendar, 
  ChevronLeft, 
  ChevronRight, 
  Play, 
  Pause,
  SkipBack,
  SkipForward,
  Clock
} from 'lucide-react';
import { TimeRange } from '@/types/research';

interface TimelineSliderProps {
  timeRange: TimeRange;
  onChange: (range: TimeRange) => void;
}

export function TimelineSlider({ timeRange, onChange }: TimelineSliderProps) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentPosition, setCurrentPosition] = useState(0);
  const lastTimeRef = useRef<number>(0);
  
  const granularityOptions = [
    { id: 'months', label: 'Months', duration: 30 * 24 * 60 * 60 * 1000 },
    { id: 'weeks', label: 'Weeks', duration: 7 * 24 * 60 * 60 * 1000 },
    { id: 'days', label: 'Days', duration: 24 * 60 * 60 * 1000 },
    { id: 'hours', label: 'Hours', duration: 60 * 60 * 1000 }
  ];

  const currentGranularity = granularityOptions.find(g => g.id === timeRange.granularity) || granularityOptions[2];
  
  // Fixed date range: March 1, 2025 (12 hours for testing)
  const fixedStartDate = new Date('2025-03-01T00:00:00Z'); // March 1, 2025 00:00 UTC
  const fixedEndDate = new Date('2025-03-01T12:00:00Z'); // March 1, 2025 12:00 UTC
  const totalDuration = fixedEndDate.getTime() - fixedStartDate.getTime();

  // Auto-play functionality
  useEffect(() => {
    if (!isPlaying) return;

    const interval = setInterval(() => {
      setCurrentPosition(prev => {
        const next = prev + 1;
        if (next > 100) {
          setIsPlaying(false);
          return 0;
        }
        return next;
      });
    }, 500);

    return () => clearInterval(interval);
  }, [isPlaying]);

  // Update time range based on position
  useEffect(() => {
    const currentTime = new Date(fixedStartDate.getTime() + (totalDuration * currentPosition) / 100);
    const currentTimeMs = currentTime.getTime();
    
    // 只有当时间真正变化时才调用onChange（避免重复调用）
    if (Math.abs(currentTimeMs - lastTimeRef.current) > 1000) { // 大于1秒差异
      lastTimeRef.current = currentTimeMs;
      
      console.log(`Timeline position: ${currentPosition}%`);
      console.log(`Current time calculated: ${currentTime.toISOString()}`);
      
      // For PNG display, we want the exact current time as the start time
      const windowSize = currentGranularity.duration;
      const windowEnd = new Date(currentTime.getTime() + windowSize / 2);
      
      onChange({
        start: currentTime, // 使用确切的当前时间
        end: Math.min(windowEnd.getTime(), fixedEndDate.getTime()) < fixedEndDate.getTime() ? windowEnd : fixedEndDate,
        granularity: timeRange.granularity
      });
    }
  }, [currentPosition, currentGranularity.duration, totalDuration, onChange]);

  const handleGranularityChange = (granularity: string) => {
    const option = granularityOptions.find(g => g.id === granularity);
    if (option) {
      const currentTime = new Date(fixedStartDate.getTime() + (totalDuration * currentPosition) / 100);
      const center = currentTime;
      const newStart = new Date(center.getTime() - option.duration / 2);
      const newEnd = new Date(center.getTime() + option.duration / 2);
      
      onChange({
        start: Math.max(newStart.getTime(), fixedStartDate.getTime()) > fixedStartDate.getTime() ? newStart : fixedStartDate,
        end: Math.min(newEnd.getTime(), fixedEndDate.getTime()) < fixedEndDate.getTime() ? newEnd : fixedEndDate,
        granularity: granularity as any
      });
    }
  };

  const getCurrentDateTime = () => {
    const currentTime = new Date(fixedStartDate.getTime() + (totalDuration * currentPosition) / 100);
    return currentTime;
  };

  const formatDateRange = () => {
    const currentTime = getCurrentDateTime();
    
    switch (timeRange.granularity) {
      case 'months':
        return currentTime.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
      case 'weeks':
        return `Week of ${currentTime.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}`;
      case 'days':
        return currentTime.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' });
      case 'hours':
        return currentTime.toLocaleString('en-US', { 
          weekday: 'long', 
          month: 'long', 
          day: 'numeric', 
          year: 'numeric',
          hour: '2-digit', 
          minute: '2-digit' 
        });
      default:
        return currentTime.toLocaleDateString();
    }
  };

  return (
    <div className="space-y-6">
      {/* Granularity Selection */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2 text-sm text-slate-600">
          <Clock className="h-4 w-4" />
          Time Resolution:
        </div>
        <div className="flex gap-2">
          {granularityOptions.map(option => (
            <Button
              key={option.id}
              variant={timeRange.granularity === option.id ? "default" : "outline"}
              size="sm"
              onClick={() => handleGranularityChange(option.id)}
              className={`h-8 ${
                timeRange.granularity === option.id 
                  ? 'bg-blue-600 hover:bg-blue-700' 
                  : 'hover:bg-blue-50'
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
          <Calendar className="h-5 w-5 text-slate-600" />
          <div>
            <div className="font-medium text-slate-800">
              {formatDateRange()}
            </div>
            <div className="text-sm text-slate-500">
              Viewing {currentGranularity.label.toLowerCase()} resolution • March 1, 2025 (Local Time)
            </div>
          </div>
        </div>
        <Badge variant="outline" className="bg-blue-50 border-blue-200 text-blue-800">
          {(() => {
            const currentTime = getCurrentDateTime();
            const startLocal = new Date('2025-03-01T00:00:00Z');
            const endLocal = new Date('2025-03-01T12:00:00Z');
            const totalHours = 12;
            const currentHour = Math.floor((currentTime.getTime() - fixedStartDate.getTime()) / (1000 * 60 * 60)) + 1;
            return `Hour ${Math.min(currentHour, totalHours)} of ${totalHours}`;
          })()}
        </Badge>
      </div>

      {/* Timeline Slider */}
      <div className="space-y-4">
        <div className="relative">
          <input
            type="range"
            min="0"
            max="100"
            value={currentPosition}
            onChange={(e) => setCurrentPosition(Number(e.target.value))}
            className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer slider"
            style={{
              background: `linear-gradient(to right, #3b82f6 0%, #3b82f6 ${currentPosition}%, #e2e8f0 ${currentPosition}%, #e2e8f0 100%)`
            }}
          />
          
          {/* Timeline markers */}
          <div className="absolute -bottom-6 left-0 right-0 flex justify-between text-xs text-slate-500">
            {Array.from({length: 7}, (_, i) => {
              const utcTime = new Date('2025-03-01T00:00:00Z');
              utcTime.setUTCHours(i * 2); // 每2小时一个标记
              const localTime = utcTime.toLocaleTimeString('en-US', { 
                hour: '2-digit', 
                minute: '2-digit',
                hour12: false 
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
            className="h-8 w-8 p-0"
          >
            <SkipBack className="h-3 w-3" />
          </Button>
          
          <Button 
            variant="outline" 
            size="sm"
            onClick={() => setCurrentPosition(Math.max(0, currentPosition - 5))}
            className="h-8 w-8 p-0"
          >
            <ChevronLeft className="h-3 w-3" />
          </Button>
          
          <Button 
            variant={isPlaying ? "secondary" : "default"}
            size="sm"
            onClick={() => setIsPlaying(!isPlaying)}
            className={`h-8 w-16 ${isPlaying ? 'bg-orange-100 hover:bg-orange-200 text-orange-800' : 'bg-blue-600 hover:bg-blue-700 text-white'}`}
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
            onClick={() => setCurrentPosition(Math.min(100, currentPosition + 5))}
            className="h-8 w-8 p-0"
          >
            <ChevronRight className="h-3 w-3" />
          </Button>
          
          <Button 
            variant="outline" 
            size="sm"
            onClick={() => setCurrentPosition(100)}
            className="h-8 w-8 p-0"
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
          background: #3b82f6;
          cursor: pointer;
          border: 2px solid white;
          box-shadow: 0 2px 6px rgba(59, 130, 246, 0.3);
        }
        
        .slider::-moz-range-thumb {
          width: 20px;
          height: 20px;
          border-radius: 50%;
          background: #3b82f6;
          cursor: pointer;
          border: 2px solid white;
          box-shadow: 0 2px 6px rgba(59, 130, 246, 0.3);
        }
      `}</style>
    </div>
  );
}
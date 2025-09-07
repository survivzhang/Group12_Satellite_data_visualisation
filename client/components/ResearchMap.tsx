"use client";

import { useState, useEffect, useMemo } from 'react';
import { Parameter, TimeRange } from '@/types/research';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { MapPin, Layers, Zap, Image as ImageIcon } from 'lucide-react';
import { useDataStore } from '@/hooks/useDataStore';

interface ResearchMapProps {
  parameter: string;
  timeRange: TimeRange;
  availableParameters: Parameter[];
  isFullscreen?: boolean;
}

// 卫星参数映射
const SATELLITE_MAPPING = {
  'ssth': { satellite: 'himawari', parameter: 'sst', staticPath: '/static/himawari/sst/png' },
  'sst-s3a': { satellite: 'sentinel3a', parameter: 'sst', staticPath: '/static/sentinel3a/sst/png' },
  'sst-s3b': { satellite: 'sentinel3b', parameter: 'sst', staticPath: '/static/sentinel3b/sst/png' },
  'chl-s3a': { satellite: 'sentinel3a', parameter: 'chl', staticPath: '/static/sentinel3a/chl/png' },
  'chl-s3b': { satellite: 'sentinel3b', parameter: 'chl', staticPath: '/static/sentinel3b/chl/png' }
};

export function ResearchMap({ parameter, timeRange, availableParameters, isFullscreen }: ResearchMapProps) {
  const [isLoading, setIsLoading] = useState(true);
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [imageError, setImageError] = useState(false);
  const [availableFiles, setAvailableFiles] = useState<any[]>([]);
  
  const { getParameterFiles } = useDataStore();
  const currentParam = availableParameters.find(p => p.id === parameter);
  const satelliteMapping = SATELLITE_MAPPING[parameter as keyof typeof SATELLITE_MAPPING];

  // 获取当前时间戳和文件名
  const currentTimestamp = useMemo(() => {
    if (!satelliteMapping) return null;
    
    // 确保使用UTC时间并向下舍入到最近的整点
    const utcDate = new Date(timeRange.start.getTime());
    utcDate.setUTCMinutes(0, 0, 0);
    
    // 不同卫星使用不同的时间戳格式
    if (parameter === 'ssth') {
      // Himawari格式: YYYYMMDDHHMMSS
      const year = utcDate.getUTCFullYear();
      const month = String(utcDate.getUTCMonth() + 1).padStart(2, '0');
      const day = String(utcDate.getUTCDate()).padStart(2, '0');
      const hour = String(utcDate.getUTCHours()).padStart(2, '0');
      return `${year}${month}${day}${hour}0000`;
    } else {
      // Sentinel-3格式: ISO时间戳
      return utcDate.toISOString().replace(/[:.]/g, '-').replace('Z', '');
    }
  }, [parameter, timeRange.start, satelliteMapping]);

  // 获取可用文件列表
  useEffect(() => {
    if (satelliteMapping) {
      getParameterFiles(parameter, 'png').then(files => {
        setAvailableFiles(files);
        console.log(`Available PNG files for ${parameter}:`, files);
      });
    }
  }, [parameter, satelliteMapping, getParameterFiles]);

  useEffect(() => {
    if (satelliteMapping && currentTimestamp && availableFiles.length > 0) {
      // 寻找最匹配的文件
      let targetFile = null;
      
      if (parameter === 'ssth') {
        // Himawari: 寻找精确匹配的时间戳文件
        targetFile = availableFiles.find(file => 
          file.filename.includes(currentTimestamp)
        );
      } else {
        // Sentinel-3: 寻找最接近时间的文件
        targetFile = availableFiles.find(file => {
          const fileTime = extractTimeFromFilename(file.filename);
          return fileTime && isTimeClose(fileTime, timeRange.start);
        });
        
        // 如果没找到精确匹配，使用最新的文件
        if (!targetFile && availableFiles.length > 0) {
          targetFile = availableFiles[0]; // 文件已按时间排序
        }
      }
      
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
        console.warn(`No suitable PNG file found for ${parameter} at ${currentTimestamp}`);
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
  }, [parameter, currentTimestamp, availableFiles, satelliteMapping, imageUrl, timeRange.start]);

  // 辅助函数：从文件名提取时间
  const extractTimeFromFilename = (filename: string): Date | null => {
    // 这里需要根据实际的Sentinel-3文件命名格式来实现
    // 示例实现，需要根据实际格式调整
    const timeMatch = filename.match(/(\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2})/);
    if (timeMatch) {
      return new Date(timeMatch[1].replace(/-/g, ':').replace('T', 'T') + 'Z');
    }
    return null;
  };

  // 辅助函数：检查时间是否接近
  const isTimeClose = (fileTime: Date, targetTime: Date, toleranceHours: number = 1): boolean => {
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
    <div className={`relative ${isFullscreen ? 'h-full' : 'h-96'} bg-gradient-to-br from-blue-900 via-blue-700 to-teal-600 rounded-lg overflow-hidden`}>
      {/* Show PNG image for supported satellites */}
      {imageUrl && satelliteMapping ? (
        <div className="absolute inset-0 w-full h-full">
          <img 
            src={imageUrl}
            alt={`${currentParam?.name} - ${currentTimestamp || 'loading'}`}
            className="w-full h-full object-cover rounded-lg"
            style={{ filter: 'contrast(1.1) brightness(1.1)' }}
          />
          {/* Overlay for better text readability */}
          <div className="absolute inset-0 bg-black/10"></div>
        </div>
      ) : (
        /* Placeholder for unsupported parameters or when image is not available */
        <div className="absolute inset-0 w-full h-full flex items-center justify-center bg-gradient-to-br from-slate-600 to-slate-800">
          <div className="text-center text-white/80">
            <div className="text-lg font-medium mb-2">
              {satelliteMapping && imageError ? 'Image not available' : `${currentParam?.name} Data`}
            </div>
            <div className="text-sm opacity-75">
              {satelliteMapping && imageError 
                ? `No satellite data for ${currentTimestamp || 'selected time'}`
                : satelliteMapping ? 'Loading satellite data...' : 'Visualization coming soon'
              }
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
              {satelliteMapping ? 'No data available' : 'Coming soon'}
            </>
          )}
        </Badge>
        {imageUrl && satelliteMapping && currentTimestamp && (
          <Badge className="bg-white/20 backdrop-blur text-white border-white/30">
            <div className="text-xs">
              {parameter === 'ssth' 
                ? new Date(`${currentTimestamp.substring(0,4)}-${currentTimestamp.substring(4,6)}-${currentTimestamp.substring(6,8)}T${currentTimestamp.substring(8,10)}:00:00Z`).toLocaleString()
                : timeRange.start.toLocaleString()
              }
            </div>
          </Badge>
        )}
      </div>

      {/* Legend */}
      <div className="absolute bottom-4 right-4 bg-white/90 backdrop-blur rounded-lg p-3">
        <div className="text-xs font-medium text-slate-700 mb-2 flex items-center gap-1">
          <Layers className="h-3 w-3" />
          Range
        </div>
        <div className="flex items-center gap-2">
          <div className="w-16 h-2 rounded-full bg-gradient-to-r from-blue-200 to-red-500"></div>
          <span className="text-xs text-slate-600">
            {currentParam?.unit}
          </span>
        </div>
      </div>

      {/* Live indicator */}
      <div className="absolute top-4 right-4">
        <Badge className="bg-green-500/20 backdrop-blur text-green-100 border-green-400/30 animate-pulse">
          <Zap className="h-3 w-3 mr-1" />
          Live
        </Badge>
      </div>
    </div>
  );
}
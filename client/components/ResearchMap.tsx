"use client";

import { useState, useEffect, useMemo } from 'react';
import { Parameter, TimeRange } from '@/types/research';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { MapPin, Zap, Image as ImageIcon } from 'lucide-react';

interface ResearchMapProps {
  parameter: string;
  timeRange: TimeRange;
  availableParameters: Parameter[];
  isFullscreen?: boolean;
  onClose?: () => void;
}

export function ResearchMap({ parameter, timeRange, availableParameters, isFullscreen, onClose }: ResearchMapProps) {
  const [isLoading, setIsLoading] = useState(true);
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [imageError, setImageError] = useState(false);
  
  const currentParam = availableParameters.find(p => p.id === parameter);

  // Memoize timestamp calculation to avoid infinite loops
  const currentTimestamp = useMemo(() => {
    if (parameter !== 'ssth') return null;
    
    // Ensure UTC time and round down to the nearest hour
    const utcDate = new Date(timeRange.start.getTime());
    utcDate.setUTCMinutes(0, 0, 0);
    
    // Format as YYYYMMDDHHMMSS for filename
    const year = utcDate.getUTCFullYear();
    const month = String(utcDate.getUTCMonth() + 1).padStart(2, '0');
    const day = String(utcDate.getUTCDate()).padStart(2, '0');
    const hour = String(utcDate.getUTCHours()).padStart(2, '0');
    
    const timestamp = `${year}${month}${day}${hour}0000`;
    // console.log(`Input date: ${timeRange.start.toISOString()}`);
    // console.log(`UTC date after rounding: ${utcDate.toISOString()}`);
    console.log(`Generated timestamp: ${timestamp}`);
    
    return timestamp;
  }, [parameter, timeRange.start]);

  useEffect(() => {
    if (parameter === 'ssth' && currentTimestamp) {
      const pngUrl = `http://localhost:8000/static/images/${currentTimestamp}.png`;
      
      // Avoid reloading the same image
      if (imageUrl === pngUrl) {
        return;
      }
      
      setIsLoading(true);
      setImageError(false);
      
      console.log(`Loading SSTH image for timestamp: ${currentTimestamp}`);
      console.log(`Image URL: ${pngUrl}`);
      
      // Check if image exists
      const img = new Image();
      img.onload = () => {
        setImageUrl(pngUrl);
        setIsLoading(false);
      };
      img.onerror = () => {
        console.warn(`PNG not found for ${currentTimestamp}`);
        setImageError(true);
        setImageUrl(null);
        setIsLoading(false);
      };
      img.src = pngUrl;
    } else {
      // For non-ssth parameters, show placeholder
      setIsLoading(false);
      setImageUrl(null);
      setImageError(false);
    }
  }, [parameter, currentTimestamp]);



  if (isLoading) {
    return (
      <div className="h-96 bg-slate-100 rounded-lg flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className={`relative ${isFullscreen ? 'h-full' : 'h-96'} rounded-lg overflow-hidden`} style={{
      background: `
        radial-gradient(ellipse at 20% 30%, #0a1a2e 0%, #16213e 40%, #1e3a8a 80%, #3b82f6 100%),
        linear-gradient(135deg, #0f172a 0%, #1e3a8a 30%, #3b82f6 60%, #60a5fa 100%)
      `,
      backgroundBlendMode: "multiply, normal"
    }}>
      {/* Close button */}
      {onClose && (
        <button
          onClick={onClose}
          className="absolute top-4 right-4 z-20 bg-white/80 hover:bg-white text-slate-800 rounded-full p-1 shadow focus:outline-none"
          aria-label="Close map"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
        </button>
      )}
      {/* Show PNG image for SST, otherwise show placeholder */}
      {imageUrl && parameter === 'ssth' ? (
        <div className="absolute inset-0 w-full h-full flex items-center justify-center" style={{
          background: `
            radial-gradient(ellipse at center, #0a1a2e 0%, #16213e 30%, #1e3a8a 70%, #3b82f6 100%),
            linear-gradient(135deg, #0f172a 0%, #1e3a8a 50%, #3b82f6 100%)
          `,
          backgroundBlendMode: "multiply, normal"
        }}>
          <img 
            src={imageUrl}
            alt={`Sea Surface Temperature - ${currentTimestamp || 'loading'}`}
            className={`${isFullscreen ? 'max-w-full max-h-full' : 'w-full h-full'} object-contain rounded-lg`}
            style={{ filter: 'contrast(1.1) brightness(1.1)' }}
          />
          {/* Overlay for better text readability */}
          <div className="absolute inset-0 bg-black/10"></div>
        </div>
      ) : (
        /* Placeholder for non-SST parameters or when image is not available */
        <div className="absolute inset-0 w-full h-full flex items-center justify-center" style={{
          background: `
            radial-gradient(ellipse at 40% 60%, #0a1a2e 0%, #16213e 40%, #1e3a8a 80%, #3b82f6 100%),
            linear-gradient(135deg, #0f172a 0%, #1e3a8a 30%, #3b82f6 60%, #60a5fa 100%)
          `,
          backgroundBlendMode: "multiply, normal"
        }}>
          <div className="text-center text-white/80">
            <div className="text-lg font-medium mb-2">
              {parameter === 'ssth' && imageError ? 'Image not available' : `${currentParam?.name} Data`}
            </div>
            <div className="text-sm opacity-75">
              {parameter === 'ssth' && imageError 
                ? `No satellite data for ${currentTimestamp}`
                : 'Visualization coming soon'
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
          {imageUrl && parameter === 'ssth' ? (
            <>
              <ImageIcon className="h-3 w-3 mr-1" />
              Satellite Image
            </>
          ) : (
            <>
              <MapPin className="h-3 w-3 mr-1" />
              {parameter === 'ssth' ? 'No data available' : 'Coming soon'}
            </>
          )}
        </Badge>
        {imageUrl && parameter === 'ssth' && currentTimestamp && (
          <Badge className="bg-white/20 backdrop-blur text-white border-white/30">
            <div className="text-xs">
              {new Date(`${currentTimestamp.substring(0,4)}-${currentTimestamp.substring(4,6)}-${currentTimestamp.substring(6,8)}T${currentTimestamp.substring(8,10)}:00:00Z`).toLocaleString()}
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
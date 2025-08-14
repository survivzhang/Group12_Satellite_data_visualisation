"use client";

import { useState, useEffect, useCallback } from 'react';

interface DataStore {
  lastUpdate: string | null;
  isUpdating: boolean;
  missingFiles: number;
  updateData: () => Promise<void>;
}

export function useDataStore(): DataStore {
  const [lastUpdate, setLastUpdate] = useState<string | null>(null);
  const [isUpdating, setIsUpdating] = useState(false);
  const [missingFiles, setMissingFiles] = useState(0);

  // Load initial data from localStorage
  useEffect(() => {
    const stored = localStorage.getItem('ningaloo-research-data');
    if (stored) {
      try {
        const data = JSON.parse(stored);
        setLastUpdate(data.lastUpdate);
      } catch (error) {
        console.error('Failed to parse stored data:', error);
      }
    }
    
    // Simulate checking for missing files
    checkMissingFiles();
  }, []);

  const checkMissingFiles = useCallback(() => {
    // Simulate scanning local storage for missing data files
    const expectedFiles = [
      'sst-data', 
      'chlorophyll-data', 
      'salinity-data', 
      'bathymetry-data'
    ];
    
    let missing = 0;
    expectedFiles.forEach(file => {
      if (!localStorage.getItem(`ningaloo-${file}`)) {
        missing++;
      }
    });
    
    setMissingFiles(missing);
  }, []);

  const updateData = useCallback(async () => {
    setIsUpdating(true);
    
    try {
      // Simulate data fetching process
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      // Mock data files to be "fetched"
      const dataFiles = [
        { key: 'ningaloo-sst-data', data: generateMockData('sst') },
        { key: 'ningaloo-chlorophyll-data', data: generateMockData('chlorophyll') },
        { key: 'ningaloo-salinity-data', data: generateMockData('salinity') },
        { key: 'ningaloo-bathymetry-data', data: generateMockData('bathymetry') }
      ];
      
      // "Download" and store data files
      dataFiles.forEach(file => {
        localStorage.setItem(file.key, JSON.stringify(file.data));
      });
      
      // Update metadata
      const now = new Date().toISOString();
      const metadata = {
        lastUpdate: now,
        filesCount: dataFiles.length,
        totalSize: dataFiles.reduce((sum, file) => sum + JSON.stringify(file.data).length, 0)
      };
      
      localStorage.setItem('ningaloo-research-data', JSON.stringify(metadata));
      setLastUpdate(now);
      setMissingFiles(0);
      
    } catch (error) {
      console.error('Failed to update data:', error);
    } finally {
      setIsUpdating(false);
    }
  }, []);

  const generateMockData = (parameter: string) => {
    const dataPoints = [];
    const now = Date.now();
    
    // Generate time series data for the last 30 days
    for (let i = 0; i < 30; i++) {
      for (let j = 0; j < 24; j++) { // Hourly data
        const timestamp = now - (i * 24 * 60 * 60 * 1000) - (j * 60 * 60 * 1000);
        
        // Generate multiple spatial points for each timestamp
        for (let k = 0; k < 10; k++) {
          dataPoints.push({
            timestamp,
            lat: -22.3 + (Math.random() - 0.5) * 2, // Ningaloo area
            lng: 113.8 + (Math.random() - 0.5) * 2,
            value: getRandomValue(parameter),
            quality: Math.random() > 0.1 ? 'good' : 'questionable'
          });
        }
      }
    }
    
    return {
      parameter,
      generatedAt: now,
      count: dataPoints.length,
      data: dataPoints
    };
  };

  const getRandomValue = (parameter: string) => {
    switch (parameter) {
      case 'sst': 
        return 18 + Math.random() * 12 + Math.sin(Date.now() / 86400000) * 3; // Seasonal variation
      case 'chlorophyll': 
        return Math.random() * 5 * (1 + Math.sin(Date.now() / 86400000) * 0.5);
      case 'salinity': 
        return 34 + Math.random() * 2 + Math.sin(Date.now() / 86400000) * 0.5;
      case 'bathymetry': 
        return -Math.random() * 200; // Depth data doesn't change over time
      default: 
        return Math.random() * 100;
    }
  };

  return {
    lastUpdate,
    isUpdating,
    missingFiles,
    updateData
  };
}
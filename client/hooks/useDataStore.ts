"use client";

import { useState, useEffect, useCallback } from 'react';

interface DataStore {
  lastUpdate: string | null;
  isUpdating: boolean;
  missingFiles: number;
  updateData: () => Promise<void>;
  systemStatus: any;
}

interface FileCheckResponse {
  expected_files: number;
  nc_files: {
    existing: string[];
    missing: string[];
    corrupted: string[];
  };
  png_files: {
    existing: string[];
    missing: string[];
  };
  summary: {
    total_expected: number;
    nc_files: {
      existing: number;
      missing: number;
      corrupted: number;
      completion_rate: string;
    };
    png_files: {
      existing: number;
      missing: number;
      completion_rate: string;
    };
  };
  timestamp: string;
}

// API configuration
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export function useDataStore(): DataStore {
  const [lastUpdate, setLastUpdate] = useState<string | null>(null);
  const [isUpdating, setIsUpdating] = useState(false);
  const [missingFiles, setMissingFiles] = useState(0);
  const [systemStatus, setSystemStatus] = useState(null);

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

  const checkMissingFiles = useCallback(async () => {
    try {
      const endTime = new Date('2025-03-01T12:00:00Z');
      const startTime = new Date('2025-03-01T00:00:00Z');
      
      const response = await fetch(`${API_BASE_URL}/check-files`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          start_time: startTime.toISOString(),
          end_time: endTime.toISOString(),
          time_step_hours: 1,
          check_nc: true,
          check_png: true
        })
      });
      
      if (response.ok) {
        const data: FileCheckResponse = await response.json();
        
        // Calculate total missing files count
        const totalMissing = data.nc_files.missing.length + 
                           data.nc_files.corrupted.length + 
                           data.png_files.missing.length;
        
        setMissingFiles(totalMissing);
        setLastUpdate(data.timestamp);
        
        console.log('File check completed:', data.summary);
      } else {
        console.error('File check failed:', response.statusText);
        // If API fails, fallback to simulated check
        simulateFileCheck();
      }
    } catch (error) {
      console.error('Error checking files:', error);
      // If network error, fallback to simulated check
      simulateFileCheck();
    }
  }, []);
  
  const simulateFileCheck = useCallback(() => {
    // Fallback simulated check (when API is unavailable)
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
      // First check file integrity
      await checkMissingFiles();
      
      // If there are missing files, automatically trigger repair
      if (missingFiles > 0) {
        console.log(`Found ${missingFiles} missing files. Starting auto repair...`);
        
        // Automatically trigger repair
        await triggerAutoRepair();
      }
      
      // Get system status
      try {
        const statusResponse = await fetch(`${API_BASE_URL}/system-status`);
        if (statusResponse.ok) {
          const status = await statusResponse.json();
          setSystemStatus(status);
          console.log('System status updated:', status);
        }
      } catch (statusError) {
        console.warn('Could not fetch system status:', statusError);
      }
      
      // Update local metadata
      const now = new Date().toISOString();
      const metadata = {
        lastUpdate: now,
        lastCheck: now,
        missingFiles: missingFiles
      };
      
      localStorage.setItem('ningaloo-research-data', JSON.stringify(metadata));
      setLastUpdate(now);
      
    } catch (error) {
      console.error('Failed to update data:', error);
      
      // If API is unavailable, fallback to simulation mode
      await simulateDataUpdate();
    } finally {
      setIsUpdating(false);
    }
  }, [checkMissingFiles, missingFiles]);

  const triggerAutoRepair = useCallback(async () => {
    try {
      console.log('Triggering automatic file repair...');
      
      // Set repair request parameters
      const repairRequest = {
        start_time: '2025-03-01T00:00:00',
        end_time: '2025-03-01T12:00:00',
        west_lon: 113.0,  // Ningaloo region
        east_lon: 115.0,
        south_lat: -24.0,
        north_lat: -21.0,
        time_step_hours: 1,
        repair_nc: true,
        repair_png: true
      };

      const response = await fetch(`${API_BASE_URL}/repair-files`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(repairRequest)
      });

      if (response.ok) {
        const result = await response.json();
        console.log('Auto repair started:', result);
        
        // Poll to check repair status
        if (result.task_id) {
          await pollRepairStatus(result.task_id);
        }
      } else {
        console.error('Auto repair failed:', response.statusText);
      }
    } catch (error) {
      console.error('Error triggering auto repair:', error);
    }
  }, []);

  const pollRepairStatus = useCallback(async (taskId: string) => {
    const maxPolls = 30; // Maximum 30 polls (about 5 minutes)
    let pollCount = 0;
    
    const poll = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/status/${taskId}`);
        if (response.ok) {
          const status = await response.json();
          console.log(`Repair status: ${status.status} - ${status.message}`);
          
          if (status.status === 'completed') {
            console.log('Auto repair completed successfully!');
            // Re-check files to update status
            await checkMissingFiles();
            return;
          } else if (status.status === 'failed') {
            console.error('Auto repair failed:', status.message);
            return;
          } else if (status.status === 'processing' && pollCount < maxPolls) {
            // Continue polling
            setTimeout(poll, 10000); // Check again after 10 seconds
            pollCount++;
          }
        }
      } catch (error) {
        console.error('Error polling repair status:', error);
      }
    };
    
    poll();
  }, [checkMissingFiles]);
  
  const simulateDataUpdate = useCallback(async () => {
    // Fallback simulated update (when API is unavailable)
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    const dataFiles = [
      { key: 'ningaloo-sst-data', data: generateMockData('sst') },
      { key: 'ningaloo-chlorophyll-data', data: generateMockData('chlorophyll') },
      { key: 'ningaloo-salinity-data', data: generateMockData('salinity') },
      { key: 'ningaloo-bathymetry-data', data: generateMockData('bathymetry') }
    ];
    
    dataFiles.forEach(file => {
      localStorage.setItem(file.key, JSON.stringify(file.data));
    });
    
    const now = new Date().toISOString();
    const metadata = {
      lastUpdate: now,
      filesCount: dataFiles.length,
      totalSize: dataFiles.reduce((sum, file) => sum + JSON.stringify(file.data).length, 0)
    };
    
    localStorage.setItem('ningaloo-research-data', JSON.stringify(metadata));
    setLastUpdate(now);
    setMissingFiles(0);
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
    updateData,
    systemStatus
  };
}
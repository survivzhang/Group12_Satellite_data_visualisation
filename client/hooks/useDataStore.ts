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

// API配置
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
        
        // 计算总的缺失文件数
        const totalMissing = data.nc_files.missing.length + 
                           data.nc_files.corrupted.length + 
                           data.png_files.missing.length;
        
        setMissingFiles(totalMissing);
        setLastUpdate(data.timestamp);
        
        console.log('File check completed:', data.summary);
      } else {
        console.error('File check failed:', response.statusText);
        // 如果API失败，回退到模拟检查
        simulateFileCheck();
      }
    } catch (error) {
      console.error('Error checking files:', error);
      // 如果网络错误，回退到模拟检查
      simulateFileCheck();
    }
  }, []);
  
  const simulateFileCheck = useCallback(() => {
    // 备用的模拟检查（当API不可用时）
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
      // 首先检查文件完整性
      await checkMissingFiles();
      
      // 如果有缺失文件，尝试修复（这里可以选择是否自动修复）
      if (missingFiles > 0) {
        console.log(`Found ${missingFiles} missing files. Consider running repair.`);
        
        // 可选：自动触发修复
        // await triggerRepair();
      }
      
      // 获取系统状态
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
      
      // 更新本地元数据
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
      
      // 如果API不可用，回退到模拟模式
      await simulateDataUpdate();
    } finally {
      setIsUpdating(false);
    }
  }, [checkMissingFiles, missingFiles]);
  
  const simulateDataUpdate = useCallback(async () => {
    // 备用的模拟更新（当API不可用时）
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
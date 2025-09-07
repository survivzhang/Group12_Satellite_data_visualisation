"use client";

import { useState, useEffect, useCallback } from 'react';

interface DataStore {
  lastUpdate: string | null;
  isUpdating: boolean;
  missingFiles: number;
  updateData: () => Promise<void>;
  systemStatus: any;
  getParameterFiles: (paramId: string, fileType: 'nc' | 'png') => Promise<any[]>;
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

// API配置 - 使用统一API
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// 卫星参数映射
const SATELLITE_MAPPING = {
  'ssth': { satellite: 'himawari', parameter: 'sst' },
  'sst-s3a': { satellite: 'sentinel3a', parameter: 'sst' },
  'sst-s3b': { satellite: 'sentinel3b', parameter: 'sst' },
  'chl-s3a': { satellite: 'sentinel3a', parameter: 'chl' },
  'chl-s3b': { satellite: 'sentinel3b', parameter: 'chl' }
};

export function useDataStore(): DataStore {
  const [lastUpdate, setLastUpdate] = useState<string | null>(null);
  const [isUpdating, setIsUpdating] = useState(false);
  const [missingFiles, setMissingFiles] = useState(0);
  const [systemStatus, setSystemStatus] = useState(null);
  const [isCheckingFiles, setIsCheckingFiles] = useState(false);

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
    // 防止重复调用
    if (isCheckingFiles) {
      console.log('File check already in progress, skipping...');
      return;
    }
    
    setIsCheckingFiles(true);
    
    try {
      // 使用新的统一API检查系统状态
      const response = await fetch(`${API_BASE_URL}/system/status`);
      
      if (response.ok) {
        const data = await response.json();
        setSystemStatus(data);
        
        // 从系统状态中提取文件信息
        let totalMissing = 0;
        
        // 检查Himawari状态 - 只有当模块可用时才检查文件
        if (data.satellites?.himawari?.available === true) {
          try {
            const himawariCheck = await fetch(`${API_BASE_URL}/himawari/check-files`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                start_time: '2025-03-01T00:00:00',
                end_time: '2025-03-01T12:00:00',
                time_step_hours: 1,
                check_nc: true,
                check_png: true
              })
            });
            
            if (himawariCheck.ok) {
              const himawariData: FileCheckResponse = await himawariCheck.json();
              totalMissing += himawariData.nc_files.missing.length + 
                            himawariData.nc_files.corrupted.length + 
                            himawariData.png_files.missing.length;
            }
          } catch (e) {
            console.warn('Could not check Himawari files:', e);
          }
        } else {
          console.log('Himawari module not available, skipping file check');
        }

        // 检查Sentinel-3状态 - 使用时间基础的新鲜度检查
        const sentinel3Satellites = ['sentinel3a', 'sentinel3b'];
        for (const satellite of sentinel3Satellites) {
          if (data.satellites?.[satellite]?.available === true) {
            try {
              // 使用Sentinel-3的freshness check API
              const s3Check = await fetch(`${API_BASE_URL}/sentinel3/check-freshness`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                  satellite: satellite,
                  threshold_hours: 2
                })
              });
              
              if (s3Check.ok) {
                const s3Data = await s3Check.json();
                // 如果数据需要更新，计为"缺失"文件
                if (s3Data.results) {
                  Object.values(s3Data.results).forEach((result: any) => {
                    if (result.needs_update) {
                      totalMissing += 1; // 每个需要更新的数据类型计为1个缺失
                    }
                  });
                }
                console.log(`${satellite} freshness check:`, s3Data);
              }
            } catch (e) {
              console.warn(`Could not check ${satellite} freshness:`, e);
            }
          } else {
            console.log(`${satellite} module not available, skipping freshness check`);
          }
        }
        
        setMissingFiles(totalMissing);
        setLastUpdate(new Date().toISOString());
        
        console.log('System status check completed:', data);
      } else {
        console.error('System status check failed:', response.statusText);
        simulateFileCheck();
      }
    } catch (error) {
      console.error('Error checking system status:', error);
      simulateFileCheck();
    } finally {
      setIsCheckingFiles(false);
    }
  }, [isCheckingFiles]);
  
  const simulateFileCheck = useCallback(() => {
    // 当API不可用时，设置为0缺失文件
    console.log('API unavailable, setting missing files to 0');
    setMissingFiles(0);
  }, []);

  const downloadLatestData = useCallback(async () => {
    try {
      console.log('Downloading latest satellite data...');
      
      // 检查系统状态，找出可用的卫星
      const statusResponse = await fetch(`${API_BASE_URL}/system/status`);
      if (!statusResponse.ok) {
        throw new Error('System status check failed');
      }
      
      const systemStatus = await statusResponse.json();
      const availableSatellites = Object.entries(systemStatus.satellites || {})
        .filter(([_, status]: [string, any]) => status.available)
        .map(([satellite, _]) => satellite);
      
      if (availableSatellites.length === 0) {
        console.log('No satellites available for data download');
        return;
      }
      
      console.log(`Available satellites: ${availableSatellites.join(', ')}`);
      
      // 为每个可用的卫星触发数据更新
      const downloadPromises = availableSatellites.map(async (satellite) => {
        try {
          if (satellite === 'himawari') {
            // 使用Himawari的auto-monitor-repair端点
            const response = await fetch(`${API_BASE_URL}/himawari/auto-monitor-repair`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' }
            });
            
            if (response.ok) {
              const result = await response.json();
              console.log(`Himawari data update initiated:`, result);
              return result;
            }
          } else if (satellite.startsWith('sentinel3')) {
            // 使用Sentinel-3的process-data端点
            const response = await fetch(`${API_BASE_URL}/sentinel3/process-data`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                satellite: satellite,
                parameter: 'sst', // 先下载SST数据
                start_time: '2025-03-01T00:00:00.000Z',
                end_time: '2025-03-01T12:00:00.000Z',
                west_lon: 113.0,
                east_lon: 115.0,
                south_lat: -24.0,
                north_lat: -21.0,
                layer_keys: [`${satellite}_sst`, `${satellite}_chl`] // 同时下载SST和CHL
              })
            });
            
            if (response.ok) {
              const result = await response.json();
              console.log(`${satellite} data update initiated:`, result);
              
              // 如果有task_id，监控任务状态
              if (result.task_id) {
                await pollSentinel3Status(result.task_id, satellite);
              }
              
              return result;
            }
          }
        } catch (error) {
          console.warn(`Failed to update data for ${satellite}:`, error);
        }
      });
      
      // 等待所有下载任务完成
      const results = await Promise.allSettled(downloadPromises);
      const successful = results.filter(r => r.status === 'fulfilled').length;
      
      console.log(`Data update completed: ${successful}/${availableSatellites.length} satellites updated successfully`);
      
    } catch (error) {
      console.error('Error downloading latest data:', error);
      throw error;
    }
  }, []);

  const triggerAutoRepair = useCallback(async () => {
    try {
      console.log('Triggering automatic file repair...');
      
      // 设置修复请求参数
      const repairRequest = {
        start_time: '2025-03-01T00:00:00',
        end_time: '2025-03-01T12:00:00',
        west_lon: 113.0,  // Ningaloo 区域
        east_lon: 115.0,
        south_lat: -24.0,
        north_lat: -21.0,
        time_step_hours: 1,
        repair_nc: true,
        repair_png: true
      };

      // 使用新的统一API修复端点
      const response = await fetch(`${API_BASE_URL}/himawari/repair-files`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(repairRequest)
      });

      if (response.ok) {
        const result = await response.json();
        console.log('Auto repair started:', result);
        
        // 轮询检查修复状态
        if (result.task_id) {
          await pollRepairStatus(result.task_id, 'himawari');
        }
      } else {
        console.error('Auto repair failed:', response.statusText);
      }
    } catch (error) {
      console.error('Error triggering auto repair:', error);
    }
  }, []);

  const pollRepairStatus = useCallback(async (taskId: string, satellite: string = 'himawari') => {
    const maxPolls = 30; // 最多轮询30次（约5分钟）
    let pollCount = 0;
    
    const poll = async () => {
      try {
        // 使用新的统一API状态端点
        const response = await fetch(`${API_BASE_URL}/${satellite}/status/${taskId}`);
        if (response.ok) {
          const status = await response.json();
          console.log(`Repair status: ${status.status} - ${status.message}`);
          
          if (status.status === 'completed') {
            console.log('Auto repair completed successfully!');
            // 重新检查文件以更新状态（延迟调用避免重复）
            setTimeout(() => checkMissingFiles(), 1000);
            return;
          } else if (status.status === 'failed') {
            console.error('Auto repair failed:', status.message);
            return;
          } else if (status.status === 'processing' && pollCount < maxPolls) {
            // 继续轮询
            setTimeout(poll, 10000); // 10秒后再次检查
            pollCount++;
          }
        }
      } catch (error) {
        console.error('Error polling repair status:', error);
      }
    };
    
    poll();
  }, [checkMissingFiles]);

  const pollSentinel3Status = useCallback(async (taskId: string, satellite: string) => {
    const maxPolls = 60; // Sentinel-3下载可能需要更长时间，最多轮询10分钟
    let pollCount = 0;
    
    const poll = async () => {
      try {
        // 使用Sentinel-3的状态端点
        const response = await fetch(`${API_BASE_URL}/sentinel3/status/${taskId}`);
        if (response.ok) {
          const status = await response.json();
          console.log(`${satellite} processing status: ${status.status} - ${status.message}`);
          
          if (status.status === 'completed') {
            console.log(`${satellite} data processing completed successfully!`);
            // 重新检查文件以更新状态（延迟调用避免重复）
            setTimeout(() => checkMissingFiles(), 1000);
            return;
          } else if (status.status === 'failed') {
            console.error(`${satellite} data processing failed:`, status.message);
            return;
          } else if (status.status === 'processing' && pollCount < maxPolls) {
            // 继续轮询
            setTimeout(poll, 10000); // 10秒后再次检查
            pollCount++;
          }
        }
      } catch (error) {
        console.error(`Error polling ${satellite} status:`, error);
      }
    };
    
    poll();
  }, [checkMissingFiles]);

  const updateData = useCallback(async () => {
    if (isUpdating || isCheckingFiles) {
      console.log('Update already in progress, skipping...');
      return;
    }
    
    setIsUpdating(true);
    
    try {
       // 首先检查文件完整性并获取当前缺失文件数量
      let currentMissingFiles = 0;
      
      try {
        // 检查系统状态
        const response = await fetch(`${API_BASE_URL}/system/status`);
        
        if (response.ok) {
          const data = await response.json();
          setSystemStatus(data);
          
          // 检查Himawari状态
          if (data.satellites?.himawari?.available === true) {
            const himawariCheck = await fetch(`${API_BASE_URL}/himawari/check-files`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                start_time: '2025-03-01T00:00:00',
                end_time: '2025-03-01T12:00:00',
                time_step_hours: 1,
                check_nc: true,
                check_png: true
              })
            });
            
            if (himawariCheck.ok) {
              const himawariData: FileCheckResponse = await himawariCheck.json();
              currentMissingFiles += himawariData.nc_files.missing.length + 
                                   himawariData.nc_files.corrupted.length + 
                                   himawariData.png_files.missing.length;
              
              console.log(`Himawari file check completed: ${himawariData.nc_files.missing.length + himawariData.nc_files.corrupted.length + himawariData.png_files.missing.length} missing files detected`);
              console.log('Missing NC files:', himawariData.nc_files.missing);
              console.log('Corrupted NC files:', himawariData.nc_files.corrupted);
              console.log('Missing PNG files:', himawariData.png_files.missing);
            }
          }

          // 检查Sentinel-3状态
          const sentinel3Satellites = ['sentinel3a', 'sentinel3b'];
          for (const satellite of sentinel3Satellites) {
            if (data.satellites?.[satellite]?.available === true) {
              try {
                const s3Check = await fetch(`${API_BASE_URL}/sentinel3/check-freshness`, {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({
                    satellite: satellite,
                    threshold_hours: 2
                  })
                });
                
                if (s3Check.ok) {
                  const s3Data = await s3Check.json();
                  let s3MissingCount = 0;
                  if (s3Data.results) {
                    Object.values(s3Data.results).forEach((result: any) => {
                      if (result.needs_update) {
                        s3MissingCount += 1;
                      }
                    });
                  }
                  currentMissingFiles += s3MissingCount;
                  console.log(`${satellite} freshness check: ${s3MissingCount} data types need updating`);
                }
              } catch (e) {
                console.warn(`Could not check ${satellite} freshness during update:`, e);
              }
            }
          }
          
          setMissingFiles(currentMissingFiles);
        }
      } catch (error) {
        console.error('Error during file check:', error);
        currentMissingFiles = 0;
        setMissingFiles(0);
      }
      
      // 如果有缺失文件，自动触发修复/下载
      if (currentMissingFiles > 0) {
        console.log(`🔧 Found ${currentMissingFiles} missing files. Starting auto repair...`);
        await triggerAutoRepair();
      } else {
        console.log('✅ No missing files detected. System is up to date.');
      }
      
      // 更新本地元数据
      const now = new Date().toISOString();
      const metadata = {
        lastUpdate: now,
        lastCheck: now,
        missingFiles: currentMissingFiles
      };
      
      localStorage.setItem('ningaloo-research-data', JSON.stringify(metadata));
      setLastUpdate(now);
      
    } catch (error) {
      console.error('Failed to update data:', error);
      
      // 如果API不可用，只更新时间戳
      const now = new Date().toISOString();
      setLastUpdate(now);
      localStorage.setItem('ningaloo-research-data', JSON.stringify({ lastUpdate: now }));
    } finally {
      setIsUpdating(false);
    }
  }, [triggerAutoRepair, isUpdating, isCheckingFiles]);

  // 获取特定参数的文件列表
  const getParameterFiles = useCallback(async (paramId: string, fileType: 'nc' | 'png') => {
    try {
      const mapping = SATELLITE_MAPPING[paramId as keyof typeof SATELLITE_MAPPING];
      if (!mapping) {
        console.warn(`No satellite mapping found for parameter: ${paramId}`);
        return [];
      }

      const { satellite, parameter } = mapping;
      const response = await fetch(`${API_BASE_URL}/api/v1/satellites/${satellite}/${parameter}/${fileType}`);
      
      if (response.ok) {
        const data = await response.json();
        return data.files || [];
      } else {
        console.error(`Failed to fetch ${fileType} files for ${paramId}:`, response.statusText);
        return [];
      }
    } catch (error) {
      console.error(`Error fetching ${fileType} files for ${paramId}:`, error);
      return [];
    }
  }, []);

  return {
    lastUpdate,
    isUpdating,
    missingFiles,
    updateData,
    systemStatus,
    getParameterFiles
  };
}
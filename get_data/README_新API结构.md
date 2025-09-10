# 重构后的卫星数据API结构

## 概述

已成功将原来分散的多个`api_example.py`文件重构为统一的API结构，所有API相关文件现在都位于`get_data`目录（后端目录）中。

## 新的目录结构

```
get_data/                           # 🏠 后端目录
├── api.py                          # 🌟 全局统一API入口
├── satellites/                     # 📁 卫星模块
│   ├── shared/                     # 🔧 共享工具和模型
│   │   ├── models.py              # 📋 通用Pydantic模型
│   │   ├── utils.py               # 🛠️ 工具函数
│   │   └── base_api.py            # 🏗️ 基础API类
│   ├── himawari/                   # 🛰️ Himawari模块
│   │   └── api.py                 # Himawari特定API
│   └── sentinel3/                  # 🛰️ Sentinel-3模块
│       └── api.py                 # Sentinel-3特定API
├── himawari_test_data/             # 📊 Himawari数据和处理器
│   └── himawari_processor.py      # Himawari业务逻辑
├── saternal3/                      # 📊 Sentinel-3数据和处理器
│   └── usingtheEumetview.py       # Sentinel-3业务逻辑
└── [其他数据目录...]
```

## 已删除的文件

✅ **已成功删除重复的API文件：**
- ❌ `get_data/api_example.py` （旧的根级API）
- ❌ `get_data/himawari_test_data/api_example.py` （Himawari重复API）
- ❌ `get_data/saternal3/api_example.py` （Sentinel-3重复API）
- ❌ 根目录下的`api.py`、`satellites/`目录和迁移脚本

## 核心改进

### ✅ 解决的问题
1. **消除代码重复** - 不再有多个相似的API文件
2. **统一入口点** - 单一的`get_data/api.py`作为全局API
3. **清晰的架构** - 共享模块和卫星特定模块分离
4. **更好的维护性** - 易于扩展新卫星
5. **一致的接口** - 所有卫星使用相同的API模式

### 🏗️ 架构特点
- **共享基础设施** - 公共模型、工具函数和基类
- **卫星特定实现** - 每个卫星有自己的API模块
- **业务逻辑分离** - API层与数据处理逻辑解耦
- **向后兼容** - 保持现有端点的兼容性

## 启动新API

### 1. 启动服务器
```bash
cd get_data
python api.py
```

### 2. 访问API文档
- **交互式文档**: http://localhost:8000/docs
- **ReDoc文档**: http://localhost:8000/redoc
- **API概览**: http://localhost:8000/

## API端点

### 统一端点
```
GET  /                              # API概览
GET  /health                        # 全局健康检查
GET  /system/status                 # 统一系统状态

# 卫星管理
GET  /api/v1/satellites             # 列出所有卫星
GET  /api/v1/satellites/{satellite} # 卫星信息
GET  /api/v1/satellites/{satellite}/{parameter}  # 参数信息

# 数据访问
GET  /api/v1/satellites/{satellite}/{parameter}/{file_type}  # 列出文件
GET  /api/v1/satellites/{satellite}/{parameter}/nc/{filename}  # 下载NC文件
POST /api/v1/process                # 处理数据（任何卫星）
GET  /tasks/{satellite}/{task_id}   # 任务状态
```

### 卫星特定端点（代理）
```
# Himawari特定功能
GET/POST /himawari/*                # 所有Himawari端点

# Sentinel-3特定功能
GET/POST /sentinel3/*               # 所有Sentinel-3端点
```

## 使用示例

### 1. 检查系统状态
```bash
curl http://localhost:8000/system/status
```

### 2. 列出所有卫星
```bash
curl http://localhost:8000/api/v1/satellites
```

### 3. 获取Himawari文件
```bash
curl http://localhost:8000/api/v1/satellites/himawari/sst/nc
```

### 4. 处理Sentinel-3数据
```bash
curl -X POST http://localhost:8000/api/v1/process \
  -H "Content-Type: application/json" \
  -d '{
    "satellite": "sentinel3a",
    "parameter": "sst",
    "start_time": "2025-03-01T00:00:00",
    "end_time": "2025-03-01T12:00:00",
    "west_lon": 113.0,
    "east_lon": 115.0,
    "south_lat": -24.0,
    "north_lat": -21.0
  }'
```

### 5. 使用卫星特定功能
```bash
# Himawari文件修复
curl -X POST http://localhost:8000/himawari/repair-files \
  -H "Content-Type: application/json" \
  -d '{...}'

# Sentinel-3图层信息
curl http://localhost:8000/sentinel3/layers
```

## 为开发者

### 添加新卫星
1. 在`satellites/`下创建新目录
2. 实现`BaseSatelliteAPI`
3. 在`api.py`的`SATELLITES`配置中添加
4. 更新静态文件挂载（如需要）

### 添加共享功能
- **模型**: 添加到`satellites/shared/models.py`
- **工具**: 添加到`satellites/shared/utils.py`
- **基类**: 扩展`satellites/shared/base_api.py`

### 调试
```bash
# 启动调试模式
cd get_data
python api.py --log-level debug
```

## 优势总结

### 🚀 **性能**
- 单一服务器实例
- 共享资源池
- 减少内存占用

### 🛠️ **可维护性**
- 零代码重复
- 集中配置
- 一致的错误处理
- 更容易测试

### 📈 **可扩展性**
- 轻松添加新卫星
- 共享基础设施
- 统一监控和日志

### 👥 **开发体验**
- 单一API学习
- 一致的模式
- 更好的文档
- 统一认证

## 故障排除

### 常见问题

1. **模块导入错误**
   - 确保`himawari_processor.py`和`usingtheEumetview.py`可访问
   - 检查Python路径配置

2. **静态文件无法访问**
   - 验证目录结构匹配预期路径
   - 检查文件权限

3. **卫星不可用**
   - 检查底层处理器模块是否工作
   - 验证数据目录是否存在

## 迁移完成！

✅ **重构成功完成！**
- 旧的重复API文件已删除
- 新的统一API结构已就位
- 所有功能保持向后兼容
- API现在位于正确的后端目录（`get_data`）中

现在您有了一个干净、可维护、可扩展的卫星数据API架构！

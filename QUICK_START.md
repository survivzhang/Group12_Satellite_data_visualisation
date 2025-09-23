# 🚀 快速启动指南 | Quick Start Guide

## ⚡ 5分钟快速体验 | 5-Minute Quick Experience

### 🎯 目标 | Goal
快速启动卫星数据可视化系统，体验交互式地图功能。
Quickly start the satellite data visualization system and experience interactive map features.

---

## 📋 准备工作 | Prerequisites

确保你的系统已安装：
Make sure your system has:

```bash
✅ Node.js (≥ 18.0)     # 查看版本: node --version  
✅ Python (≥ 3.9)       # 查看版本: python --version
✅ npm 或 yarn          # 查看版本: npm --version
✅ Git                  # 查看版本: git --version
```

---

## 🔥 一键启动命令 | One-Click Start Commands

### 步骤 1: 获取最新代码 | Step 1: Get Latest Code
```bash
# 首次使用 / First time
git clone [你的仓库URL]
cd Group12_Satellite_data_visualisation

# 或者更新现有代码 / Or update existing code
git pull origin main
```

💡 **团队协作提示**: 推送到主分支后，其他成员只需 `git pull` 然后按以下步骤启动即可！
💡 **Team Tip**: After pushing to main branch, other members just need `git pull` and follow steps below!

### 步骤 2: 后端启动 | Step 2: Start Backend
```bash
# 进入后端目录
cd get_data

# 创建并激活虚拟环境 (首次运行)
python -m venv venv
venv\Scripts\activate    # Windows
# source venv/bin/activate  # macOS/Linux

# 安装Python依赖 (首次运行)
pip install -r requirements.txt

# 启动后端服务
python api.py
```

✅ **成功标志**: 看到 `Uvicorn running on http://0.0.0.0:8000`

### 步骤 3: 前端启动 | Step 3: Start Frontend
```bash
# 新开一个终端，进入前端目录
cd client

# 安装Node.js依赖 (首次运行)
npm install

# 启动前端服务
npm run dev
```

✅ **成功标志**: 看到 `ready - started server on 0.0.0.0:3000`

### 步骤 4: 体验功能 | Step 4: Experience Features
1. **打开浏览器**: http://localhost:3000
2. **添加地图**: 点击 "+ Add Map" 
3. **选择参数**: 展开 "Data Parameters"，选择 "SST (Himawari)"
4. **切换模式**: 点击 "Canvas" 按钮体验热力图
5. **时间控制**: 使用底部时间轴播放动画

---

## 🎮 核心功能体验清单 | Core Feature Experience Checklist

### ✅ 基础功能测试 | Basic Function Tests

- [ ] **页面加载**: 访问 http://localhost:3000 正常显示
- [ ] **API连接**: 访问 http://localhost:8000/docs 显示API文档
- [ ] **添加地图**: 点击 "+ Add Map" 成功添加新地图窗口
- [ ] **参数选择**: 展开参数面板，选择不同卫星数据

### ✅ 交互式地图测试 | Interactive Map Tests

- [ ] **静态模式**: 默认Static模式显示PNG图像
- [ ] **交互模式**: 点击 "Interactive" 显示点式数据
- [ ] **热力图模式**: 点击 "Canvas" 显示连续热力图 ⭐
- [ ] **地图交互**: 缩放、拖拽地图功能正常

### ✅ 时间控制测试 | Time Control Tests

- [ ] **时间轴拖拽**: 拖动时间滑块，地图数据更新
- [ ] **播放控制**: 点击播放按钮，自动播放时间序列
- [ ] **分辨率切换**: 切换时间分辨率 (小时/日/周/月)

### ✅ 高级功能测试 | Advanced Feature Tests

- [ ] **数据范围过滤**: 点击 "Range" 按钮设置数值范围
- [ ] **图像信息**: 点击 "Image Info" 查看详细数据统计
- [ ] **全屏模式**: 点击全屏按钮放大地图
- [ ] **多地图对比**: 添加多个地图对比不同参数

---

## 🔧 常见启动问题速查 | Common Startup Issues Quick Fix

### 🚨 后端问题 | Backend Issues

**问题**: `pip install` 失败
**解决**: 
```bash
# 升级pip
python -m pip install --upgrade pip
# 使用国内镜像 (中国用户)
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/
```

**问题**: `uvicorn: command not found`
**解决**:
```bash
# 确保在正确的虚拟环境中
pip install uvicorn[standard]
# 或直接运行
python -m uvicorn api:app --reload --port 8000
```

**问题**: 端口8000被占用
**解决**:
```bash
# 使用其他端口
uvicorn api:app --reload --port 8001
# 记得更新前端配置中的API地址
```

### 🚨 前端问题 | Frontend Issues

**问题**: `npm install` 慢或失败
**解决**:
```bash
# 清除缓存
npm cache clean --force
# 使用国内镜像 (中国用户)  
npm install --registry https://registry.npmmirror.com
```

**问题**: 地图不显示
**解决**:
```bash
# 确保后端服务正在运行
# 检查浏览器控制台是否有CORS错误
# 刷新页面重试
```

**问题**: TypeScript编译错误
**解决**:
```bash
# 删除.next目录重新构建
rm -rf .next
npm run dev
```

---

## 📊 验证成功安装 | Verify Successful Installation

### 🎯 后端验证 | Backend Verification
访问: http://localhost:8000/docs
应该看到: FastAPI交互式API文档页面

Visit: http://localhost:8000/docs
Should see: FastAPI interactive API documentation page

### 🎯 前端验证 | Frontend Verification  
访问: http://localhost:3000
应该看到: 卫星数据可视化主界面，包含以下元素：

Visit: http://localhost:3000
Should see: Satellite data visualization main interface with:

```
✅ 顶部: "Data Parameters (8 available)" 
✅ 中间: 地图显示区域
✅ 底部: 时间轴控制器
✅ 右上角: "Add Map" 按钮
```

### 🎯 功能验证 | Feature Verification
1. **添加地图**: 点击 "+ Add Map" → 新地图窗口出现
2. **选择参数**: 展开参数面板 → 看到8种卫星数据选项
3. **Canvas模式**: 切换到Canvas → 看到彩色热力图
4. **时间播放**: 点击播放按钮 → 地图数据自动更新

---

## 🎉 成功启动后的下一步 | Next Steps After Successful Launch

### 🔍 探索功能 | Explore Features
1. **试试不同卫星数据**: Himawari SST vs Sentinel-3 CHL
2. **对比分析**: 添加4个地图同时显示不同参数  
3. **时间序列**: 使用播放功能观察数据变化趋势
4. **精确查询**: 在Interactive模式下点击地图查看具体数值

### 📚 深入学习 | Deep Learning
- 阅读 [功能使用说明](docs/前端功能使用说明.md) 了解详细功能
- 查看 [部署指南](DEPLOYMENT_GUIDE.md) 进行生产部署
- 研究 [时间处理逻辑](docs/时间轴处理逻辑文档.md) 理解算法原理

### 🛠️ 开发定制 | Development Customization
- 修改 `client/components/` 中的React组件
- 在 `get_data/data/` 中添加你自己的卫星数据
- 调整 `get_data/api.py` 中的API端点

---

## 💡 专业提示 | Pro Tips

### ⚡ 性能优化 | Performance Optimization
```bash
# 生产环境构建
cd client && npm run build && npm start

# 后端多进程
uvicorn api:app --workers 4 --host 0.0.0.0 --port 8000
```

### 🔧 开发工具 | Development Tools
```bash
# 实时代码检查
cd client && npm run lint

# Python代码格式化
cd get_data && black . && isort .
```

### 📱 移动端访问 | Mobile Access
```bash
# 获取本机IP地址
ipconfig  # Windows
ifconfig  # macOS/Linux

# 手机访问: http://你的IP:3000
```

---

## 🆘 获取帮助 | Get Help

### 快速帮助 | Quick Help
- **🐛 遇到Bug**: 检查浏览器控制台和终端输出
- **📖 功能疑问**: 查看 `docs/` 目录下的详细文档  
- **💡 想要新功能**: 联系项目团队讨论

### 联系方式 | Contact
- **GitHub**: 提交Issue到项目仓库
- **文档**: 查看项目 `docs/` 目录
- **团队**: CITS5206 Capstone Group 12

---

🎊 **恭喜！你已经成功启动了卫星数据可视化系统！**
🎊 **Congratulations! You have successfully launched the satellite data visualization system!**

现在可以开始探索海洋卫星数据的奇妙世界了！🌊🛰️
Now you can start exploring the wonderful world of ocean satellite data! 🌊🛰️

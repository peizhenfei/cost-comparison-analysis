---
name: "cost-analysis-web"
description: "Launches a Streamlit web interface for real estate cost comparison analysis. Invoke when user wants to run the web app or access the visual interface."
---

# 成本对比分析系统 - 网页前端

## 功能概述

这是一个基于Streamlit的交互式网页前端，用于房地产项目成本对比分析。

## 快速启动

### 方法1: 使用命令行

```bash
# 安装依赖
pip install -r requirements.txt

# 启动网页应用
streamlit run web_app.py
```

### 方法2: 使用Python直接运行

```bash
python web_app.py
```

## 功能特性

### 📂 数据加载
- 支持上传两个项目的Excel文件
- 自动识别项目信息（名称、面积、业态等）
- 实时显示数据加载状态

### 📊 业态匹配
- 自动匹配两个项目的业态类型
- 显示匹配结果和状态
- 支持跨分类业态匹配

### 📈 数据分析
- 汇总成本对比计算
- 固定成本差异分析
- 弹性成本差异分析
- 实时显示分析进度

### 📥 报告生成
- 自动生成Excel对比报告
- 支持下载报告文件
- 预览汇总数据表格

## 界面布局

- **侧边栏**: 文件上传、配置选项、开始分析按钮
- **主区域**:
  - 项目信息卡片
  - 业态匹配结果表格
  - 数据分析进度条
  - 汇总数据预览表格

## 输出文件

报告包含3个工作表：
1. **成本对比总表**: 项目整体成本对比
2. **固定单方差异明细分析**: 固定成本科目差异分解
3. **弹性单方差异明细分析**: 弹性成本科目差异分解

## 依赖项

- openpyxl >= 3.0.9
- streamlit >= 1.28.0
- pandas >= 2.0.0
- numpy >= 1.24.0

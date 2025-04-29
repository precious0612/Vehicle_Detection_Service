# Vehicle Detection Service

本项目基于 FastAPI + YOLOv5 + DeepSort 实现多路视频流的车辆检测与跟踪，支持 RTSP（暂不支持）/HTTP 视频流输出，并支持 GPU 加速和多流并发。  
支持 Docker Compose 一键部署，内置 Prometheus GPU/主机监控。

---

## 目录

- [功能特性](#功能特性)
- [环境要求](#环境要求)
- [快速部署](#快速部署)
- [接口说明](#接口说明)
- [监控与可视化](#监控与可视化)
- [常见问题](#常见问题)

---

## 功能特性

- 支持多路视频流并发检测（每路独立线程）
- 支持 RTSP/HTTP 视频流输出
- 支持 GPU 加速（NVIDIA T4/CUDA 12.4 及以上）
- 支持权重缓存，避免重复下载
- 支持 Prometheus 监控 GPU/主机资源
- 容器化部署，环境一致性强

---

## 环境要求

- Ubuntu 20.04+
- NVIDIA GPU（如 Tesla T4），已安装驱动
- CUDA 12.4 及以上
- Docker 20.10+，Docker Compose 1.29+
- 已安装 NVIDIA Container Toolkit  
  安装方法见：https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html

---

## 快速部署

### 1. 克隆项目

```bash
git clone https://github.com/precious0612/Vehicle_Detection_Service.git
cd Vehicle_Detection_Service
```

### 2. 启动服务

```bash
docker-compose up --build -d
```

首次启动会自动下载 YOLOv5 权重，后续重启无需重复下载。

### 3. 查看服务状态

```bash
docker ps
```

### 4. 访问 API 文档

浏览器访问：  
```
http://<服务器IP>:2334/docs
```

---

## 接口说明

### 1. 启动视频流检测

```http
POST /start_stream/{stream_id}
Content-Type: application/json

{
  "stream_url": "<视频流RTSP_URL>",
  "rtsp_port": 8554   // 可选，启用RTSP输出
}
```

**注：首次启动需要下载依赖以及模型权重**

- `stream_id`：自定义唯一标识
- 返回：HTTP/RTSP 访问地址

### 2. 获取视频流（HTTP MJPEG）

```http
GET /video_feed/{stream_id}
```

- 直接浏览器或 VLC 播放

### 3. 获取流信息和统计

```http
GET /stream_info/{stream_id}
GET /statistics/{stream_id}
```

### 4. 停止视频流

```http
DELETE /stop_stream/{stream_id}
```

---

## 监控与可视化

### 1. Prometheus 监控

- Prometheus: [http://<服务器IP>:9090](http://<服务器IP>:9090)
- Node Exporter (主机监控): [http://<服务器IP>:9100/metrics](http://<服务器IP>:9100/metrics)
- DCGM Exporter (GPU监控): [http://<服务器IP>:9400/metrics](http://<服务器IP>:9400/metrics)

### 2. Grafana 可选

如需可视化大盘，可单独部署 Grafana，数据源指向 Prometheus。

---

## 权重缓存说明

- 容器会自动将 YOLOv5 权重缓存到 `/root/.cache/torch/hub`，并通过 docker volume `yolov5-cache` 持久化，避免重复下载。

---

## 常见问题

### 1. 容器无法使用 GPU？

- 请确保主机已正确安装 NVIDIA 驱动和 nvidia-docker。
- 测试命令：`docker run --rm --gpus all nvidia/cuda:12.8.1-cudnn-devel-ubuntu20.04 nvidia-smi`

### 2. 权重下载慢或失败？

- 检查网络，或提前下载权重并挂载到 `/root/.cache/torch/hub`。

### 3. 如何扩展多实例？

- `docker-compose up --scale vehicledetect=2 -d` 可启动多个副本，配合负载均衡器使用。

---

## 目录结构

```
.
├── app.py
├── video_processor.py
├── rtsp_server.py
├── stream_worker.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── prometheus.yml
└── README.md
```


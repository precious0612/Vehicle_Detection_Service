FROM nvidia/cuda:12.4.0-cudnn8-runtime-ubuntu20.04

# 安装系统依赖
RUN apt-get update && \
    apt-get install -y python3 python3-pip ffmpeg libgl1-mesa-glx && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app

# 安装 Python 依赖
RUN python3 -m pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 可选：提前下载YOLOv5权重
# RUN python3 -c "import torch; torch.hub.load('ultralytics/yolov5', 'yolov5s')"

EXPOSE 2334 8554

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "2334"]
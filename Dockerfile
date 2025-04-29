FROM nvidia/cuda:12.8.1-cudnn-devel-ubuntu20.04

# 构建参数，默认国际源
ARG USE_CHINA_MIRROR=false

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Shanghai

# 根据参数选择 apt 源
RUN if [ "$USE_CHINA_MIRROR" = "true" ]; then \
        sed -i 's|http://archive.ubuntu.com/ubuntu/|http://mirrors.aliyun.com/ubuntu/|g' /etc/apt/sources.list; \
    fi && \
    apt-get update && \
    apt-get install -y python3 python3-pip ffmpeg libgl1-mesa-glx && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app

# 根据参数选择 pip 源
RUN python3 -m pip install --upgrade pip && \
    if [ "$USE_CHINA_MIRROR" = "true" ]; then \
        pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple; \
    fi && \
    pip install --cache-dir /root/.cache/pip -r requirements.txt

# 可选：提前下载YOLOv5权重
# RUN python3 -c "import torch; torch.hub.load('ultralytics/yolov5', 'yolov5s')"

EXPOSE 2334 8554

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "2334"]
import cv2
import numpy as np
import subprocess
import threading
from queue import Queue
import time
from typing import Optional
import os

class RTSPOutputStream:
    def __init__(self, port: int = 8554, stream_name: str = "stream"):
        self.port = port
        self.stream_name = stream_name
        self.frame_queue = Queue(maxsize=30)
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.ffmpeg_process: Optional[subprocess.Popen] = None
        
        # 创建临时管道文件
        self.pipe_path = f"/tmp/rtsp_pipe_{port}_{stream_name}"
        if os.path.exists(self.pipe_path):
            os.remove(self.pipe_path)
        os.mkfifo(self.pipe_path)

    def start(self):
        """启动RTSP流服务"""
        self.running = True
        
        # 优化的ffmpeg命令参数
        command = [
            'ffmpeg',
            '-y',
            '-f', 'rawvideo',
            '-vcodec', 'rawvideo',
            '-pix_fmt', 'bgr24',
            '-s', '640x480',
            '-r', '30',
            '-i', self.pipe_path,
            '-c:v', 'libx264',
            '-preset', 'ultrafast',
            '-tune', 'zerolatency',
            '-profile:v', 'baseline',
            '-level', '3.0',
            '-x264-params', 'keyint=30:min-keyint=30:scenecut=0:bframes=0',
            '-bufsize', '1000k',
            '-maxrate', '1000k',
            '-crf', '23',
            '-f', 'rtsp',
            '-rtsp_transport', 'tcp',
            '-muxdelay', '0.1',
            f'rtsp://localhost:{self.port}/{self.stream_name}'
        ]
        
        # 使用subprocess.PIPE来捕获错误输出
        self.ffmpeg_process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,  # 捕获错误输出但不显示
            bufsize=10**8  # 增加缓冲区大小
        )
        
        # 启动帧处理线程
        self.thread = threading.Thread(target=self._stream_frames)
        self.thread.daemon = True
        self.thread.start()
        
        return f"rtsp://localhost:{self.port}/{self.stream_name}"

    def stop(self):
        """停止RTSP流服务"""
        self.running = False
        if self.thread:
            self.thread.join()
        
        if self.ffmpeg_process:
            self.ffmpeg_process.terminate()
            self.ffmpeg_process.wait()
        
        # 清理管道文件
        if os.path.exists(self.pipe_path):
            os.remove(self.pipe_path)

    def put_frame(self, frame: np.ndarray):
        """将新帧放入队列"""
        if self.frame_queue.full():
            try:
                self.frame_queue.get_nowait()
            except:
                pass
        try:
            # 确保帧大小符合ffmpeg参数设置
            frame = cv2.resize(frame, (640, 480))
            self.frame_queue.put_nowait(frame)
        except:
            pass

    def _stream_frames(self):
        """处理帧并通过RTSP流发送"""
        with open(self.pipe_path, 'wb') as pipe:
            while self.running:
                if not self.frame_queue.empty():
                    frame = self.frame_queue.get()
                    try:
                        if len(frame.shape) == 3 and frame.shape[2] == 3:
                            pipe.write(frame.tobytes())
                            pipe.flush()
                    except Exception as e:
                        print(f"Error streaming frame: {e}")
                else:
                    time.sleep(0.001)

    def __del__(self):
        """清理资源"""
        self.stop() 
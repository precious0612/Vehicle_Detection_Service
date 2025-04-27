import cv2
import torch
import numpy as np
from deep_sort_realtime.deepsort_tracker import DeepSort
from collections import deque
from dataclasses import dataclass
from typing import Optional, List, Tuple, Iterator
import warnings
from functools import partial
from rtsp_server import RTSPOutputStream
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ProcessedFrame:
    frame: np.ndarray
    car_count: int
    current_vehicles: List[int]

def get_device():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Selected device: {device}")
    return device

def load_yolov5_model(device):
    logger.info(f"Loading YOLOv5 model to device: {device}")
    model = torch.hub.load('ultralytics/yolov5', 'yolov5s').to(device)
    logger.info("YOLOv5 model loaded successfully.")
    return model

class VideoProcessor:
    def __init__(self, rtsp_port: Optional[int] = None):
        warnings.filterwarnings("ignore", category=FutureWarning)
        self.device = get_device()
        self.model = load_yolov5_model(self.device)
        self.deepsort = DeepSort()
        self.car_count = 0
        self.vehicle_tracker = deque(maxlen=30)  # 30 frames window
        
        # RTSP输出设置
        self.rtsp_server = None
        self.rtsp_url = None
        if rtsp_port:
            logger.info(f"Starting RTSP server on port {rtsp_port}")
            self.rtsp_server = RTSPOutputStream(port=rtsp_port)
            self.rtsp_url = self.rtsp_server.start()
            logger.info(f"RTSP server started at {self.rtsp_url}")
        
    def get_rtsp_url(self) -> Optional[str]:
        """获取RTSP输出流的URL"""
        return self.rtsp_url if self.rtsp_server else None
        
    @staticmethod
    def _filter_vehicles(detections: np.ndarray) -> np.ndarray:
        return detections[detections[:, -1] == 2]
    
    @staticmethod
    def _format_detections(vehicles: np.ndarray) -> List[Tuple]:
        return [
            ([float(x1), float(y1), float(x2 - x1), float(y2 - y1)], float(conf), "vehicle")
            for x1, y1, x2, y2, conf, _ in vehicles
            if conf > 0.5
        ]
    
    @staticmethod
    def _draw_vehicle_info(frame: np.ndarray, track) -> np.ndarray:
        x1, y1, x2, y2 = map(int, track.to_ltrb())
        # 只绘制边界框，使用绿色
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        return frame
    
    def _update_vehicle_count(self, track_id: int) -> None:
        if track_id not in self.vehicle_tracker:
            self.vehicle_tracker.append(track_id)
            self.car_count += 1
    
    def process_frame(self, frame: np.ndarray) -> ProcessedFrame:
        # Detect vehicles using YOLO
        results = self.model(frame)
        detections = results.xyxy[0].cpu().numpy()
        
        # Filter and format detections
        vehicles = self._filter_vehicles(detections)
        deepsort_detections = self._format_detections(vehicles)
        
        current_vehicles = []
        
        if deepsort_detections:
            # Track vehicles
            tracks = self.deepsort.update_tracks(deepsort_detections, frame=frame)
            
            # Process each track
            for track in filter(lambda t: t.is_confirmed(), tracks):
                frame = self._draw_vehicle_info(frame, track)
                self._update_vehicle_count(track.track_id)
                current_vehicles.append(track.track_id)
        
        # 不在画面上显示车辆计数
        
        return ProcessedFrame(frame, self.car_count, current_vehicles)

    def process_stream(self, stream_url: str) -> Iterator[ProcessedFrame]:
        cap = cv2.VideoCapture(stream_url)
        
        try:
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                    
                yield self.process_frame(frame)
                
        finally:
            cap.release()
            
    def __del__(self):
        """清理资源"""
        if self.rtsp_server:
            self.rtsp_server.stop() 
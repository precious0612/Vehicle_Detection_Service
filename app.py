from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
import cv2
from typing import Dict, Optional, Tuple
from video_processor import VideoProcessor
from pydantic import BaseModel
from stream_worker import StreamWorker
import time

app = FastAPI(title="Vehicle Detection Service")

# Store active video processors and their stream URLs
processors: Dict[str, Tuple[VideoProcessor, str]] = {}
workers: Dict[str, StreamWorker] = {}

class StreamInfo(BaseModel):
    stream_url: str
    rtsp_port: Optional[int] = None

def generate_frames(processor: VideoProcessor, stream_url: str):
    """Generator function to yield processed video frames"""
    for processed_frame in processor.process_stream(stream_url):
        # Encode frame to JPEG
        _, buffer = cv2.imencode('.jpg', processed_frame.frame)
        # Convert to bytes
        frame_bytes = buffer.tobytes()
        # Yield frame in multipart format
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.post("/start_stream/{stream_id}")
async def start_stream(stream_id: str, stream_info: StreamInfo):
    """Start processing a new video stream"""
    if stream_id in workers:
        raise HTTPException(status_code=400, detail="Stream ID already exists")
    
    # 创建处理器实例，如果提供了RTSP端口则启用RTSP输出
    processor = VideoProcessor(rtsp_port=stream_info.rtsp_port)
    worker = StreamWorker(stream_id, stream_info.stream_url, processor)
    workers[stream_id] = worker
    worker.start()
    
    response = {
        "message": f"Stream {stream_id} started successfully",
        "http_url": f"/video_feed/{stream_id}"
    }
    
    # 如果启用了RTSP输出，添加RTSP URL到响应
    rtsp_url = processor.get_rtsp_url()
    if rtsp_url:
        response["rtsp_url"] = rtsp_url
    
    return response

@app.get("/video_feed/{stream_id}")
async def video_feed(stream_id: str):
    """Get the processed video stream"""
    if stream_id not in workers:
        raise HTTPException(status_code=404, detail="Stream not found")
    
    worker = workers[stream_id]
    def frame_gen():
        while True:
            frame = worker.get_latest_frame()
            if frame is not None:
                # Encode frame to JPEG
                _, buffer = cv2.imencode('.jpg', frame.frame)
                # Convert to bytes
                frame_bytes = buffer.tobytes()
                # Yield frame in multipart format
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            else:
                time.sleep(0.01)
    return StreamingResponse(frame_gen(), media_type="multipart/x-mixed-replace; boundary=frame")

@app.get("/stream_info/{stream_id}")
async def get_stream_info(stream_id: str):
    """Get stream information including URLs and statistics"""
    if stream_id not in workers:
        raise HTTPException(status_code=404, detail="Stream not found")
    
    worker = workers[stream_id]
    return {
        "http_url": f"/video_feed/{stream_id}",
        "rtsp_url": worker.processor.get_rtsp_url(),
        "input_url": worker.stream_url,
        "statistics": {
            "total_car_count": worker.processor.car_count,
            "current_vehicles": len(worker.processor.current_frame_vehicles)
        }
    }

@app.get("/statistics/{stream_id}")
async def get_statistics(stream_id: str):
    """Get vehicle statistics for a stream"""
    if stream_id not in workers:
        raise HTTPException(status_code=404, detail="Stream not found")
    
    worker = workers[stream_id]
    return {
        "total_car_count": worker.processor.car_count,
        "current_vehicles": len(worker.processor.current_frame_vehicles)
    }

@app.delete("/stop_stream/{stream_id}")
async def stop_stream(stream_id: str):
    """Stop processing a video stream"""
    if stream_id not in workers:
        raise HTTPException(status_code=404, detail="Stream not found")
    
    worker = workers.pop(stream_id)
    worker.stop()
    return {"message": f"Stream {stream_id} stopped successfully"} 
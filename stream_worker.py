import threading
import queue
import time

class StreamWorker(threading.Thread):
    def __init__(self, stream_id, stream_url, processor):
        super().__init__(daemon=True)
        self.stream_id = stream_id
        self.stream_url = stream_url
        self.processor = processor
        self.frame_queue = queue.Queue(maxsize=2)
        self.running = True

    def run(self):
        for processed_frame in self.processor.process_stream(self.stream_url):
            if not self.running:
                break
            # 只保留最新帧
            if self.frame_queue.full():
                try:
                    self.frame_queue.get_nowait()
                except queue.Empty:
                    pass
            self.frame_queue.put(processed_frame)
        self.running = False

    def get_latest_frame(self):
        try:
            return self.frame_queue.get(timeout=1)
        except queue.Empty:
            return None

    def stop(self):
        self.running = False

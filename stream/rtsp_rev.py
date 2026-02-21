import cv2
import threading
import queue
import time
import logging


class RTSPRECEIVEProducer(threading.Thread):
    def __init__(self,rtsp_url:str,frame_queue:queue.Queue):
        super().__init__()
        self.rtsp_url=rtsp_url
        self.frame_queue = frame_queue
        self.running = True
        self.cap =None
        self.logger = logging.getLogger("AIPipeline")
        self.daemon =True

    def _connect(self):
        if self.cap is not None:
            self.cap.release()

        self.logger.info(f"[rtsp_rev.py] Attempting to connect to: {self.rtsp_url}")

        gst_pipeline = (
            f'rtspsrc location={self.rtsp_url} latency=0 ! '
            'rtph264depay ! h264parse ! avdec_h264 ! '
            'videoconvert ! appsink drop=true max-buffers=1'
        )

        self.cap = cv2.VideoCapture(gst_pipeline, cv2.CAP_GSTREAMER)

        # Fallback to standard backend if GStreamer fails or is not available
        if not self.cap.isOpened():
            self.logger.warning("[rtsp_rev.py] GStreamer backend failed. Falling back to default backend.")
            self.cap = cv2.VideoCapture(self.rtsp_url)

        if  self.cap.isOpened():
            self.logger.info("[rtsp_rev.py] Connect established sucessfully.")
        else:
            self.logger.error("[rtsp_rev.py] Connection failed. Please check the RTSP URL or Network.")


    def run(self):
        """Continuously read frames. Automatically reconnects and logs events."""
        self._connect()

        while self.running:
            if not self.cap or not self.cap.isOpened():
                self.logger.warning("[rtsp_rev.py] Receive stream lost. Reconnecting in 3 seconds...")
                time.sleep(3)
                self._connect()
                continue
        
            ret, frame = self.cap.read()
            if not ret:
                    self.logger.error("[rtsp_rev.py] Empty frame received. Triggering reconnection...")
                    self.cap.release()
                    continue
            
            if self.frame_queue.full():
                    try:
                        # Drop the oldest frame to maintain real-time processing
                        self.frame_queue.get_nowait() 
                    except queue.Empty:
                        pass

            self.frame_queue.put(frame)
        
        if self.cap:
            self.cap.release()
        self.logger.info("[rtsp_rev.py] Thread stopped cleanly.")

    def stop(self):
        """Stop the producer thread."""
        self.running = False
        self.logger.debug("[rtsp_rev.py] Stop signal received.")


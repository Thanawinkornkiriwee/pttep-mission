import cv2
import queue
import time

from stream.base_input import BaseInputProducer


class RTSPRECEIVEProducer(BaseInputProducer):
    def __init__(self, rtsp_url: str, frame_queue: queue.Queue):
        
        super().__init__(source_url=rtsp_url, frame_queue=frame_queue)
        
        self.cap = None

    def _connect(self):
        """Internal method to initialize the RTSP connection."""
        if self.cap is not None:
            self.cap.release()

        # self.source_url (parent class uses)
        self.logger.info(f"[RTSPProducer] Attempting to connect to: {self.source_url}")

        gst_pipeline = (
            f'rtspsrc location={self.source_url} latency=0 ! '
            'rtph264depay ! h264parse ! avdec_h264 ! '
            'videoconvert ! appsink drop=true max-buffers=1'
        )

        self.cap = cv2.VideoCapture(gst_pipeline, cv2.CAP_GSTREAMER)

        # Fallback to standard backend if GStreamer fails or is not available
        if not self.cap.isOpened():
            self.logger.warning("[RTSPProducer] GStreamer backend failed. Falling back to default backend.")
            self.cap = cv2.VideoCapture(self.source_url)

        if self.cap.isOpened():
            self.logger.info("[RTSPProducer] Connect established successfully.")
        else:
            self.logger.error("[RTSPProducer] Connection failed. Please check the RTSP URL or Network.")

    def run(self):
        """Continuously read frames. Automatically reconnects and logs events."""
        self._connect()

        while self.running:  # self.running is defined in the parent class
            if not self.cap or not self.cap.isOpened():
                self.logger.warning("[RTSPProducer] Receive stream lost. Reconnecting in 3 seconds...")
                time.sleep(3)
                self._connect()
                continue
        
            ret, frame = self.cap.read()
            if not ret:
                self.logger.error("[RTSPProducer] Empty frame received. Triggering reconnection...")
                self.cap.release()
                continue
            
            if self.frame_queue.full():
                try:
                    # Drop the oldest frame to maintain real-time processing
                    self.frame_queue.get_nowait() 
                except queue.Empty:
                    pass

            self.frame_queue.put(frame)
            self.logger.debug("[RTSPProducer] Successfully grabbed a frame and put it in queue.")
        
        if self.cap:
            self.cap.release()
        self.logger.info("[RTSPProducer] Thread stopped cleanly.")
        
    
import cv2
import queue
import time
import requests
import numpy as np
from stream.base_input import BaseInputProducer

class HTTPRECEIVEProducer(BaseInputProducer):
    def __init__(self, http_url: str, frame_queue: queue.Queue):
        # Pass values to the parent class (BaseInputProducer) to handle base variables
        super().__init__(source_url=http_url, frame_queue=frame_queue)
        
        # Use requests.Session() for faster repeated requests through the same connection
        self.session = requests.Session()

    def _connect(self):
        
        self.logger.info(f"[HTTPProducer] Starting to poll images from: {self.source_url}")

    def _fetch_image(self):
        
        try:
           
            response = self.session.get(self.source_url, timeout=3)
            response.raise_for_status()
            
            html = response.text
            
            
            if 'src="' in html:
                # Extract only the /media/xxx.jpg path
                img_path = html.split('src="')[1].split('"')[0]
                
                # Build the full image URL
                img_url = self.source_url.rstrip('/') + img_path
                
                # Download the image file
                img_response = self.session.get(img_url, timeout=3)
                img_response.raise_for_status()
                
                # Convert raw image bytes into a Numpy array -> OpenCV color frame (for YOLO usage)
                image_array = np.asarray(bytearray(img_response.content), dtype=np.uint8)
                frame = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
                
                return frame
            else:
                self.logger.warning("[HTTPProducer] No image tag found in HTML. Make sure the media folder has images.")
                return None
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"[HTTPProducer] Network error trying to reach server: {e}")
            return None
        except Exception as e:
            self.logger.error(f"[HTTPProducer] Failed to decode image: {e}")
            return None

    def run(self):
        """Loop to continuously fetch new images and put them into the queue for AI processing"""
        self._connect()

        while self.running:
            frame = self._fetch_image()
            
            if frame is not None:
                # Keep only the latest frame in the queue (discard old ones)
                if self.frame_queue.full():
                    try:
                        self.frame_queue.get_nowait() 
                    except queue.Empty:
                        pass
                        
                self.frame_queue.put(frame)
            
            # Delay to avoid sending requests to simulate_image.py too frequently (1 request per second)
            time.sleep(1.0)
        
        self.logger.info("[HTTPProducer] Thread stopped cleanly.")
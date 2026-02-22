import cv2
import queue
import time
import requests
import numpy as np
from urllib.parse import urljoin

# Import the base template
from stream.base_input import BaseInputProducer

class HTTPRECEIVEProducer(BaseInputProducer):
    def __init__(self, http_url: str, frame_queue: queue.Queue):
        # Pass variables to the parent class (BaseInputProducer)
        super().__init__(source_url=http_url, frame_queue=frame_queue)
        
        # Use requests.Session() for better performance on repeated requests
        self.session = requests.Session()
        
        # Connection state tracker to prevent log spamming during downtime
        self.is_connected = True 

    def _connect(self):
        """Log the initial polling action."""
        self.logger.info(f"[HTTPProducer] Starting to poll images from: {self.source_url}")

    def _fetch_image(self):
        """Fetch the latest image. Handles both direct image and HTML responses."""
        try:
            # 1. Send GET request to the server
            response = self.session.get(self.source_url, timeout=3)
            response.raise_for_status()
            
            # If the connection was previously lost, log the recovery
            if not self.is_connected:
                self.logger.info("[HTTPProducer] Connection re-established successfully.")
                self.is_connected = True
            
            # 2. Check the Content-Type header to determine the response format
            content_type = response.headers.get('Content-Type', '')
            
            # --- Case 1: Server returns an image file directly ---
            if 'image' in content_type:
                # Convert bytes directly to an OpenCV frame
                image_array = np.asarray(bytearray(response.content), dtype=np.uint8)
                frame = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
                return frame
                
            # --- Case 2: Server returns HTML containing an image tag ---
            else:
                html = response.text
                if 'src="' in html:
                    # Extract the image path (e.g., /media/pic.jpg)
                    img_path = html.split('src="')[1].split('"')[0]
                    
                    # Safely join the base URL with the extracted path
                    img_url = urljoin(self.source_url, img_path)
                    
                    # Request the actual image file
                    img_response = self.session.get(img_url, timeout=3)
                    img_response.raise_for_status()
                    
                    # Convert to OpenCV frame
                    image_array = np.asarray(bytearray(img_response.content), dtype=np.uint8)
                    frame = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
                    return frame
                else:
                    # Only warn if connected but no image tag is found
                    self.logger.warning("[HTTPProducer] No image tag found in HTML. Check media folder.")
                    return None
                    
        except requests.exceptions.RequestException as e:
            # Gracefully handle server down/network drop without spamming the log
            if self.is_connected:
                self.logger.warning(f"[HTTPProducer] Connection lost. Server might be down. Retrying in background...")
                self.is_connected = False
            return None
            
        except Exception as e:
            self.logger.error(f"[HTTPProducer] Failed to decode image: {e}")
            return None

    def run(self):
        """Continuously poll the server and put frames into the queue."""
        self._connect()

        while self.running:
            frame = self._fetch_image()
            
            if frame is not None:
                # Ensure the queue only contains the absolute latest frame
                if self.frame_queue.full():
                    try:
                        self.frame_queue.get_nowait() 
                    except queue.Empty:
                        pass
                        
                self.frame_queue.put(frame)
                
                # Normal polling interval (1 second)
                time.sleep(1.0)
            else:
                # If disconnected or error occurred, wait 3 seconds before trying again 
                # (Matches RTSP reconnect behavior and saves CPU)
                time.sleep(3.0)
        
        self.logger.info("[HTTPProducer] Thread stopped cleanly.")
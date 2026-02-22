import logging
import traceback 
from ultralytics import YOLO

class YOLOTask:
    def __init__(self, config: dict):
        self.logger = logging.getLogger("AIPipeline")
        try:
            self.config = config['object_detection']
            model_path = self.config['yolo_model']
            self.conf = self.config.get('confidence_threshold', 0.25) 
            
            self.logger.info(f"[ObjectDetectionTask] Loading YOLO model from {model_path}...")
            self.model = YOLO(model_path)
            self.logger.info("[ObjectDetectionTask] YOLO model loaded successfully.")
            
        except Exception as e:
           
            self.logger.error(f"[ObjectDetectionTask] Failed to initialize YOLO model: {str(e)}")
            self.logger.error(traceback.format_exc())
            raise 

    def execute(self, frame):
        try:
            
            results = self.model.predict(
                source=frame, 
                conf=self.conf, 
                verbose=False
            )
            
            if len(results) == 0:
                self.logger.warning("[ObjectDetectionTask] No results returned from model.")
                return None
                
            return results[0]

        except Exception as e:
            self.logger.error(f"[YOLOTask] Error during inference: {str(e)}")
            self.logger.debug(traceback.format_exc()) 
            return None
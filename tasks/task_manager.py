import threading
import queue
import time
import logging
import cv2

from tasks.object_detection_task import YOLOTask

# from tasks.ocr_task import OCRTask
# from tasks.analog_task import AnalogTask
# from tasks.classification_task import ClassificationTask

class TaskManager(threading.Thread):
    def __init__(self, config: dict, frame_queue: queue.Queue):
        super().__init__()
        self.config = config
        self.frame_queue = frame_queue
        self.running = True
        self.daemon = True
        self.logger = logging.getLogger("AIPipeline")
        
        self.yolo = YOLOTask(config)
        
        # 2. เตรียมแผนกอื่นๆ (คอมเมนต์ไว้ก่อน)
        # self.ocr_task = OCRTask(config)
        # self.analog_task = AnalogTask(config)
        # self.classification_task = ClassificationTask(config)

    def run(self):
        self.logger.info("[TaskManager] Started pulling frames for AI Processing.")
        
        while self.running:
            try:
                
                frame = self.frame_queue.get(timeout=1.0)
                frame_h, frame_w = frame.shape[:2] 
                
             
                detection_result = self.yolo.execute(frame)
                boxes = detection_result.boxes
                
                if len(boxes) > 0:
                    
                    for box in boxes:
                        cls_id = int(box.cls[0])
                        label = detection_result.names[cls_id] 
                        
                        
                        # xyxy TOPLEFT(x1,y1) BOTTOMTRIGHT(x2,y2)
                        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                        # prevent coordinate exceed in image
                        x1, y1 = max(0, x1), max(0, y1)
                        x2, y2 = min(frame_w, x2), min(frame_h, y2)
                        
                        cropped_img = frame[y1:y2, x1:x2]

                        if cropped_img.size == 0:
                            continue
                        

                        if label == "digital-gauge":
                            self.logger.debug(f"[Router] Found {label}, routing cropped image to OCR Task.")
                            # result = self.ocr_task.execute(cropped_img)
                            
                        elif label == "analog-gauge":
                            self.logger.debug(f"[Router] Found {label}, routing cropped image to Analog Task.")
                            # result = self.analog_task.execute(cropped_img)
                            
                        else:
                            
                            self.logger.debug(f"[Router] Found {label}, routing cropped image to Classification Task.")
                            # result = self.classification_task.execute(cropped_img)
                            
                        # (ทางเลือกเสริม) ถ่ายภาพที่ถูก Crop บันทึกลงเครื่องเพื่อตรวจสอบว่าตัดถูกไหม
                        # cv2.imwrite(f"test_crop_{label}_{time.time()}.jpg", cropped_img)

            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"[TaskManager] Error during processing: {e}", exc_info=True)

    def stop(self):
        self.running = False
        self.logger.debug("[TaskManager] Stop signal received.")
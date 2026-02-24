import threading
import queue
import time
import logging
import cv2
import traceback
from cores.visualizer import Visualizer

from tasks.object_detection_task import YOLOTask
from tasks.ocr_task import OCRTask
from tasks.classification_task import ClassificationTask

# from tasks.analog_task import AnalogTask


class TaskManager(threading.Thread):
    def __init__(self, config: dict, frame_queue: queue.Queue, output_queues: dict):
        super().__init__()
        self.config = config
        self.frame_queue = frame_queue
        self.output_queues = output_queues
        self.running = True
        
        self.logger = logging.getLogger("AIPipeline")

        self.logger.info("[TaskManager] Initializing AI Models...")
        self.yolo = YOLOTask(config)
        self.ocr_task = OCRTask(config)
        self.cls_task = ClassificationTask(config)
        
        
        self.visualizer = Visualizer(config)

    def push_to_stream(self, stream_name, img):
        if stream_name in self.output_queues and img is not None:
            out_w = self.config.get('output_stream', {}).get('width', 640)
            out_h = self.config.get('output_stream', {}).get('height', 480)
            resized_img = cv2.resize(img, (out_w, out_h))
            
            if not self.output_queues[stream_name].full():
                self.output_queues[stream_name].put(resized_img)

    def run(self):
        while self.running:
            try:
                frame = self.frame_queue.get(timeout=1.0)
                
                detection_result = self.yolo.execute(frame)
                
                if detection_result is None:
                    continue
                
                annotated_frame = detection_result.plot()
                self.push_to_stream('od', annotated_frame)
                
                boxes = detection_result.boxes
                if boxes is not None and len(boxes) > 0:
                    for box in boxes:
                        cls_id = int(box.cls[0].item())
                        label = detection_result.names[cls_id] 
                        
                        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                        cropped_img = frame[y1:y2, x1:x2]
                        if cropped_img.size == 0: 
                            continue
                        
                        if label == "digital-gauge": 
                            text, conf = self.ocr_task.execute(cropped_img)
                            if text:
                                ocr_display = cropped_img.copy()
                                
                               
                                display_text = text
                                ocr_display = self.visualizer.draw_unicode_text(
                                    ocr_display, 
                                    display_text, 
                                    position=(5, 5),     
                                    font_size=25,        
                                    color=(0, 0, 255)    
                                )
                                
                                self.push_to_stream('ocr', ocr_display)
                                
                        elif label == "analog-gauge":
                            self.push_to_stream('analog', cropped_img)
                        else:
                            
                            pred_class, conf = self.cls_task.execute(cropped_img)
                            
                            if pred_class:
                                
                                cls_display = cropped_img.copy()
                                display_text = f"{pred_class.upper()} ({conf:.1f}%)"
                                print('xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',display_text)
                             
                                cls_display = self.visualizer.draw_unicode_text(
                                    cls_display, 
                                    display_text, 
                                    position=(5, 5), 
                                    font_size=30, 
                                    color=(0, 255, 0) if pred_class == "normal" else (0, 0, 255) 
                                )
                                self.push_to_stream('cls', cls_display)
                            
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"[TaskManager] Critical error in AI loop: {e}")
                self.logger.debug(traceback.format_exc())

    def stop(self):
        self.running = False
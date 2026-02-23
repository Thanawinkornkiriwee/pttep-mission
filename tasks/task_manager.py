import threading
import queue
import time
import logging
import cv2

from tasks.object_detection_task import YOLOTask

from tasks.ocr_task import OCRTask
# from tasks.analog_task import AnalogTask
# from tasks.classification_task import ClassificationTask

class TaskManager(threading.Thread):
    def __init__(self, config: dict, frame_queue: queue.Queue, output_queues: dict): # รับเป็น dict
        super().__init__()
        self.config = config
        self.frame_queue = frame_queue
        self.output_queues = output_queues
        # ... (โค้ดโหลดโมเดลอื่นๆ เหมือนเดิม) ...

    def push_to_stream(self, stream_name, img):
        """ฟังก์ชันช่วยย่อภาพและยัดลงตะกร้าแบบอัตโนมัติ"""
        if stream_name in self.output_queues and img is not None:
            out_w = self.config.get('output_stream', {}).get('width', 640)
            out_h = self.config.get('output_stream', {}).get('height', 480)
            # ต้องบังคับย่อภาพให้มีขนาดตรงกับ GStreamer เพื่อกันภาพล้ม
            resized_img = cv2.resize(img, (out_w, out_h))
            
            if not self.output_queues[stream_name].full():
                self.output_queues[stream_name].put(resized_img)

    def run(self):
        while self.running:
            try:
                frame = self.frame_queue.get(timeout=1.0)
                frame_h, frame_w = frame.shape[:2] 
                
                detection_result = self.yolo.execute(frame)
                
                # 1. โยนภาพหลักเข้าสตรีม Object Detection ทันที
                annotated_frame = detection_result.plot()
                self.push_to_stream('od', annotated_frame)
                
                boxes = detection_result.boxes
                if len(boxes) > 0:
                    for box in boxes:
                        cls_id = int(box.cls[0])
                        label = detection_result.names[cls_id] 
                        
                        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                        # ... (ขอบเขต x1,y1 เหมือนเดิม) ...
                        cropped_img = frame[y1:y2, x1:x2]
                        if cropped_img.size == 0: continue
                        
                        # 2. ถ้าเป็น OCR
                        if label == "digital-gauge": 
                            text, conf = self.ocr_task.execute(cropped_img)
                            if text:
                                # วาดผลลัพธ์ลงบนรูปที่ถูกตัด
                                ocr_display = cropped_img.copy()
                                cv2.putText(ocr_display, text, (5, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                                
                                # โยนรูปที่ถูกตัดเข้าสตรีม OCR (ไม่ต้องสนใจเรื่องรูปเล็ก เพราะ push_to_stream จะย่อ/ขยายให้เอง)
                                self.push_to_stream('ocr', ocr_display)
                                
                        elif label == "analog-gauge":
                            pass # โยนเข้า self.push_to_stream('analog', res_img)
                            
            except queue.Empty:
                continue
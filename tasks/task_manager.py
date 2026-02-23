import threading
import queue
import time
import logging
import cv2
import traceback # เพิ่มตัวนี้เพื่อดู Error แบบละเอียด

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
        self.running = True

        # >>> ต้องมี 2 บรรทัดนี้ด้วยครับ <<<
        self.yolo = YOLOTask(config)
        self.ocr_task = OCRTask(config)

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
                # 1. รับภาพจากกล้อง
                frame = self.frame_queue.get(timeout=1.0)
                
                # 2. ทำ Object Detection
                detection_result = self.yolo.execute(frame)
                label = detection_result.names[cls_id] 
                print(f"DEBUG: YOLO detected -> '{label}'") # เพิ่มบรรทัดนี้เพื่อเช็คชื่อ
                
                # ป้องกันกรณี YOLO คืนค่า None
                if detection_result is None:
                    continue
                
                # 3. วาดกล่องและโยนภาพหลักเข้าสตรีม OD
                annotated_frame = detection_result.plot()
                self.push_to_stream('od', annotated_frame)
                
                boxes = detection_result.boxes
                if boxes is not None and len(boxes) > 0:
                    for box in boxes:
                        # ใช้ .item() เพื่อดึงตัวเลขออกจาก Tensor ของ PyTorch อย่างปลอดภัย
                        cls_id = int(box.cls[0].item())
                        label = detection_result.names[cls_id] 
                        
                        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                        cropped_img = frame[y1:y2, x1:x2]
                        
                        if cropped_img.size == 0: 
                            continue
                        
                        # 2. ถ้าเป็น OCR
                        if label == "digital-gauge": 
                            # ตรวจสอบว่าเปิดใช้งาน self.ocr_task หรือยัง ใน __init__
                            text, conf = self.ocr_task.execute(cropped_img)
                            if text:
                                ocr_display = cropped_img.copy()
                                cv2.putText(ocr_display, text, (5, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                                self.push_to_stream('ocr', ocr_display)
                                
                        elif label == "analog-gauge":
                            # ลองโยนรูปเข้าสตรีมแบบไม่ต้อง pass เพื่อเทสการแสดงผล
                            self.push_to_stream('analog', cropped_img)
                            
            except queue.Empty:
                continue
            except Exception as e:
                # แก้ Error จุดที่ 2: ดักจับ Error ทุกอย่างไม่ให้ Thread ตาย และพิมพ์ลง Log
                self.logger.error(f"[TaskManager] Critical error in AI loop: {e}")
                self.logger.debug(traceback.format_exc())


    def stop(self):
        self.running = False
import os
import json
import cv2
import numpy as np
import logging

os.environ["LRU_CACHE_CAPACITY"] = "1"
os.environ["TORCH_CPP_LOG_LEVEL"] = "ERROR"

import torch
try:
    torch.backends.mkldnn.enabled = False 
    torch.backends.nnpack.enabled = False
except:
    pass

from torchvision.transforms.v2 import Resize, Compose, ToImage, ToDtype
from doctr.models import recognition
from ultralytics import YOLO  
import warnings
warnings.filterwarnings("ignore")

class OCRTask:
    
    def __init__(self, config: dict):
        self.logger = logging.getLogger("AIPipeline")
        self.config = config.get('ocr', {})
        
        self.model_dir = self.config.get('model_dir', '')
        self.conf_threshold = self.config.get('confidence_threshold', 0.8)
        
        self.display_yolo_path = self.config.get('display_yolo_model', '')
        self.display_conf = self.config.get('display_confidence_threshold', 0.5)
        self.display_model = None
        
        if self.config.get('device', 'auto') == 'auto':
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = self.config.get('device', 'cpu')

        self.model = None
        self.transforms = None
        
        
        self._initialize_display_model()
        self._initialize_model()

    def _initialize_display_model(self):
        
        if self.display_yolo_path and os.path.exists(self.display_yolo_path):
            try:
                self.logger.info(f"[OCRTask] Loading Display YOLO model from {self.display_yolo_path}...")
                self.display_model = YOLO(self.display_yolo_path)
                self.logger.info("[OCRTask] Display YOLO model loaded successfully.")
            except Exception as e:
                self.logger.error(f"[OCRTask] Failed to initialize Display YOLO model: {e}")
        else:
            self.logger.warning(f"[OCRTask] Display YOLO model not found at {self.display_yolo_path}. Will use full crop instead.")

    def _initialize_model(self):
        
        parent_dir = os.path.dirname(self.model_dir)
        config_path = os.path.join(parent_dir, "config.json")
        ckpt_path = os.path.join(self.model_dir)
        

        if not os.path.exists(config_path) or not os.path.exists(ckpt_path):
            self.logger.error(f"[OCRTask] Model files missing. Please check model_dir: {self.model_dir}")
            return

        self.logger.info(f"[OCRTask] Loading config from {config_path}...")
        with open(config_path, "r") as f:
            cfg = json.load(f)

        vocab = cfg.get("vocab")
        input_size = tuple(cfg.get("INPUT_SIZE", [32, 128])) 
        model_arch = cfg.get("MODEL_ARCH", "parseq")

        self.logger.info(f"[OCRTask] Model: {model_arch}, Input Size: {input_size}, Device: {self.device.upper()}")

        try:
            self.model = recognition.__dict__[model_arch](
                pretrained=False, 
                vocab=vocab, 
                input_shape=(3, input_size[0], input_size[1]) 
            )
        except Exception as e:
            self.logger.error(f"[OCRTask] Error initializing model architecture: {e}")
            return

        self.logger.info(f"[OCRTask] Loading weights from {ckpt_path}...")
        state_dict = torch.load(ckpt_path, map_location=self.device)
        
        if "model_state_dict" in state_dict:
            state_dict = state_dict["model_state_dict"] 
        clean_state_dict = {k.replace("module.", ""): v for k, v in state_dict.items()}
        
        try:
            self.model.load_state_dict(clean_state_dict)
        except RuntimeError as e:
            self.logger.warning(f"[OCRTask] Weight mismatch ignored: {e}")

        self.model.to(self.device)
        self.model.eval()

        self.transforms = Compose([
            ToImage(),
            ToDtype(torch.float32, scale=True), 
            Resize(input_size, antialias=True),
        ])
        
        self.logger.info("[OCRTask] Model loaded and ready for inference.")

    def execute(self, cropped_img):
        if self.model is None or cropped_img is None or cropped_img.size == 0:
            return None, 0.0

        try:
            # ==========================================
            #  # Crop display digital gauge
            # ==========================================
            final_img_for_ocr = cropped_img 
            
            if self.display_model is not None:
            
                results = self.display_model.predict(source=cropped_img, conf=self.display_conf, verbose=False)
                
                if len(results) > 0 and len(results[0].boxes) > 0:
                    
                    box = results[0].boxes[0]
                    x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                    
                  
                    h, w = cropped_img.shape[:2]
                    x1, y1 = max(0, x1), max(0, y1)
                    x2, y2 = min(w, x2), min(h, y2)
                    
                    display_crop = cropped_img[y1:y2, x1:x2]
               
                    cv2.imwrite('output_image.png', display_crop)
                    
                   
                    if display_crop.size > 0:
                        final_img_for_ocr = display_crop

            # ==========================================
            # DOCTR 
            # ==========================================
            with torch.no_grad():

                target_width = 1536
                (h, w) = final_img_for_ocr.shape[:2]
                r = target_width / float(w)
                dim = (target_width, int(h * r))

                resized = cv2.resize(final_img_for_ocr, dim, interpolation=cv2.INTER_AREA)
                cv2.imwrite('resize_display.jpg',resized)
                
                img_rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
                img_tensor = self.transforms(img_rgb).unsqueeze(0).to(self.device)

                output = self.model(img_tensor, target=None, return_preds=True)
                
                if "preds" in output:
                    pred_text, conf = output['preds'][0]
                else:
                    pred_text, conf = output[0]

                return pred_text, conf
                
        except Exception as e:
            self.logger.error(f"[OCRTask] Inference error: {e}", exc_info=True)
            return None, 0.0
import os
import torch
from torch import nn
from torchvision import transforms
from torchvision.models import resnet18
import torch.nn.functional as F
from PIL import Image
import logging
import cv2

from tasks.prototypicalNetwork import PrototypicalNetworks 

class ClassificationTask:
    def __init__(self, config: dict):
        self.logger = logging.getLogger("AIPipeline")
        self.config = config.get('classification', {})
        
        self.model_path = self.config.get('model_path', '')
        self.dataset_root = self.config.get('dataset_root', '')
        self.img_size = self.config.get('img_size', 112)
        self.shots = self.config.get('shots', 20)
        
        device_str = self.config.get('device', 'cpu')
        self.device = torch.device("cuda" if torch.cuda.is_available() and device_str == "cuda" else "cpu")

        self.transform = transforms.Compose([
            transforms.Resize([self.img_size, self.img_size]),
            transforms.ToTensor(),
            transforms.Normalize((0,), (1,))
        ])

        self.model = None
        self.prototypes = {}

        self._initialize_model()

    def _initialize_model(self):
        if not os.path.exists(self.model_path):
            self.logger.error(f"[ClassificationTask] Model weights not found at: {self.model_path}")
            return
            
        try:
            self.logger.info(f"[ClassificationTask] Loading Prototypical Network from {self.model_path}...")
            convolutional_network = resnet18(pretrained=False)
            convolutional_network.fc = nn.Flatten()
            self.model = PrototypicalNetworks(convolutional_network)
            
            self.model.load_state_dict(torch.load(self.model_path, map_location=self.device))
            self.model.to(self.device)
            self.model.eval()
            self.logger.info("[ClassificationTask] Model loaded successfully.")
            
            if os.path.exists(self.dataset_root):
                self._build_prototypes()
            else:
                self.logger.warning(f"[ClassificationTask] Dataset root not found: {self.dataset_root}. Prototypes cannot be built.")
                
        except Exception as e:
            self.logger.error(f"[ClassificationTask] Failed to initialize model: {e}")

    def _build_prototypes(self):
        self.logger.info(f"[ClassificationTask] Building Class Prototypes (Shots: {self.shots})...")
        class_names = sorted(os.listdir(self.dataset_root))

        for class_name in class_names:
            class_dir = os.path.join(self.dataset_root, class_name)
            if not os.path.isdir(class_dir): continue
            
            images = []
            image_files = os.listdir(class_dir)[:self.shots] 
            
            for img_file in image_files:
                img_path = os.path.join(class_dir, img_file)
                try:
                    img = Image.open(img_path).convert('RGB')
                    img_tensor = self.transform(img)
                    images.append(img_tensor)
                except Exception as e:
                    self.logger.debug(f"[ClassificationTask] Skipping image {img_file}: {e}")
            
            if not images:
                continue

            input_tensor = torch.stack(images).to(self.device)
            with torch.no_grad():
                features = self.model.backbone(input_tensor) 
            
            self.prototypes[class_name] = features.mean(dim=0)
            
        self.logger.info(f"[ClassificationTask] Prototypes built for classes: {list(self.prototypes.keys())}")

    def execute(self, image_bgr):
        
        if self.model is None or not self.prototypes or image_bgr is None or image_bgr.size == 0:
            return None, 0.0

        try:

            image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
            img_pil = Image.fromarray(image_rgb)
            
            input_tensor = self.transform(img_pil).unsqueeze(0).to(self.device)

            with torch.no_grad():
                query_feature = self.model.backbone(input_tensor).squeeze(0)

            distances = {}
            for class_name, proto_vec in self.prototypes.items():
                dist = torch.dist(query_feature, proto_vec).item()
                distances[class_name] = dist

            if not distances:
                return None, 0.0

            predicted_class = min(distances, key=distances.get)
            
            values = torch.tensor([-d for d in distances.values()])
            probs = F.softmax(values, dim=0)
            confidence = probs.max().item() * 100
            
            return predicted_class, confidence
            
        except Exception as e:
            self.logger.error(f"[ClassificationTask] Inference error: {e}")
            return None, 0.0
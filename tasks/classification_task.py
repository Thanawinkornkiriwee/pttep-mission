import os
import torch
from torch import nn
from torchvision import transforms
from torchvision.models import resnet152, ResNet152_Weights
import torch.nn.functional as F
from PIL import Image
import logging
import cv2
from tasks.prototypicalNetwork import PrototypicalNetworks


class ResNet152Backbone(nn.Module):
    def __init__(self, pretrained=False):
        super().__init__()
        if pretrained:
            self.backbone = resnet152(weights=ResNet152_Weights.IMAGENET1K_V1)
        else:
            self.backbone = resnet152(weights=None)
        self.backbone.fc = nn.Identity()
        self.feature_dim = 2048
    
    def forward(self, x):
        x = self.backbone.conv1(x)
        x = self.backbone.bn1(x)
        x = self.backbone.relu(x)
        x = self.backbone.maxpool(x)
        x = self.backbone.layer1(x)
        x = self.backbone.layer2(x)
        x = self.backbone.layer3(x)
        x = self.backbone.layer4(x)
        x = self.backbone.avgpool(x)
        x = torch.flatten(x, 1)
        return x


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

        # Define Transforms
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
            
            
            convolutional_network = ResNet152Backbone(pretrained=False)
            self.model = PrototypicalNetworks(convolutional_network)
            
           
            checkpoint = torch.load(self.model_path, map_location=self.device, weights_only=False)
            
            if 'model_state_dict' in checkpoint:
                self.model.load_state_dict(checkpoint['model_state_dict'])
                self.logger.info(f"[ClassificationTask] Loaded from checkpoint (epoch {checkpoint.get('epoch', '?')})")
            else:
                self.model.load_state_dict(checkpoint)

            self.model.to(self.device)
            self.model.eval()
            self.logger.info("[ClassificationTask] Model loaded successfully.")
            
            # Build Prototypes
            if os.path.exists(self.dataset_root):
                self._build_prototypes()
            else:
                self.logger.warning(f"[ClassificationTask] Dataset root not found: {self.dataset_root}. Prototypes cannot be built.")
                
        except Exception as e:
            self.logger.error(f"[ClassificationTask] Failed to initialize model: {e}", exc_info=True)

    def _build_prototypes(self):
        self.logger.info(f"[ClassificationTask] Building Class Prototypes from: {self.dataset_root}")
        class_names = sorted([d for d in os.listdir(self.dataset_root) if os.path.isdir(os.path.join(self.dataset_root, d))])

        for class_name in class_names:
            class_dir = os.path.join(self.dataset_root, class_name)
            images = []
            valid_extensions = ('.png', '.jpg', '.jpeg', '.bmp')
            
            image_files = [f for f in os.listdir(class_dir) if f.lower().endswith(valid_extensions)][:self.shots]
            
            for img_file in image_files:
                img_path = os.path.join(class_dir, img_file)
                try:
                    img = Image.open(img_path).convert('RGB')
                    img_tensor = self.transform(img)
                    images.append(img_tensor)
                except Exception as e:
                    self.logger.debug(f"[ClassificationTask] Warning: Could not load {img_path}: {e}")
            
            if len(images) == 0:
                continue

            input_tensor = torch.stack(images).to(self.device)
            with torch.no_grad():
                features = self.model.backbone(input_tensor) 
            
            prototype = features.mean(dim=0)
            self.prototypes[class_name] = prototype
            self.logger.info(f"[ClassificationTask] Prototype created for '{class_name}' using {len(images)} images.")
            
        self.logger.info(f"[ClassificationTask] Prototypes ready: {list(self.prototypes.keys())}")

    def execute(self, image_bgr):
     
        if self.model is None or not self.prototypes or image_bgr is None or image_bgr.size == 0:
            return None, 0.0

        try:
           
            image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
            img_pil = Image.fromarray(image_rgb)
            
            input_tensor = self.transform(img_pil).unsqueeze(0).to(self.device)

            with torch.no_grad():
                query_feature = self.model.backbone(input_tensor).squeeze(0)

            distances = {name: torch.dist(query_feature, vec).item() for name, vec in self.prototypes.items()}

            if not distances:
                return None, 0.0

            predicted_class = min(distances, key=distances.get)
            
            probs = F.softmax(torch.tensor([-d for d in distances.values()]), dim=0)
            confidence = probs.max().item() * 100
            
            return predicted_class, confidence
            
        except Exception as e:
            self.logger.error(f"[ClassificationTask] Inference error: {e}")
            return None, 0.0
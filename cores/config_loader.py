import yaml
import os

def load_config(config_path="configs/config.yaml"):
    """read config.yaml and return Dictionary"""
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Not Found Config at: {config_path}")
        
    with open(config_path, 'r', encoding='utf-8') as file:
        config = yaml.safe_load(file)
    return config
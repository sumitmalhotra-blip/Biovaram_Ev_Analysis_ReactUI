#!/usr/bin/env python3
"""
EV Viability Classifier - Inference Script
Uses trained CNN model to classify EVs as viable or non-viable
"""

import cv2
import numpy as np
from tensorflow import keras
import json
import os
from typing import List, Dict, Tuple


class EVViabilityClassifier:
    """Load and use trained model for EV classification"""
    
    def __init__(self, model_path='ev_viability_model.h5', metadata_path='model_metadata.json'):
        self.model_path = model_path
        self.metadata_path = metadata_path
        self.model = None
        self.img_size = 128
        self.class_names = ["non_viable", "viable"]
        
        self.load_model()
    
    def load_model(self):
        """Load trained model and metadata"""
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Model file not found: {self.model_path}")
        
        print(f"Loading model from {self.model_path}...")
        self.model = keras.models.load_model(self.model_path)
        
        # Load metadata if available
        if os.path.exists(self.metadata_path):
            with open(self.metadata_path, 'r') as f:
                metadata = json.load(f)
                self.img_size = metadata.get('img_size', 128)
                self.class_names = metadata.get('class_names', ["non_viable", "viable"])
        
        print("Model loaded successfully")
    
    def preprocess_image(self, image_path: str) -> np.ndarray:
        """Preprocess single image for prediction"""
        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            raise ValueError(f"Could not read image: {image_path}")
        
        # Resize
        img = cv2.resize(img, (self.img_size, self.img_size))
        
        # Normalize
        img = img.astype('float32') / 255.0
        
        # Add batch and channel dimensions
        img = np.expand_dims(img, axis=-1)
        img = np.expand_dims(img, axis=0)
        
        return img
    
    def predict(self, image_path: str, threshold: float = 0.5) -> Dict:
        """
        Predict viability of single EV image
        
        Returns:
            dict with keys: 'class', 'confidence', 'viable_prob', 'non_viable_prob'
        """
        # Preprocess
        img = self.preprocess_image(image_path)
        
        # Predict
        prob = self.model.predict(img, verbose=0)[0][0]
        
        # Classify
        is_viable = prob > threshold
        class_name = "viable" if is_viable else "non_viable"
        confidence = prob if is_viable else (1 - prob)
        
        return {
            'class': class_name,
            'confidence': float(confidence),
            'viable_prob': float(prob),
            'non_viable_prob': float(1 - prob),
            'is_viable': bool(is_viable)
        }
    
    def predict_batch(self, image_paths: List[str], threshold: float = 0.5) -> List[Dict]:
        """Predict viability for multiple images"""
        results = []
        for img_path in image_paths:
            try:
                result = self.predict(img_path, threshold)
                result['image_path'] = img_path
                results.append(result)
            except Exception as e:
                print(f"Error processing {img_path}: {e}")
                results.append({
                    'image_path': img_path,
                    'error': str(e)
                })
        return results


def demo_inference():
    """Demo: classify test images"""
    print("=" * 60)
    print("EV Viability Classifier - Inference Demo")
    print("=" * 60)
    
    # Initialize classifier
    classifier = EVViabilityClassifier(
        model_path='ev_viability_model.h5',
        metadata_path='model_metadata.json'
    )
    
    # Test on sample images
    test_dirs = ['training_data/viable', 'training_data/non_viable']
    
    for test_dir in test_dirs:
        if not os.path.exists(test_dir):
            continue
        
        print(f"\nTesting on: {test_dir}")
        print("-" * 60)
        
        for img_file in os.listdir(test_dir)[:3]:  # Test first 3 images
            if img_file.endswith(('.png', '.jpg', '.jpeg', '.tif', '.tiff')):
                img_path = os.path.join(test_dir, img_file)
                result = classifier.predict(img_path)
                
                print(f"\nImage: {img_file}")
                print(f"  Predicted: {result['class']}")
                print(f"  Confidence: {result['confidence']:.2%}")
                print(f"  Viable prob: {result['viable_prob']:.2%}")
                print(f"  Non-viable prob: {result['non_viable_prob']:.2%}")


if __name__ == "__main__":
    demo_inference()

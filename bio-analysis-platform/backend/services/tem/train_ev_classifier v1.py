#!/usr/bin/env python3
"""
EV Viability Classifier - CNN Training Script
Trains a deep learning model to classify EVs as viable or non-viable
"""

import os
import numpy as np
import cv2
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers, models
from tensorflow.keras.preprocessing.image import ImageDataGenerator
import json
import matplotlib.pyplot as plt
from datetime import datetime


class EVViabilityTrainer:
    """Train CNN to classify EV viability"""
    
    def __init__(self, data_dir="training_data", img_size=128):
        self.data_dir = data_dir
        self.img_size = img_size
        self.model = None
        self.history = None
        self.class_names = ["non_viable", "viable"]
        
    def load_and_preprocess_data(self):
        """Load images from directories and preprocess"""
        print("Loading training data...")
        
        images = []
        labels = []
        
        # Load viable images (label = 1)
        viable_dir = os.path.join(self.data_dir, "viable")
        if os.path.exists(viable_dir):
            for img_file in os.listdir(viable_dir):
                if img_file.endswith(('.png', '.jpg', '.jpeg', '.tif', '.tiff')):
                    img_path = os.path.join(viable_dir, img_file)
                    img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
                    if img is not None:
                        img = cv2.resize(img, (self.img_size, self.img_size))
                        images.append(img)
                        labels.append(1)  # viable
        
        # Load non-viable images (label = 0)
        non_viable_dir = os.path.join(self.data_dir, "non_viable")
        if os.path.exists(non_viable_dir):
            for img_file in os.listdir(non_viable_dir):
                if img_file.endswith(('.png', '.jpg', '.jpeg', '.tif', '.tiff')):
                    img_path = os.path.join(non_viable_dir, img_file)
                    img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
                    if img is not None:
                        img = cv2.resize(img, (self.img_size, self.img_size))
                        images.append(img)
                        labels.append(0)  # non-viable
        
        if len(images) == 0:
            raise ValueError("No images found in training directories")
        
        # Convert to numpy arrays
        X = np.array(images)
        y = np.array(labels)
        
        # Normalize pixel values to [0, 1]
        X = X.astype('float32') / 255.0
        
        # Add channel dimension for grayscale
        X = np.expand_dims(X, axis=-1)
        
        print(f"Loaded {len(X)} images: {np.sum(y==1)} viable, {np.sum(y==0)} non-viable")
        
        return X, y
    
    def create_augmented_generators(self, X_train, y_train, X_val, y_val, batch_size=8):
        """Create data generators with augmentation"""
        
        # Data augmentation for training
        train_datagen = ImageDataGenerator(
            rotation_range=20,
            width_shift_range=0.1,
            height_shift_range=0.1,
            horizontal_flip=True,
            vertical_flip=True,
            zoom_range=0.1,
            fill_mode='nearest'
        )
        
        # No augmentation for validation
        val_datagen = ImageDataGenerator()
        
        train_generator = train_datagen.flow(X_train, y_train, batch_size=batch_size)
        val_generator = val_datagen.flow(X_val, y_val, batch_size=batch_size)
        
        return train_generator, val_generator
    
    def build_model(self):
        """Build CNN architecture"""
        print("Building model...")
        
        model = models.Sequential([
            # First conv block
            layers.Conv2D(32, (3, 3), activation='relu', input_shape=(self.img_size, self.img_size, 1)),
            layers.BatchNormalization(),
            layers.MaxPooling2D((2, 2)),
            layers.Dropout(0.25),
            
            # Second conv block
            layers.Conv2D(64, (3, 3), activation='relu'),
            layers.BatchNormalization(),
            layers.MaxPooling2D((2, 2)),
            layers.Dropout(0.25),
            
            # Third conv block
            layers.Conv2D(128, (3, 3), activation='relu'),
            layers.BatchNormalization(),
            layers.MaxPooling2D((2, 2)),
            layers.Dropout(0.25),
            
            # Fourth conv block
            layers.Conv2D(256, (3, 3), activation='relu'),
            layers.BatchNormalization(),
            layers.MaxPooling2D((2, 2)),
            layers.Dropout(0.25),
            
            # Dense layers
            layers.Flatten(),
            layers.Dense(512, activation='relu'),
            layers.BatchNormalization(),
            layers.Dropout(0.5),
            layers.Dense(256, activation='relu'),
            layers.BatchNormalization(),
            layers.Dropout(0.5),
            layers.Dense(1, activation='sigmoid')  # Binary classification
        ])
        
        model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=0.0001),
            loss='binary_crossentropy',
            metrics=['accuracy', keras.metrics.Precision(), keras.metrics.Recall()]
        )
        
        self.model = model
        return model
    
    def train(self, epochs=100, batch_size=8, validation_split=0.2):
        """Train the model"""
        
        # Load data
        X, y = self.load_and_preprocess_data()
        
        # Split data
        X_train, X_val, y_train, y_val = train_test_split(
            X, y, test_size=validation_split, random_state=42, stratify=y
        )
        
        print(f"Training set: {len(X_train)} images")
        print(f"Validation set: {len(X_val)} images")
        
        # Create data generators
        train_gen, val_gen = self.create_augmented_generators(
            X_train, y_train, X_val, y_val, batch_size
        )
        
        # Build model if not exists
        if self.model is None:
            self.build_model()
        
        # Print model summary
        self.model.summary()
        
        # Callbacks
        callbacks = [
            keras.callbacks.EarlyStopping(
                monitor='val_loss',
                patience=15,
                restore_best_weights=True
            ),
            keras.callbacks.ReduceLROnPlateau(
                monitor='val_loss',
                factor=0.5,
                patience=5,
                min_lr=1e-7
            ),
            keras.callbacks.ModelCheckpoint(
                'ev_viability_best_model.h5',
                monitor='val_accuracy',
                save_best_only=True
            )
        ]
        
        # Train
        print("Starting training...")
        self.history = self.model.fit(
            train_gen,
            steps_per_epoch=len(X_train) // batch_size,
            epochs=epochs,
            validation_data=val_gen,
            validation_steps=len(X_val) // batch_size,
            callbacks=callbacks,
            verbose=1
        )
        
        # Evaluate on validation set
        print("\nEvaluating on validation set...")
        val_loss, val_acc, val_precision, val_recall = self.model.evaluate(X_val, y_val)
        print(f"Validation Accuracy: {val_acc:.4f}")
        print(f"Validation Precision: {val_precision:.4f}")
        print(f"Validation Recall: {val_recall:.4f}")
        
        # Predictions
        y_pred_prob = self.model.predict(X_val)
        y_pred = (y_pred_prob > 0.5).astype(int).flatten()
        
        # Classification report
        print("\nClassification Report:")
        print(classification_report(y_val, y_pred, target_names=self.class_names))
        
        # Confusion matrix
        print("\nConfusion Matrix:")
        print(confusion_matrix(y_val, y_pred))
        
        return self.history
    
    def plot_training_history(self, save_path='training_history.png'):
        """Plot training metrics"""
        if self.history is None:
            print("No training history available")
            return
        
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        
        # Accuracy
        axes[0, 0].plot(self.history.history['accuracy'], label='Train')
        axes[0, 0].plot(self.history.history['val_accuracy'], label='Validation')
        axes[0, 0].set_title('Model Accuracy')
        axes[0, 0].set_ylabel('Accuracy')
        axes[0, 0].set_xlabel('Epoch')
        axes[0, 0].legend()
        axes[0, 0].grid(True)
        
        # Loss
        axes[0, 1].plot(self.history.history['loss'], label='Train')
        axes[0, 1].plot(self.history.history['val_loss'], label='Validation')
        axes[0, 1].set_title('Model Loss')
        axes[0, 1].set_ylabel('Loss')
        axes[0, 1].set_xlabel('Epoch')
        axes[0, 1].legend()
        axes[0, 1].grid(True)
        
        # Precision
        axes[1, 0].plot(self.history.history['precision'], label='Train')
        axes[1, 0].plot(self.history.history['val_precision'], label='Validation')
        axes[1, 0].set_title('Model Precision')
        axes[1, 0].set_ylabel('Precision')
        axes[1, 0].set_xlabel('Epoch')
        axes[1, 0].legend()
        axes[1, 0].grid(True)
        
        # Recall
        axes[1, 1].plot(self.history.history['recall'], label='Train')
        axes[1, 1].plot(self.history.history['val_recall'], label='Validation')
        axes[1, 1].set_title('Model Recall')
        axes[1, 1].set_ylabel('Recall')
        axes[1, 1].set_xlabel('Epoch')
        axes[1, 1].legend()
        axes[1, 1].grid(True)
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Training history plot saved to {save_path}")
    
    def save_model(self, model_path='ev_viability_model.h5', metadata_path='model_metadata.json'):
        """Save trained model and metadata"""
        if self.model is None:
            print("No model to save")
            return
        
        self.model.save(model_path)
        print(f"Model saved to {model_path}")
        
        # Save metadata
        metadata = {
            'img_size': self.img_size,
            'class_names': self.class_names,
            'timestamp': datetime.now().isoformat(),
            'architecture': 'CNN',
            'input_shape': [self.img_size, self.img_size, 1]
        }
        
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        print(f"Metadata saved to {metadata_path}")


def main():
    """Main training pipeline"""
    print("=" * 60)
    print("EV Viability Classification - Training Pipeline")
    print("=" * 60)
    
    # Initialize trainer
    trainer = EVViabilityTrainer(
        data_dir="training_data",
        img_size=128
    )
    
    # Train model
    history = trainer.train(
        epochs=100,
        batch_size=8,
        validation_split=0.2
    )
    
    # Plot results
    trainer.plot_training_history('training_history.png')
    
    # Save model
    trainer.save_model('ev_viability_model.h5', 'model_metadata.json')
    
    print("\n" + "=" * 60)
    print("Training Complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()

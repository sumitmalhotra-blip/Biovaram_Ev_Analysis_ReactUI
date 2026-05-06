#!/usr/bin/env python3
"""
EV Viability Classifier - Improved Training Script
Uses MobileNetV2 Transfer Learning for small datasets (~24 images)
Classifies EVs as viable or non-viable from TEM images

Improvements over original:
- MobileNetV2 pretrained on ImageNet (much better with small datasets)
- Two-phase training: feature extraction → fine-tuning
- Stronger data augmentation to combat small dataset size
- RGB conversion (MobileNetV2 expects 3 channels)
- Same output format: ev_viability_model.h5 + model_metadata.json
"""
import os
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"  # disable GPU, use CPU only

import os
import numpy as np
import cv2
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers, models
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.preprocessing.image import ImageDataGenerator
import json
import matplotlib.pyplot as plt
from datetime import datetime


class EVViabilityTrainer:
    """Train EV viability classifier using MobileNetV2 transfer learning"""

    def __init__(self, data_dir="training_data", img_size=128):
        self.data_dir = data_dir
        self.img_size = img_size
        self.model = None
        self.history_phase1 = None
        self.history_phase2 = None
        self.class_names = ["non_viable", "viable"]

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def load_and_preprocess_data(self):
        """Load images from viable/ and non_viable/ subdirectories"""
        print("Loading training data...")

        images, labels = [], []

        # viable → label 1
        viable_dir = os.path.join(self.data_dir, "viable")
        if os.path.exists(viable_dir):
            for fname in os.listdir(viable_dir):
                if fname.lower().endswith(('.png', '.jpg', '.jpeg', '.tif', '.tiff')):
                    img = self._load_image(os.path.join(viable_dir, fname))
                    if img is not None:
                        images.append(img)
                        labels.append(1)

        # non_viable → label 0
        non_viable_dir = os.path.join(self.data_dir, "non_viable")
        # also accept "nonviable" without underscore
        if not os.path.exists(non_viable_dir):
            non_viable_dir = os.path.join(self.data_dir, "nonviable")

        if os.path.exists(non_viable_dir):
            for fname in os.listdir(non_viable_dir):
                if fname.lower().endswith(('.png', '.jpg', '.jpeg', '.tif', '.tiff')):
                    img = self._load_image(os.path.join(non_viable_dir, fname))
                    if img is not None:
                        images.append(img)
                        labels.append(0)

        if len(images) == 0:
            raise ValueError(
                f"No images found in '{self.data_dir}/viable' or "
                f"'{self.data_dir}/non_viable'. "
                "Check your folder names and image extensions."
            )

        X = np.array(images, dtype='float32') / 255.0   # normalise to [0, 1]
        y = np.array(labels)

        print(f"Loaded {len(X)} images — "
              f"{np.sum(y == 1)} viable, {np.sum(y == 0)} non-viable")
        return X, y

    def _load_image(self, path):
        """Read image and convert grayscale TEM images to RGB for MobileNetV2"""
        img = cv2.imread(path)
        if img is None:
            print(f"  Warning: could not read {path}, skipping.")
            return None
        img = cv2.resize(img, (self.img_size, self.img_size))
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)   # MobileNetV2 expects RGB
        return img

    # ------------------------------------------------------------------
    # Data augmentation
    # ------------------------------------------------------------------

    def create_augmented_generators(self, X_train, y_train, X_val, y_val,
                                     batch_size=4):
        """
        Strong augmentation for training — essential for ~20-image datasets.
        Validation generator applies NO augmentation.
        """
        train_datagen = ImageDataGenerator(
            rotation_range=40,
            width_shift_range=0.15,
            height_shift_range=0.15,
            horizontal_flip=True,
            vertical_flip=True,
            zoom_range=0.2,
            shear_range=0.1,
            brightness_range=[0.8, 1.2],
            fill_mode='reflect'        # reflect is better than nearest for TEM
        )

        val_datagen = ImageDataGenerator()   # no augmentation on val

        train_gen = train_datagen.flow(X_train, y_train, batch_size=batch_size)
        val_gen   = val_datagen.flow(X_val,   y_val,   batch_size=batch_size)

        return train_gen, val_gen

    # ------------------------------------------------------------------
    # Model
    # ------------------------------------------------------------------

    def build_model(self):
        """
        MobileNetV2 transfer learning model.

        Phase 1 — feature extraction:
            MobileNetV2 base is FROZEN; only the new head is trained.
        Phase 2 — fine-tuning:
            Top layers of MobileNetV2 are UNFROZEN and trained with a
            very small learning rate.
        """
        print("Building MobileNetV2 transfer learning model...")

        # Load MobileNetV2 without the top classification layer
        base_model = MobileNetV2(
            input_shape=(self.img_size, self.img_size, 3),
            include_top=False,
            weights='imagenet'
        )
        base_model.trainable = False   # freeze for Phase 1

        # Custom classification head
        inputs  = keras.Input(shape=(self.img_size, self.img_size, 3))
        x       = base_model(inputs, training=False)
        x       = layers.GlobalAveragePooling2D()(x)
        x       = layers.Dense(128, activation='relu')(x)
        x       = layers.BatchNormalization()(x)
        x       = layers.Dropout(0.4)(x)
        x       = layers.Dense(64, activation='relu')(x)
        x       = layers.Dropout(0.3)(x)
        outputs = layers.Dense(1, activation='sigmoid')(x)

        model = keras.Model(inputs, outputs)

        model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=1e-3),
            loss='binary_crossentropy',
            metrics=[
                'accuracy',
                keras.metrics.Precision(name='precision'),
                keras.metrics.Recall(name='recall')
            ]
        )

        self.model     = model
        self.base_model = base_model
        return model

    # ------------------------------------------------------------------
    # Training (two phases)
    # ------------------------------------------------------------------

    def train(self, epochs_phase1=30, epochs_phase2=50,
              batch_size=4, validation_split=0.2):
        """
        Two-phase training:
          Phase 1 — train only the new head (base frozen)      ~30 epochs
          Phase 2 — fine-tune top layers of MobileNetV2        ~50 epochs
        """

        # ---- load & split ------------------------------------------------
        X, y = self.load_and_preprocess_data()

        # With very small datasets keep at least 1 sample per class in val
        test_size = max(validation_split, 2 / len(X))
        X_train, X_val, y_train, y_val = train_test_split(
            X, y,
            test_size=test_size,
            random_state=42,
            stratify=y
        )
        print(f"Train: {len(X_train)} | Val: {len(X_val)}")

        train_gen, val_gen = self.create_augmented_generators(
            X_train, y_train, X_val, y_val, batch_size
        )

        if self.model is None:
            self.build_model()

        self.model.summary()

        # ---- Phase 1: feature extraction ---------------------------------
        print("\n" + "=" * 50)
        print("PHASE 1 — Feature Extraction (base frozen)")
        print("=" * 50)

        callbacks_p1 = self._get_callbacks(
            checkpoint_path='ev_viability_best_model.h5',
            patience_es=10,
            patience_lr=4
        )

        self.history_phase1 = self.model.fit(
            train_gen,
            steps_per_epoch=max(1, len(X_train) // batch_size),
            epochs=epochs_phase1,
            validation_data=val_gen,
            validation_steps=max(1, len(X_val) // batch_size),
            callbacks=callbacks_p1,
            verbose=1
        )

        # ---- Phase 2: fine-tuning ----------------------------------------
        print("\n" + "=" * 50)
        print("PHASE 2 — Fine-Tuning (top MobileNetV2 layers unfrozen)")
        print("=" * 50)

        # Unfreeze the top 30 layers of MobileNetV2
        self.base_model.trainable = True
        fine_tune_at = len(self.base_model.layers) - 30
        for layer in self.base_model.layers[:fine_tune_at]:
            layer.trainable = False

        # Recompile with a much smaller LR to avoid destroying learned weights
        self.model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=1e-5),
            loss='binary_crossentropy',
            metrics=[
                'accuracy',
                keras.metrics.Precision(name='precision'),
                keras.metrics.Recall(name='recall')
            ]
        )

        callbacks_p2 = self._get_callbacks(
            checkpoint_path='ev_viability_best_model.h5',
            patience_es=15,
            patience_lr=5
        )

        self.history_phase2 = self.model.fit(
            train_gen,
            steps_per_epoch=max(1, len(X_train) // batch_size),
            epochs=epochs_phase2,
            validation_data=val_gen,
            validation_steps=max(1, len(X_val) // batch_size),
            callbacks=callbacks_p2,
            verbose=1
        )

        # ---- Final evaluation --------------------------------------------
        print("\nFinal evaluation on validation set...")
        results = self.model.evaluate(X_val, y_val, verbose=0)
        print(f"  Loss:      {results[0]:.4f}")
        print(f"  Accuracy:  {results[1]:.4f}")
        print(f"  Precision: {results[2]:.4f}")
        print(f"  Recall:    {results[3]:.4f}")

        y_pred = (self.model.predict(X_val) > 0.5).astype(int).flatten()
        print("\nClassification Report:")
        print(classification_report(y_val, y_pred,
                                    target_names=self.class_names))
        print("Confusion Matrix:")
        print(confusion_matrix(y_val, y_pred))

        return self.history_phase1, self.history_phase2

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_callbacks(self, checkpoint_path, patience_es, patience_lr):
        return [
            keras.callbacks.EarlyStopping(
                monitor='val_loss',
                patience=patience_es,
                restore_best_weights=True,
                verbose=1
            ),
            keras.callbacks.ReduceLROnPlateau(
                monitor='val_loss',
                factor=0.5,
                patience=patience_lr,
                min_lr=1e-8,
                verbose=1
            ),
            keras.callbacks.ModelCheckpoint(
                checkpoint_path,
                monitor='val_accuracy',
                save_best_only=True,
                verbose=1
            )
        ]

    # ------------------------------------------------------------------
    # Plotting
    # ------------------------------------------------------------------

    def plot_training_history(self, save_path='training_history.png'):
        """Plot both training phases side by side"""
        if self.history_phase1 is None:
            print("No training history available yet.")
            return

        def _get_metric(history, key):
            """Return metric list; try alternate key names gracefully."""
            for k in [key, key.split('_')[-1]]:
                if k in history.history:
                    return history.history[k]
            return []

        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle('EV Viability Classifier — Training History', fontsize=14)

        metrics = [
            ('accuracy',  'val_accuracy',  'Accuracy'),
            ('loss',      'val_loss',       'Loss'),
            ('precision', 'val_precision',  'Precision'),
            ('recall',    'val_recall',     'Recall'),
        ]

        for ax, (train_key, val_key, title) in zip(axes.flatten(), metrics):
            for phase_label, hist in [('P1 Train', self.history_phase1),
                                       ('P2 Train', self.history_phase2)]:
                train_vals = _get_metric(hist, train_key)
                val_vals   = _get_metric(hist, val_key)
                if train_vals:
                    ax.plot(train_vals, label=phase_label)
                if val_vals:
                    ax.plot(val_vals,   label=phase_label.replace('Train', 'Val'),
                            linestyle='--')
            ax.set_title(title)
            ax.set_xlabel('Epoch')
            ax.legend()
            ax.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Training history saved → {save_path}")

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------

    def save_model(self, model_path='ev_viability_model.h5',
                   metadata_path='model_metadata.json'):
        """Save model + metadata (same format as original script)"""
        if self.model is None:
            print("No model to save.")
            return

        self.model.save(model_path)
        print(f"Model saved → {model_path}")

        metadata = {
            'img_size':     self.img_size,
            'class_names':  self.class_names,
            'timestamp':    datetime.now().isoformat(),
            'architecture': 'MobileNetV2_TransferLearning',
            'input_shape':  [self.img_size, self.img_size, 3],
            'notes':        'Phase1=feature_extraction, Phase2=fine_tuning'
        }
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        print(f"Metadata saved → {metadata_path}")


# ----------------------------------------------------------------------
# Entry point
# ----------------------------------------------------------------------

def main():
    print("=" * 60)
    print("EV Viability Classifier — MobileNetV2 Transfer Learning")
    print("=" * 60)

    trainer = EVViabilityTrainer(
        data_dir="training_data",   # expects training_data/viable & training_data/non_viable
        img_size=128
    )

    trainer.train(
        epochs_phase1=30,    # feature extraction
        epochs_phase2=50,    # fine-tuning
        batch_size=4,        # small batch for small dataset
        validation_split=0.2
    )

    trainer.plot_training_history('training_history.png')
    trainer.save_model('ev_viability_model.h5', 'model_metadata.json')

    print("\n" + "=" * 60)
    print("Training Complete!")
    print("Outputs: ev_viability_model.h5 | model_metadata.json | training_history.png")
    print("=" * 60)


if __name__ == "__main__":
    main()
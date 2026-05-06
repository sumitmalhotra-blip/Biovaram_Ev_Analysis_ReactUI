#!/usr/bin/env python3
"""
CNN Retraining Script — EV Viability Model
===========================================
Trains a MobileNetV2-based binary classifier on TEM EV images.

Usage:
    python train_cnn.py

Folder structure expected:
    trainning_data/viable/       ← intact EV images
    trainning_data/non_viable/   ← non-intact EV images

Output:
    ev_viability_best_model.h5   ← best model saved automatically
"""

import os
import cv2
import numpy as np

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
import tensorflow as tf
from tensorflow import keras
from sklearn.model_selection import train_test_split

# --- Config ---
IMG_SIZE    = 128
EPOCHS      = 20
BATCH_SIZE  = 8
VIABLE_DIR  = "trainning_data/viable"
NV_DIR      = "trainning_data/non_viable"
OUTPUT_MODEL = "ev_viability_best_model.h5"


def load_images(folder, label):
    images, labels = [], []
    for f in sorted(os.listdir(folder)):
        if f.endswith(".png") and "annotated" not in f and "detection" not in f:
            img = cv2.imread(os.path.join(folder, f))
            if img is not None:
                img = cv2.resize(img, (IMG_SIZE, IMG_SIZE))
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                images.append(img)
                labels.append(label)
    return images, labels


def build_model():
    base = keras.applications.MobileNetV2(
        input_shape=(IMG_SIZE, IMG_SIZE, 3),
        include_top=False,
        weights="imagenet"
    )
    base.trainable = False
    model = keras.Sequential([
        base,
        keras.layers.GlobalAveragePooling2D(),
        keras.layers.Dropout(0.3),
        keras.layers.Dense(64, activation="relu"),
        keras.layers.Dense(1, activation="sigmoid"),
    ])
    model.compile(
        optimizer="adam",
        loss="binary_crossentropy",
        metrics=["accuracy"]
    )
    return model


def main():
    print("Loading images...")
    v_imgs, v_lbls = load_images(VIABLE_DIR, 1)
    n_imgs, n_lbls = load_images(NV_DIR, 0)
    print(f"Viable: {len(v_imgs)}, Non-viable: {len(n_imgs)}, Total: {len(v_imgs)+len(n_imgs)}")

    X = np.array(v_imgs + n_imgs, dtype="float32") / 255.0
    y = np.array(v_lbls + n_lbls, dtype="float32")

    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"Train: {len(X_train)}, Val: {len(X_val)}")

    model = build_model()

    callbacks = [
        keras.callbacks.ModelCheckpoint(
            OUTPUT_MODEL,
            save_best_only=True,
            monitor="val_accuracy",
            verbose=1
        ),
        keras.callbacks.EarlyStopping(
            monitor="val_loss",
            patience=5,
            restore_best_weights=True,
            verbose=1
        )
    ]

    history = model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=EPOCHS,
        batch_size=BATCH_SIZE,
        callbacks=callbacks
    )

    best_val_acc = max(history.history["val_accuracy"])
    print(f"\nTraining complete!")
    print(f"Best val_accuracy: {best_val_acc:.4f} ({best_val_acc*100:.1f}%)")
    print(f"Model saved to: {OUTPUT_MODEL}")


if __name__ == "__main__":
    main()
    
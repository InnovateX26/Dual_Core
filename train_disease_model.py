"""
AgriSense AI - MobileNetV2 Disease Model Training (Lightweight)

Usage:
  python train_disease_model.py                           # Auto-download, use ~7.6k images
  python train_disease_model.py --data_dir <path>         # Use local dataset
  python train_disease_model.py --max_images 5000         # Limit total images

Dataset: PlantVillage (54,306 images, 38 classes, 14 crop species)
"""

import os
import sys
import json
import shutil
import random
import argparse
import numpy as np
import zipfile
import urllib.request


def download_progress(block_num, block_size, total_size):
    downloaded = block_num * block_size
    if total_size > 0:
        percent = min(100, downloaded * 100 / total_size)
        mb = downloaded / (1024 * 1024)
        mb_total = total_size / (1024 * 1024)
        sys.stdout.write(f"\r   📥 {mb:.1f}/{mb_total:.1f} MB ({percent:.1f}%)")
        sys.stdout.flush()


def download_plantvillage(output_dir):
    """Download PlantVillage dataset from GitHub."""
    print("=" * 60)
    print("📥 Downloading PlantVillage Dataset...")
    print("=" * 60)

    os.makedirs(output_dir, exist_ok=True)
    zip_path = os.path.join(output_dir, "plantvillage.zip")
    url = "https://github.com/spMohanty/PlantVillage-Dataset/archive/refs/heads/master.zip"

    try:
        print(f"\n   Source: GitHub (spMohanty/PlantVillage-Dataset)")
        urllib.request.urlretrieve(url, zip_path, download_progress)
        print(f"\n   ✅ Download complete!")

        print("   📦 Extracting dataset...")
        with zipfile.ZipFile(zip_path, 'r') as z:
            z.extractall(output_dir)
        os.remove(zip_path)

        # Find the color images directory
        for root, dirs, _ in os.walk(output_dir):
            if 'color' in dirs:
                color_dir = os.path.join(root, 'color')
                class_dirs = [d for d in os.listdir(color_dir)
                              if os.path.isdir(os.path.join(color_dir, d))]
                if len(class_dirs) >= 10:
                    print(f"   ✅ Found {len(class_dirs)} classes in color/")
                    return color_dir

    except Exception as e:
        print(f"\n   ❌ Download failed: {e}")
        if os.path.exists(zip_path):
            os.remove(zip_path)

    print("\n⚠️  Auto-download failed. Please download manually:")
    print("  Kaggle: https://www.kaggle.com/datasets/abdallahalidev/plantvillage-dataset")
    print("  GitHub: git clone https://github.com/spMohanty/PlantVillage-Dataset")
    print("  Then run: python train_disease_model.py --data_dir <path_to_color_folder>")
    sys.exit(1)


def subsample_dataset(source_dir, dest_dir, max_per_class=200):
    """Copy a random subset of images from each class to a new directory."""
    print(f"\n📋 Creating lightweight subset (~{max_per_class} images/class)...")

    if os.path.exists(dest_dir):
        shutil.rmtree(dest_dir)
    os.makedirs(dest_dir)

    class_dirs = sorted([d for d in os.listdir(source_dir)
                         if os.path.isdir(os.path.join(source_dir, d))])

    total = 0
    for cls in class_dirs:
        src_cls = os.path.join(source_dir, cls)
        dst_cls = os.path.join(dest_dir, cls)
        os.makedirs(dst_cls, exist_ok=True)

        imgs = [f for f in os.listdir(src_cls)
                if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.bmp'))]

        # Random subsample
        if len(imgs) > max_per_class:
            random.seed(42)
            imgs = random.sample(imgs, max_per_class)

        for img in imgs:
            shutil.copy2(os.path.join(src_cls, img), os.path.join(dst_cls, img))

        total += len(imgs)
        print(f"   {cls}: {len(imgs)} images")

    print(f"\n   ✅ Subset: {total} images across {len(class_dirs)} classes → {dest_dir}")
    return dest_dir


def train_model(data_dir, epochs=10, batch_size=32, img_size=224):
    """Train MobileNetV2 on plant disease dataset."""

    import tensorflow as tf
    from tensorflow.keras.applications import MobileNetV2
    from tensorflow.keras.layers import Dense, GlobalAveragePooling2D, Dropout
    from tensorflow.keras.models import Model
    from tensorflow.keras.optimizers import Adam
    from tensorflow.keras.preprocessing.image import ImageDataGenerator
    from tensorflow.keras.callbacks import (
        EarlyStopping, ReduceLROnPlateau, ModelCheckpoint
    )

    print("\n" + "=" * 60)
    print("🌱 AgriSense AI - MobileNetV2 Disease Model Training")
    print("=" * 60)

    subdirs = [d for d in os.listdir(data_dir)
               if os.path.isdir(os.path.join(data_dir, d))]
    print(f"\n📂 Dataset: {data_dir}")
    print(f"   Classes: {len(subdirs)}")

    # Data generators
    train_datagen = ImageDataGenerator(
        rescale=1./255,
        rotation_range=25,
        width_shift_range=0.15,
        height_shift_range=0.15,
        shear_range=0.15,
        zoom_range=0.15,
        horizontal_flip=True,
        fill_mode='nearest',
        validation_split=0.2
    )

    print(f"   Image size: {img_size}x{img_size}")

    train_generator = train_datagen.flow_from_directory(
        data_dir,
        target_size=(img_size, img_size),
        batch_size=batch_size,
        class_mode='categorical',
        subset='training',
        shuffle=True
    )

    val_generator = train_datagen.flow_from_directory(
        data_dir,
        target_size=(img_size, img_size),
        batch_size=batch_size,
        class_mode='categorical',
        subset='validation',
        shuffle=False
    )

    num_classes = len(train_generator.class_indices)
    class_names = list(train_generator.class_indices.keys())

    print(f"\n✅ Training: {train_generator.samples} | Validation: {val_generator.samples}")
    print(f"✅ Classes: {num_classes}")

    # Build model
    print("\n🏗️ Building MobileNetV2...")
    base_model = MobileNetV2(
        weights='imagenet', include_top=False,
        input_shape=(img_size, img_size, 3)
    )
    base_model.trainable = False

    x = base_model.output
    x = GlobalAveragePooling2D()(x)
    x = Dense(256, activation='relu')(x)
    x = Dropout(0.5)(x)
    x = Dense(128, activation='relu')(x)
    x = Dropout(0.3)(x)
    predictions = Dense(num_classes, activation='softmax')(x)

    model = Model(inputs=base_model.input, outputs=predictions)
    model.compile(
        optimizer=Adam(learning_rate=0.001),
        loss='categorical_crossentropy',
        metrics=['accuracy']
    )

    print(f"   Parameters: {model.count_params():,}")

    # Output paths
    model_dir = os.path.join(os.path.dirname(__file__), 'models')
    os.makedirs(model_dir, exist_ok=True)
    model_path = os.path.join(model_dir, 'disease_model.h5')

    callbacks = [
        EarlyStopping(monitor='val_accuracy', patience=4,
                      restore_best_weights=True, verbose=1),
        ReduceLROnPlateau(monitor='val_loss', factor=0.5,
                          patience=2, min_lr=1e-6, verbose=1),
        ModelCheckpoint(model_path, monitor='val_accuracy',
                        save_best_only=True, verbose=1)
    ]

    # PHASE 1: Train head
    print(f"\n{'='*60}")
    print(f"🚀 PHASE 1: Training classification head ({epochs} epochs)")
    print(f"{'='*60}")

    model.fit(
        train_generator, epochs=epochs,
        validation_data=val_generator,
        callbacks=callbacks, verbose=1
    )

    # PHASE 2: Fine-tune
    print(f"\n{'='*60}")
    print(f"🔧 PHASE 2: Fine-tuning top layers (5 epochs)")
    print(f"{'='*60}")

    base_model.trainable = True
    for layer in base_model.layers[:-20]:
        layer.trainable = False

    model.compile(
        optimizer=Adam(learning_rate=0.0001),
        loss='categorical_crossentropy',
        metrics=['accuracy']
    )

    model.fit(
        train_generator, epochs=5,
        validation_data=val_generator,
        callbacks=callbacks, verbose=1
    )

    # Save
    model.save(model_path)
    print(f"\n💾 Model saved: {model_path}")

    class_names_path = os.path.join(model_dir, 'disease_classes.json')
    with open(class_names_path, 'w') as f:
        json.dump(class_names, f, indent=2)
    print(f"💾 Classes saved: {class_names_path}")

    # Evaluate
    val_loss, val_acc = model.evaluate(val_generator, verbose=0)
    print(f"\n📊 Final Accuracy: {val_acc*100:.2f}% | Loss: {val_loss:.4f}")
    print(f"\n✅ Done! Start service with: python disease_detector.py")

    return model


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Train disease detection model')
    parser.add_argument('--data_dir', type=str, default=None,
                        help='Path to dataset with class subdirectories')
    parser.add_argument('--max_images', type=int, default=7600,
                        help='Max total images to use (default: 7600 = ~200/class)')
    parser.add_argument('--epochs', type=int, default=10,
                        help='Training epochs (default: 10)')
    parser.add_argument('--batch_size', type=int, default=32,
                        help='Batch size (default: 32)')
    parser.add_argument('--img_size', type=int, default=224,
                        help='Image size (default: 224)')

    args = parser.parse_args()

    # Locate dataset
    script_dir = os.path.dirname(__file__)
    full_dataset_dir = os.path.join(script_dir, 'dataset', 'PlantVillage')
    subset_dir = os.path.join(script_dir, 'dataset', 'PlantVillage_subset')

    data_dir = args.data_dir

    if data_dir is None:
        # Check for existing subset first
        if os.path.exists(subset_dir) and len(os.listdir(subset_dir)) >= 10:
            print(f"✅ Found existing subset: {subset_dir}")
            data_dir = subset_dir
        else:
            # Check for full dataset
            if not os.path.exists(full_dataset_dir) or len(os.listdir(full_dataset_dir)) < 10:
                # Need to find extracted color dir
                found = False
                for root, dirs, _ in os.walk(os.path.join(script_dir, 'dataset')):
                    if 'color' in dirs:
                        candidate = os.path.join(root, 'color')
                        if len(os.listdir(candidate)) >= 10:
                            full_dataset_dir = candidate
                            found = True
                            break
                if not found:
                    full_dataset_dir = download_plantvillage(
                        os.path.join(script_dir, 'dataset', 'PlantVillage')
                    )

            # Subsample
            max_per_class = max(50, args.max_images // 38)
            data_dir = subsample_dataset(full_dataset_dir, subset_dir, max_per_class)
    elif not os.path.exists(data_dir):
        print(f"❌ Not found: {data_dir}")
        sys.exit(1)

    train_model(data_dir, args.epochs, args.batch_size, args.img_size)

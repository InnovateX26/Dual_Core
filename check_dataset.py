from datasets import load_dataset
import json

print("Loading color config...")
try:
    ds = load_dataset("mohanty/PlantVillage", "color", trust_remote_code=True)
    print(f"Keys: {list(ds.keys())}")
    for split_name in ds:
        print(f"{split_name}: {len(ds[split_name])} rows")
    features = ds["train"].features
    print(f"Feature names: {list(features.keys())}")
    if 'label' in features:
        ft = features['label']
        if hasattr(ft, 'names'):
            names = ft.names
            print(f"Classes ({len(names)}):")
            for i, n in enumerate(names):
                print(f"  {i}: {n}")
            # Save to file
            with open("python/models/_hf_classes.json", "w") as f:
                json.dump(names, f, indent=2)
            print("Saved class names to python/models/_hf_classes.json")
except Exception as e:
    print(f"Color config failed: {e}")
    print("\nTrying default config and checking text features...")
    ds = load_dataset("mohanty/PlantVillage", trust_remote_code=True)
    print(f"Keys: {list(ds.keys())}")
    row = ds["train"][0]
    print(f"First row: {row}")

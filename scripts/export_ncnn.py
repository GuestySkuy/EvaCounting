import sys
import os
import argparse
from pathlib import Path
from ultralytics import YOLO

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

def main():
    parser = argparse.ArgumentParser(description="Export YOLO model to NCNN format for Raspberry Pi")
    parser.add_argument("--model", type=str, default="yolo11n.pt", 
                        help="Path to PyTorch model file (default: yolo11n.pt)")
    parser.add_argument("--imgsz", type=int, default=320, 
                        help="Image size for inference (default: 320)")
    args = parser.parse_args()

    models_dir = Path(__file__).resolve().parent.parent / "models"
    models_dir.mkdir(exist_ok=True)
    
    model_path = args.model
    # If file name only, prepend models directory path
    if not os.path.exists(model_path):
        model_path = str(models_dir / args.model)
        
    print(f"Loading PyTorch model from: {model_path}")
    if not os.path.exists(model_path):
        print(f"Model file not found at {model_path}. It will be downloaded automatically by Ultralytics.")

    try:
        model = YOLO(model_path)
        print(f"Exporting model to NCNN format with imgsz={args.imgsz}...")
        
        # Export the model
        exported_path = model.export(format="ncnn", imgsz=args.imgsz, half=True)
        print(f"\nModel exported successfully to NCNN format!")
        print(f"Exported Model Path: {exported_path}")
        print("Copy this directory to your Raspberry Pi models/ folder for deployment.")
        
    except Exception as e:
        print(f"Error during export: {e}")

if __name__ == "__main__":
    main()

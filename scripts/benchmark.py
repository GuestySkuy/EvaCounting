import sys
import os
import time
import numpy as np
from pathlib import Path
from ultralytics import YOLO

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

def run_benchmark(model_path, imgsz, num_frames=50):
    print(f"\nBenchmarking Model: {model_path} | Img Size: {imgsz}")
    if not os.path.exists(model_path):
        print(f"Error: Model not found at {model_path}")
        return None
        
    try:
        model = YOLO(model_path)
    except Exception as e:
        print(f"Failed to load model: {e}")
        return None

    # Create a dummy frame (white image)
    dummy_frame = np.ones((480, 640, 3), dtype=np.uint8) * 255
    
    # Warmup
    print("Warming up model...")
    for _ in range(5):
        model.predict(dummy_frame, imgsz=imgsz, verbose=False)
        
    print(f"Running {num_frames} benchmark runs...")
    latencies = []
    
    for i in range(num_frames):
        t0 = time.time()
        model.predict(dummy_frame, imgsz=imgsz, verbose=False)
        t1 = time.time()
        latencies.append((t1 - t0) * 1000) # milliseconds
        
    avg_latency = np.mean(latencies)
    std_latency = np.std(latencies)
    fps = 1000.0 / avg_latency
    
    print(f"  Avg Latency: {avg_latency:.2f} ms")
    print(f"  Std Dev: {std_latency:.2f} ms")
    print(f"  FPS: {fps:.2f}")
    
    return {
        "avg_latency": avg_latency,
        "fps": fps
    }

def main():
    models_dir = Path(__file__).resolve().parent.parent / "models"
    
    pt_model = str(models_dir / "yolo11n.pt")
    ncnn_model = str(models_dir / "yolo11n_ncnn_model")
    
    print("=== People Counting System - Inference Benchmark ===")
    print(f"Benchmarking on {num_frames := 50} dummy frames.")
    
    results = {}
    
    # Benchmark PyTorch Model (320 and 640)
    if os.path.exists(pt_model):
        results["PT-320"] = run_benchmark(pt_model, 320, num_frames)
        results["PT-640"] = run_benchmark(pt_model, 640, num_frames)
    else:
        print(f"\nPyTorch model not found at {pt_model}. Skip PyTorch benchmarks.")
        
    # Benchmark NCNN Model (320 and 640)
    if os.path.exists(ncnn_model):
        results["NCNN-320"] = run_benchmark(ncnn_model, 320, num_frames)
        results["NCNN-640"] = run_benchmark(ncnn_model, 640, num_frames)
    else:
        print(f"\nNCNN model not found at {ncnn_model}.")
        print("Note: To benchmark NCNN, run 'python scripts/export_ncnn.py' first.")

    # Print summary table
    print("\n" + "="*50)
    print(f"{'Configuration':<20} | {'Avg Latency (ms)':<18} | {'Estimated FPS':<12}")
    print("-"*50)
    for cfg, res in results.items():
        if res:
            print(f"{cfg:<20} | {res['avg_latency']:<18.2f} | {res['fps']:<12.2f}")
    print("="*50)

if __name__ == "__main__":
    main()

"""Export ONNX model weights to NumPy .npz format for offline pure-numpy inference."""
import onnx
from onnx import numpy_helper
import numpy as np
import os

def main():
    # Find model.onnx
    model_paths = ['model.onnx', '../model.onnx', 'mobile_app/model.onnx']
    model_path = None
    for p in model_paths:
        if os.path.exists(p):
            model_path = p
            break
            
    if not model_path:
        raise FileNotFoundError("Could not find model.onnx in typical locations.")
        
    print(f"Loading ONNX model from {model_path}...")
    model = onnx.load(model_path)
    
    weights = {}
    print("Extracting weights...")
    for init in model.graph.initializer:
        arr = numpy_helper.to_array(init)
        weights[init.name] = arr
        print(f"  Extracted: {init.name:50} | Shape: {arr.shape}")
        
    # Save weights to model_weights.npz in the same directory as this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, 'model_weights.npz')
    
    print(f"Saving weights to {output_path}...")
    np.savez_compressed(output_path, **weights)
    print("Export complete!")

if __name__ == '__main__':
    main()

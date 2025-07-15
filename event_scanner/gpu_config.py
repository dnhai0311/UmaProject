"""
GPU Configuration for RTX 3050 Laptop
Optimized settings for Uma Event Scanner OCR
"""

import torch
import os

class GPUConfig:
    """GPU configuration optimized for RTX 3050 laptop"""
    
    @staticmethod
    def optimize_for_rtx3050():
        """Apply optimizations for RTX 3050"""
        try:
            if torch.cuda.is_available():
                # Set memory fraction to avoid OOM (RTX 3050 has 4GB VRAM)
                torch.cuda.set_per_process_memory_fraction(0.7)
                
                # Enable memory efficient attention if available
                if hasattr(torch, 'backends') and hasattr(torch.backends, 'cuda'):
                    torch.backends.cuda.matmul.allow_tf32 = True
                    torch.backends.cudnn.allow_tf32 = True
                
                # Set optimal CUDA device
                torch.cuda.set_device(0)
                
                # Clear cache
                torch.cuda.empty_cache()
                
                return True
        except Exception as e:
            print(f"GPU optimization failed: {e}")
            return False
    
    @staticmethod
    def get_optimal_batch_size():
        """Get optimal batch size for RTX 3050"""
        return 1  # RTX 3050 works best with batch size 1 for OCR
    
    @staticmethod
    def get_memory_info():
        """Get GPU memory information"""
        try:
            if torch.cuda.is_available():
                device = torch.cuda.current_device()
                total_memory = torch.cuda.get_device_properties(device).total_memory / 1024**3
                allocated_memory = torch.cuda.memory_allocated(device) / 1024**3
                cached_memory = torch.cuda.memory_reserved(device) / 1024**3
                
                return {
                    'total_gb': total_memory,
                    'allocated_gb': allocated_memory,
                    'cached_gb': cached_memory,
                    'free_gb': total_memory - allocated_memory
                }
        except:
            return None
    
    @staticmethod
    def clear_memory():
        """Clear GPU memory"""
        try:
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except:
            pass

# EasyOCR specific optimizations
EASYOCR_CONFIG = {
    'gpu': True,
    'verbose': False,
    'model_storage_directory': './models',
    'download_enabled': True,
    'quantize': True  # Use quantization for better performance
    # Removed 'batch_size', 'recognition_network', 'detection_network' as they're not valid Reader parameters
}

# Image processing optimizations
IMAGE_PROCESSING_CONFIG = {
    'max_image_size': (800, 600),  # Limit image size for faster processing
    'preprocessing_methods': ['adaptive_clahe', 'otsu_enhanced'],  # Only use 2 best methods
    'confidence_threshold': 0.4,  # Higher threshold for speed
    'max_results': 3,  # Limit results for speed
    'enable_multi_scale': True,  # Enable multi-scale for accuracy
    'scales': [0.8, 1.0, 1.2]  # Optimized scales for RTX 3050
} 
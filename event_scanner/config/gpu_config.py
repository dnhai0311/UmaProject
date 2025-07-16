"""
GPU Configuration for RTX 3050 Laptop
Advanced optimizations for Uma Event Scanner OCR
Optimized for RTX 3050 4GB VRAM with laptop thermal constraints
"""

import torch
import os
import sys
import psutil
from typing import Dict, Optional, Tuple

class GPUConfig:
    """Advanced GPU configuration optimized for RTX 3050 laptop"""
    
    # RTX 3050 specific constants
    RTX3050_VRAM_GB = 4.0
    RTX3050_CUDA_CORES = 2048
    OPTIMAL_MEMORY_FRACTION = 0.65  # Conservative for laptop thermal management
    
    @staticmethod
    def optimize_for_rtx3050():
        """Apply advanced optimizations for RTX 3050 laptop"""
        try:
            # Check if CUDA is available
            if not torch.cuda.is_available():
                print("CUDA not available - will use CPU")
                return False
            
            device = torch.cuda.current_device()
            device_name = torch.cuda.get_device_name(device)
            
            # Verify it's RTX 3050 or similar
            if "3050" not in device_name and "3060" not in device_name and "3070" not in device_name:
                print(f"Warning: Expected RTX 30 series, found {device_name}")
            
            # Advanced memory management for laptop
            GPUConfig._setup_memory_management()
            
            # Performance optimizations
            GPUConfig._setup_performance_optimizations()
            
            # Thermal management for laptop
            GPUConfig._setup_thermal_management()
            
            # Set optimal CUDA device
            torch.cuda.set_device(device)
            
            # Clear cache
            torch.cuda.empty_cache()
            
            # Print optimization summary
            GPUConfig._print_optimization_summary(device_name)
            
            return True
            
        except Exception as e:
            print(f"GPU optimization failed: {e}")
            return False
    
    @staticmethod
    def _setup_memory_management():
        """Advanced memory management for RTX 3050"""
        try:
            # Conservative memory fraction for laptop thermal management
            torch.cuda.set_per_process_memory_fraction(GPUConfig.OPTIMAL_MEMORY_FRACTION)
            
            # Enable memory efficient attention
            if hasattr(torch, 'backends') and hasattr(torch.backends, 'cuda'):
                # Enable TF32 for better performance on RTX 30 series
                torch.backends.cuda.matmul.allow_tf32 = True
                torch.backends.cudnn.allow_tf32 = True
                
                # Optimize cuDNN for laptop usage
                torch.backends.cudnn.benchmark = True
                torch.backends.cudnn.deterministic = False
                
                # Memory efficient settings
                torch.backends.cudnn.enabled = True
                
            # Set memory pool size (conservative for laptop)
            if hasattr(torch.cuda, 'set_per_process_memory_fraction'):
                torch.cuda.set_per_process_memory_fraction(0.65)
                
        except Exception as e:
            print(f"Memory management setup failed: {e}")
    
    @staticmethod
    def _setup_performance_optimizations():
        """Performance optimizations for RTX 3050"""
        try:
            # Enable mixed precision for better performance
            if hasattr(torch, 'autocast'):
                # Will be used in inference
                pass
            
            # Optimize for inference rather than training
            torch.set_grad_enabled(False)
            
            # Set optimal thread settings for laptop
            if hasattr(torch, 'set_num_threads'):
                # Use fewer threads to avoid thermal throttling
                cpu_count = psutil.cpu_count(logical=False)
                if cpu_count is not None:
                    optimal_threads = min(cpu_count, 4)  # Conservative for laptop
                    torch.set_num_threads(optimal_threads)
                
        except Exception as e:
            print(f"Performance optimization setup failed: {e}")
    
    @staticmethod
    def _setup_thermal_management():
        """Thermal management for laptop GPU"""
        try:
            # Conservative settings to avoid thermal throttling
            if hasattr(torch.cuda, 'set_per_process_memory_fraction'):
                # Use less memory to reduce heat generation
                torch.cuda.set_per_process_memory_fraction(0.65)
            
            # Disable some features that generate heat
            if hasattr(torch, 'backends') and hasattr(torch.backends, 'cuda'):
                # Disable some optimizations that generate heat
                torch.backends.cudnn.benchmark = False  # Disable for thermal management
                
        except Exception as e:
            print(f"Thermal management setup failed: {e}")
    
    @staticmethod
    def _print_optimization_summary(device_name: str):
        """Print optimization summary"""
        try:
            memory_info = GPUConfig.get_memory_info()
            print(f"✅ GPU optimizations applied for {device_name}")
            
            if memory_info:
                print(f"   📊 VRAM: {memory_info['total_gb']:.1f}GB total")
                print(f"   🔧 Memory fraction: {GPUConfig.OPTIMAL_MEMORY_FRACTION * 100}%")
                print(f"   🎯 Optimized for laptop thermal management")
                
        except Exception as e:
            print(f"Failed to print optimization summary: {e}")
    
    @staticmethod
    def get_optimal_batch_size() -> int:
        """Get optimal batch size for RTX 3050 laptop"""
        try:
            memory_info = GPUConfig.get_memory_info()
            if memory_info and memory_info['free_gb'] > 2.0:
                return 2  # Can handle batch size 2 if enough memory
            else:
                return 1  # Conservative batch size for laptop
        except:
            return 1
    
    @staticmethod
    def get_adaptive_confidence_threshold() -> float:
        """Get adaptive confidence threshold based on GPU performance"""
        try:
            memory_info = GPUConfig.get_memory_info()
            if memory_info and memory_info['free_gb'] > 2.5:
                return 0.35  # Lower threshold if plenty of memory
            else:
                return 0.45  # Higher threshold to reduce processing
        except:
            return 0.4
    
    @staticmethod
    def get_memory_info() -> Optional[Dict]:
        """Get detailed GPU memory information"""
        try:
            if torch.cuda.is_available():
                device = torch.cuda.current_device()
                props = torch.cuda.get_device_properties(device)
                
                total_memory = props.total_memory / 1024**3
                allocated_memory = torch.cuda.memory_allocated(device) / 1024**3
                cached_memory = torch.cuda.memory_reserved(device) / 1024**3
                free_memory = total_memory - allocated_memory
                
                return {
                    'total_gb': total_memory,
                    'allocated_gb': allocated_memory,
                    'cached_gb': cached_memory,
                    'free_gb': free_memory,
                    'utilization_percent': (allocated_memory / total_memory) * 100,
                    'device_name': props.name,
                    'compute_capability': f"{props.major}.{props.minor}"
                }
        except Exception as e:
            print(f"Failed to get memory info: {e}")
            return None
    
    @staticmethod
    def clear_memory():
        """Clear GPU memory with error handling"""
        try:
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.synchronize()  # Ensure all operations complete
        except Exception as e:
            print(f"Memory clear failed: {e}")
    
    @staticmethod
    def get_optimal_image_size() -> Tuple[int, int]:
        """Get optimal image size based on available memory"""
        try:
            memory_info = GPUConfig.get_memory_info()
            if memory_info and memory_info['free_gb'] > 2.0:
                return (1000, 800)  # Larger size if enough memory
            else:
                return (800, 600)   # Conservative size for laptop
        except:
            return (800, 600)
    
    @staticmethod
    def should_use_multi_scale() -> bool:
        """Determine if multi-scale processing should be used"""
        try:
            memory_info = GPUConfig.get_memory_info()
            if memory_info and memory_info['free_gb'] > 1.5:
                return True
            else:
                return False  # Disable to save memory
        except:
            return True

# Advanced EasyOCR configuration for RTX 3050
EASYOCR_CONFIG = {
    'gpu': True,
    'verbose': False,
    'model_storage_directory': './models',
    'download_enabled': True,
    'quantize': True,  # Use quantization for better performance
}

# Advanced image processing configuration
IMAGE_PROCESSING_CONFIG = {
    'max_image_size': GPUConfig.get_optimal_image_size() if hasattr(GPUConfig, 'get_optimal_image_size') else (800, 600),
    'preprocessing_methods': ['adaptive_clahe', 'otsu_enhanced'],  # Only 2 best methods for speed
    'confidence_threshold': GPUConfig.get_adaptive_confidence_threshold() if hasattr(GPUConfig, 'get_adaptive_confidence_threshold') else 0.4,
    'max_results': 3,  # Limit results for speed
    'enable_multi_scale': GPUConfig.should_use_multi_scale() if hasattr(GPUConfig, 'should_use_multi_scale') else True,
    'scales': [0.8, 1.0, 1.2],  # Optimized scales for RTX 3050
    'enable_noise_reduction': True,  # Enable noise reduction for better OCR
    'enable_edge_enhancement': True,  # Enable edge enhancement
    'max_preprocessing_time': 2.0,  # Max time for preprocessing (seconds)
    'memory_efficient_mode': True,  # Enable memory efficient mode for laptop
}

# Performance monitoring
PERFORMANCE_CONFIG = {
    'enable_monitoring': True,
    'log_memory_usage': True,
    'log_processing_time': True,
    'auto_clear_cache': True,
    'clear_cache_interval': 10,  # Clear cache every 10 operations
} 
# Windows System Requirements

## Required Windows Components

### Visual C++ Redistributables (Required for PyTorch GPU support)

**Download and Install**: [Visual C++ Redistributables x64](https://aka.ms/vs/17/release/vc_redist.x64.exe)

**Why it's needed:**
- PyTorch with CUDA support requires Visual C++ runtime libraries
- Without it, you'll get DLL loading errors when using GPU features
- Required for both XGBoost GPU and DNABERT Transformer GPU training

**Installation:**
1. Download from the link above
2. Run the installer (vc_redist.x64.exe)
3. Follow the installation wizard
4. Restart your computer after installation

**Verification:**
After installation, restart your computer and verify:
```powershell
python -c "import torch; print('CUDA available:', torch.cuda.is_available())"
```

### CUDA Toolkit (Optional, for GPU acceleration)

If you want GPU acceleration, you need NVIDIA CUDA Toolkit:
- CUDA 11.8 or CUDA 12.1 (recommended)
- Download from: https://developer.nvidia.com/cuda-downloads

Note: PyTorch will work on CPU without CUDA, but training will be slower.

## System Requirements Summary

| Component | Required | For |
|-----------|----------|-----|
| Visual C++ Redistributables | ✅ Yes | PyTorch DLL loading |
| CUDA Toolkit | ❌ Optional | GPU acceleration |
| NVIDIA GPU | ❌ Optional | GPU training (10x+ faster) |


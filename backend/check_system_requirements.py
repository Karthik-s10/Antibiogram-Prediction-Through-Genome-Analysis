"""
System requirements checker for Windows.
Checks for Visual C++ Redistributables and provides installation instructions.
"""
import sys
import subprocess
import platform
import logging

logger = logging.getLogger(__name__)

def check_vc_redist():
    """Check if Visual C++ Redistributables are installed."""
    if platform.system() != 'Windows':
        logger.info("Not on Windows, skipping Visual C++ Redistributables check")
        return True
    
    try:
        # Try to check registry for Visual C++ Redistributables
        import winreg
        
        # Check common registry keys for VC++ Redistributables
        vc_keys = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\VisualStudio\14.0\VC\Runtimes\x64"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\VC\90\CRT"),
        ]
        
        for hkey, key_path in vc_keys:
            try:
                winreg.OpenKey(hkey, key_path)
                logger.info("Visual C++ Redistributables detected in registry")
                return True
            except FileNotFoundError:
                continue
        
        # Alternative: Try to check via DLL availability
        try:
            import ctypes
            # Try to load a common VC++ DLL
            ctypes.windll.LoadLibrary("vcruntime140.dll")
            logger.info("Visual C++ runtime DLLs detected")
            return True
        except OSError:
            pass
        
        logger.warning("Visual C++ Redistributables not detected")
        return False
        
    except ImportError:
        # winreg not available (shouldn't happen on Windows, but handle gracefully)
        logger.warning("Could not check Visual C++ Redistributables (registry access unavailable)")
        return None
    except Exception as e:
        logger.warning(f"Error checking Visual C++ Redistributables: {e}")
        return None

def check_pytorch_gpu():
    """Check if PyTorch GPU support is working."""
    try:
        import torch
        try:
            cuda_available = torch.cuda.is_available()
            if cuda_available:
                logger.info(f"✅ PyTorch GPU support: Available (CUDA {torch.version.cuda})")
                return True
            else:
                logger.info("⚠️  PyTorch GPU support: Not available (CUDA not detected)")
                return False
        except (OSError, RuntimeError) as e:
            logger.error(f"❌ PyTorch GPU support: DLL loading failed ({e})")
            logger.error("   This likely means Visual C++ Redistributables are missing!")
            return False
    except ImportError:
        logger.warning("PyTorch not installed")
        return None

def print_requirements_summary():
    """Print a summary of system requirements check."""
    print("=" * 70)
    print("  System Requirements Check")
    print("=" * 70)
    print()
    
    if platform.system() == 'Windows':
        print("Windows System Requirements:")
        print("-" * 70)
        
        vc_redist = check_vc_redist()
        if vc_redist is True:
            print("✅ Visual C++ Redistributables: Installed")
        elif vc_redist is False:
            print("❌ Visual C++ Redistributables: NOT FOUND")
            print()
            print("   REQUIRED for PyTorch GPU support!")
            print("   Download and install from:")
            print("   https://aka.ms/vs/17/release/vc_redist.x64.exe")
            print()
        else:
            print("⚠️  Visual C++ Redistributables: Could not verify")
            print("   If you get DLL errors, install from:")
            print("   https://aka.ms/vs/17/release/vc_redist.x64.exe")
            print()
        
        pytorch_gpu = check_pytorch_gpu()
        if pytorch_gpu is True:
            print("✅ PyTorch GPU Support: Working")
        elif pytorch_gpu is False:
            print("⚠️  PyTorch GPU Support: Not available (will use CPU)")
        elif pytorch_gpu is None:
            print("ℹ️  PyTorch: Not installed yet")
        print()
        
        if vc_redist is False:
            print("=" * 70)
            print("  ACTION REQUIRED")
            print("=" * 70)
            print()
            print("Please install Visual C++ Redistributables:")
            print("1. Download: https://aka.ms/vs/17/release/vc_redist.x64.exe")
            print("2. Run the installer")
            print("3. Restart your computer")
            print("4. Re-run this check: python check_system_requirements.py")
            print()
    else:
        print(f"Operating System: {platform.system()}")
        print("Visual C++ Redistributables check skipped (Windows only)")
        print()
    
    print("=" * 70)
    print()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print_requirements_summary()


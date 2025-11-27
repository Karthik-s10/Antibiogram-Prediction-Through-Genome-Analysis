"""
Automatically download and install Visual C++ Redistributables for Windows.
This is required for PyTorch GPU support.
"""
import sys
import platform
import subprocess
import urllib.request
import os
import tempfile
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

VC_REDIST_URL = "https://aka.ms/vs/17/release/vc_redist.x64.exe"

def check_vc_redist_installed():
    """Check if Visual C++ Redistributables are already installed."""
    if platform.system() != 'Windows':
        return True  # Not needed on non-Windows
    
    try:
        import winreg
        vc_keys = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\VisualStudio\14.0\VC\Runtimes\x64"),
        ]
        
        for hkey, key_path in vc_keys:
            try:
                winreg.OpenKey(hkey, key_path)
                return True
            except FileNotFoundError:
                continue
        
        # Try to load DLL directly
        try:
            import ctypes
            ctypes.windll.LoadLibrary("vcruntime140.dll")
            return True
        except OSError:
            pass
        
        return False
    except Exception as e:
        logger.warning(f"Could not check VC++ Redistributables: {e}")
        return None

def download_vc_redist():
    """Download Visual C++ Redistributables installer to venv directory."""
    print("=" * 70)
    print("  Downloading Visual C++ Redistributables")
    print("=" * 70)
    print(f"Source: {VC_REDIST_URL}")
    print()
    
    try:
        # Download to venv directory (or current directory if no venv)
        venv_base = os.environ.get('VIRTUAL_ENV', None)
        if venv_base:
            # Store in venv directory
            installer_dir = os.path.join(venv_base, 'vc_redist')
            os.makedirs(installer_dir, exist_ok=True)
            installer_path = os.path.join(installer_dir, "vc_redist.x64.exe")
        else:
            # Fallback to current directory
            installer_dir = os.path.dirname(os.path.abspath(__file__))
            installer_path = os.path.join(installer_dir, "vc_redist.x64.exe")
        
        # If already downloaded, reuse it
        if os.path.exists(installer_path):
            print(f"Using existing installer: {installer_path}")
            return installer_path
        
        print(f"Downloading to: {installer_path}")
        print("This may take a minute...")
        
        # Download with progress
        def show_progress(block_num, block_size, total_size):
            downloaded = block_num * block_size
            percent = min(100, (downloaded * 100) // total_size) if total_size > 0 else 0
            print(f"\rProgress: {percent}%", end='', flush=True)
        
        urllib.request.urlretrieve(VC_REDIST_URL, installer_path, show_progress)
        print()  # New line after progress
        print("Download complete!")
        print(f"Installer saved to: {installer_path}")
        print()
        
        return installer_path
    except Exception as e:
        print(f"\nError downloading: {e}")
        print("\nPlease download manually from:")
        print(VC_REDIST_URL)
        return None

def install_vc_redist(installer_path):
    """Launch the Visual C++ Redistributables installer."""
    print("=" * 70)
    print("  Installing Visual C++ Redistributables")
    print("=" * 70)
    print()
    print(f"Running installer: {installer_path}")
    print()
    print("NOTE: The installer may require Administrator privileges.")
    print("If prompted, click 'Yes' to allow the installation.")
    print()
    
    try:
        # Launch installer
        # Use /install /quiet for silent installation (requires admin)
        # Or just launch normally and let user interact
        subprocess.Popen([installer_path], shell=True)
        print("Installer launched successfully!")
        print()
        print("Please follow the installation wizard.")
        print("After installation completes, restart your computer for changes to take effect.")
        print()
        return True
    except Exception as e:
        print(f"Error launching installer: {e}")
        print("\nPlease run the installer manually:")
        print(f"  {installer_path}")
        return False

def main(auto_mode=False):
    """Main function to check, download, and install VC++ Redistributables.
    
    Args:
        auto_mode: If True, skip prompts and auto-install if needed
    """
    if platform.system() != 'Windows':
        return  # Skip on non-Windows
    
    # Check if already installed
    is_installed = check_vc_redist_installed()
    
    if is_installed:
        print("✅ Visual C++ Redistributables already installed")
        return  # Already installed, nothing to do
    
    # Download installer to venv
    installer_path = download_vc_redist()
    if not installer_path:
        return
    
    # Auto-install if in auto mode, otherwise prompt
    if auto_mode:
        print("Auto-installing Visual C++ Redistributables...")
        install_vc_redist(installer_path)
    else:
        print()
        response = input("Launch installer now? (y/n): ").strip().lower()
        if response in ['y', 'yes']:
            install_vc_redist(installer_path)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInstallation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)


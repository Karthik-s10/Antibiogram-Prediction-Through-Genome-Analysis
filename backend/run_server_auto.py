"""
Enhanced server startup script with automatic port detection.
Handles port conflicts by finding an available port automatically.
"""
import uvicorn
import sys
import os
import socket
from typing import Optional

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def is_port_available(port: int, host: str = "0.0.0.0") -> bool:
    """Check if a port is available for binding."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((host, port))
            return True
    except OSError:
        return False


def find_available_port(preferred_port: int = 8000, max_attempts: int = 10) -> Optional[int]:
    """
    Find an available port starting from preferred_port.
    Tries preferred_port, then 8001, 8002, ... up to max_attempts.
    """
    ports_to_try = [preferred_port] + list(range(8001, 8001 + max_attempts))
    
    for port in ports_to_try:
        if is_port_available(port):
            return port
    
    return None


def get_port_from_env() -> int:
    """Get port from environment variable or use default."""
    return int(os.getenv("BACKEND_PORT", "8000"))


if __name__ == "__main__":
    # Try to get port from environment or use default
    preferred_port = get_port_from_env()
    
    # Check if preferred port is available
    if is_port_available(preferred_port):
        selected_port = preferred_port
        print("=" * 70)
        print("  Starting Antibiotic Resistance Prediction API")
        print("=" * 70)
    else:
        print("=" * 70)
        print(f"  WARNING: Port {preferred_port} is already in use!")
        print("  Finding an available port...")
        print("=" * 70)
        
        selected_port = find_available_port(preferred_port)
        
        if selected_port is None:
            print()
            print("  ERROR: Could not find an available port!")
            print("  Please free up ports 8000-8010 or specify a custom port:")
            print("  Example: set BACKEND_PORT=9000 && python run_server_auto.py")
            print("=" * 70)
            sys.exit(1)
        
        print()
        print(f"  Found available port: {selected_port}")
        print("=" * 70)
    
    # Display server information
    print()
    print(f"  API Documentation: http://localhost:{selected_port}/docs")
    print(f"  Health Check:      http://localhost:{selected_port}/health")
    print(f"  API Base URL:      http://localhost:{selected_port}")
    print()
    
    # Important notice if port changed
    if selected_port != preferred_port:
        print("  IMPORTANT: Backend is running on a different port!")
        print(f"  Update your frontend configuration:")
        print()
        print("  Option 1: Create/Edit .env file in project root:")
        print(f"  VITE_API_URL=http://localhost:{selected_port}")
        print()
        print("  Option 2: Set environment variable:")
        print(f"  set VITE_API_URL=http://localhost:{selected_port}")
        print()
        print("  Then restart your frontend: npm run dev")
        print("=" * 70)
        print()
    
    print("  Press CTRL+C to stop the server")
    print("=" * 70)
    print()
    
    # Start the server
    try:
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=selected_port,
            reload=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n")
        print("=" * 70)
        print("  Server stopped")
        print("=" * 70)
    except Exception as e:
        print("\n")
        print("=" * 70)
        print(f"  ERROR: {e}")
        print("=" * 70)
        sys.exit(1)


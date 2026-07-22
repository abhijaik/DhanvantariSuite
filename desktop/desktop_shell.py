import os
import sys
import socket
import threading
import uvicorn
import webview

def find_free_port() -> int:
    """Finds an unused TCP port on localhost."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
    s.close()
    return port

def run_backend(port: int):
    """Runs the FastAPI backend server on the specified port."""
    # Set environment variables if needed
    os.environ["DATABASE_URL"] = "sqlite:///clinic_local.db"
    
    # Run uvicorn server
    uvicorn.run("src.main:app", host="127.0.0.1", port=port, log_level="info")

def main():
    # 1. Find a free port for the loopback REST API service
    port = find_free_port()
    
    # 2. Start the FastAPI backend in a daemon thread
    backend_thread = threading.Thread(target=run_backend, args=(port,), daemon=True)
    backend_thread.start()
    
    # Wait briefly for the backend to start up
    import time
    time.sleep(1.0)
    
    # 3. Start PyWebView desktop GUI pointing to the localhost service
    # In a fully deployed setup, pywebview can mount a local dist directory containing
    # static HTML/JS/CSS files, or fetch them from the uvicorn loopback interface.
    print(f"Launching desktop wrapper pointing to http://127.0.0.1:{port}")
    
    webview.create_window(
        title="Clinic Management System (ERP)",
        url=f"http://127.0.0.1:{port}/ui/index.html", # Assuming static files are served at /ui/
        width=1280,
        height=800,
        resizable=True
    )
    
    # Start the webview loop (blocking)
    webview.start()
    
    # Exit program cleanly when GUI is closed
    sys.exit(0)

if __name__ == "__main__":
    main()

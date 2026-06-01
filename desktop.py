import sys
import os
import time
import socket
import threading
import streamlit.web.cli as stcli
import webview

def find_free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
    s.close()
    return port

def run_streamlit_programmatic(app_path, port):
    # Configure arguments for streamlit web server
    sys.argv = [
        "streamlit",
        "run",
        app_path,
        "--server.port", str(port),
        "--server.headless", "true",
        "--browser.gatherUsageStats", "false",
        "--global.developmentMode", "false"
    ]
    stcli.main()

def main():
    # Resolve absolute path for PyInstaller package temp directory or current dir
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
        
    app_path = os.path.join(base_path, "app.py")
    port = find_free_port()
    
    # Start streamlit programmatically in a background daemon thread
    t = threading.Thread(target=run_streamlit_programmatic, args=(app_path, port))
    t.daemon = True
    t.start()
    
    # Wait for the local port to spin up
    for _ in range(15):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.5)
            s.connect(('127.0.0.1', port))
            s.close()
            break
        except Exception:
            time.sleep(0.5)
            
    # Open the native desktop window pointing to the local Streamlit port
    try:
        webview.create_window(
            "NA, Blocked Report Generator - Standalone App",
            f"http://127.0.0.1:{port}",
            width=1280,
            height=850,
            resizable=True
        )
        webview.start()
    except Exception as e:
        print(f"Error launching native desktop client: {e}", file=sys.stderr)
    finally:
        # Exit application cleanly, terminating the background daemon thread
        sys.exit(0)

if __name__ == "__main__":
    main()

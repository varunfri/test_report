import sys
import os
import time
import socket
import threading
import streamlit.web.cli as stcli
import webview

# Force Streamlit to run headlessly, bind only to loopback, and disable telemetry
os.environ["STREAMLIT_SERVER_HEADLESS"] = "true"
os.environ["STREAMLIT_SERVER_ADDRESS"] = "127.0.0.1"
os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"

# Suppress console outputs for standard streams in packaged/frozen mode
if getattr(sys, 'frozen', False):
    sys.stdout = open(os.devnull, 'w')
    sys.stderr = open(os.devnull, 'w')

def find_free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
    s.close()
    return port

def run_streamlit_programmatic(app_path, port):
    sys.argv = [
        "streamlit",
        "run",
        app_path,
        "--server.port", str(port),
        "--server.address", "127.0.0.1",
        "--server.headless", "true",
        "--browser.gatherUsageStats", "false",
        "--global.developmentMode", "false"
    ]
    stcli.main()

def main():
    # Resolve absolute path for app.py
    # If compiled/frozen via PyInstaller, app.py is copied to root of sys._MEIPASS
    # If running raw in dev, desktop.py is inside the 'desktop/' folder, so app.py is in the parent folder '..'
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
        app_path = os.path.join(base_path, "app.py")
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
        app_path = os.path.abspath(os.path.join(base_path, "..", "app.py"))
        
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

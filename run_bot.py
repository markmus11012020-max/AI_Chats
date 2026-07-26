import os
import subprocess
import sys

if __name__ == "__main__":
    port = os.getenv("STREAMLIT_PORT", "8501")
    cmd = [
        sys.executable, "-m", "streamlit", "run", "app.py",
        "--server.port", port,
        "--server.headless", "true",
        "--browser.gatherUsageStats", "false",
    ]
    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        pass
    except FileNotFoundError:
        print("Streamlit не установлен.")
        sys.exit(1)
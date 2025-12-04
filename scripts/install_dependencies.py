import subprocess
import sys

def main() -> int:
    try:
        subprocess.run(["uv", "add", "pyahocorasick"], check=True)
        return 0
    except subprocess.CalledProcessError as e:
        return e.returncode

if __name__ == "__main__":
    sys.exit(main())

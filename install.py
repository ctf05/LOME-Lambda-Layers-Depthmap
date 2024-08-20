import subprocess
import sys

def run_script(script_name):
    try:
        subprocess.check_call([sys.executable, script_name])
    except subprocess.CalledProcessError as e:
        if 'No module named' in str(e):
            module_name = str(e).split("'")[1]
            print(f"Module {module_name} not found. Attempting to install it...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", module_name])
            print(f"Module {module_name} installed successfully. Retrying script...")
            subprocess.check_call([sys.executable, script_name])
        else:
            raise

if __name__ == "__main__":
    script_to_run = "test.py"  # Replace with the script you want to run
    run_script(script_to_run)

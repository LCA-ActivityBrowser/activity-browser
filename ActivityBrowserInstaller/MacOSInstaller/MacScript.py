import subprocess

def run_install_script():
    try:
        # Execute the shell script './install_ab.sh'
        subprocess.run(['./install_ab.sh'], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
    except FileNotFoundError:
        print("Error: The script './install_ab.sh' does not exist or is not accessible.")

if __name__ == "__main__":
    run_install_script()
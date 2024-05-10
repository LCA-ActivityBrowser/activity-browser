import subprocess

def installABEnvironMent():
    """Install the 'ab' Conda environment with the 'activity-browser' package from conda-forge."""	
    try:
        # Initialize Conda in the shell session
        subprocess.run(['conda', 'shell.bash', 'hook'], check=True)

        # Check if the 'ab' environment exists
        env_list = subprocess.run(['conda', 'env', 'list'], check=True, capture_output=True, text=True)
        if "\bab\b" not in env_list.stdout:
            # Create a Conda environment named 'ab' with 'activity-browser' package from conda-forge
            subprocess.run(['conda', 'create', '-y', '-n', 'ab', '-c', 'conda-forge', 'activity-browser'], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
    except FileNotFoundError:
        print("Error: The command does not exist or is not accessible.")

if __name__ == "__main__":
    installABEnvironMent()
import subprocess

def launch_activity_browser(env_name):
    # Launch the AB
    try:
        launchABCommand = f'conda activate {env_name} && activity-browser'
        subprocess.run(launchABCommand, shell=True)
    except subprocess.CalledProcessError as e:
        print("Error launching the Activity Browser:", e)

    # deactivate the AB enviroment
    try:
        deactivateABCommand = f'conda deactivate {env_name}'
        subprocess.run(deactivateABCommand, shell=True)
    except subprocess.CalledProcessError as e:
        print("Error deactivating the Activity Browser", e)

if __name__ == "__main__":
    env_name = "ActivityBrowser"
    launch_activity_browser(env_name)

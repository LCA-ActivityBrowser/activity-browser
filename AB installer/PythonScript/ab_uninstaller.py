import subprocess

uninstall_command = f"conda remove -n ActivityBrowser --all --yes"
subprocess.run(uninstall_command, shell=True, check=True)

remove_env_command = "conda env remove -n ActivityBrowser --yes"
subprocess.run(remove_env_command, shell=True, check=True)

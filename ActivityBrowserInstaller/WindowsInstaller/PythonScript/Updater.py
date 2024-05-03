import requests

def getLatestRelease(user, repo):
    url = f"https://api.github.com/repos/{user}/{repo}/releases/latest"
    response = requests.get(url)
    data = response.json()
    return data['tag_name']

def downloadLatestRelease(user, repo):
  url = f"https://api.github.com/repos/{user}/{repo}/releases/latest"
  response = requests.get(url)
  data = response.json()

  # Check if 'assets' is in the data dictionary
  if 'assets' not in data:
    print("No 'assets' in the response data")
    return

  # Get the URL of the exe file from the release data
  assets = data['assets']
  exeUrl = None
  for asset in assets:
    if asset['name'].endswith('.exe'):
      exeUrl = asset['browser_download_url']
      break

  if exeUrl is None:
    print("No exe file found in the release")
    return

  # Download the exe file
  response = requests.get(exeUrl, stream=True)
  if response.status_code == 200:
    with open(f"{repo}.exe", 'wb') as f:
      for chunk in response.iter_content(chunk_size=1024):
        if chunk:
          f.write(chunk)
  else:
    print(f"Failed to download file: {response.status_code}")

print(getLatestRelease("ThisIsSomeone", "activity-browser"))
downloadLatestRelease("ThisIsSomeone", "activity-browser")



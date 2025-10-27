import base64
import os
import requests

def upload_to_github(file_path, github_path):
    token = os.getenv("GITHUB_TOKEN")
    repo = os.getenv("GITHUB_REPO")
    branch = os.getenv("GITHUB_BRANCH", "main")

    if not token or not repo:
        raise RuntimeError("⚠️ Variables d’environnement GitHub manquantes")

    with open(file_path, "rb") as f:
        content = f.read()

    encoded_content = base64.b64encode(content).decode("utf-8")
    url = f"https://api.github.com/repos/{repo}/contents/{github_path}"

    payload = {
        "message": f"Add {os.path.basename(file_path)}",
        "content": encoded_content,
        "branch": branch
    }

    headers = {"Authorization": f"token {token}"}
    r = requests.put(url, json=payload, headers=headers)
    if r.status_code not in (200, 201):
        raise Exception(f"Échec upload GitHub : {r.json()}")

    js = r.json()
    return js["content"]["html_url"], js["content"]["download_url"]

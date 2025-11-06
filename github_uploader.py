import base64
import os
import requests

def upload_to_github(file_path, github_path):
    """
    Upload ou met à jour un fichier sur GitHub via l'API REST.
    Gère automatiquement le cas où le fichier existe déjà (sha).
    """

    token = os.getenv("GITHUB_TOKEN")
    repo = "STS-Engineer/uploads"  # Ton dépôt GitHub
    branch = os.getenv("GITHUB_BRANCH", "main")

    if not token or not repo:
        raise RuntimeError("⚠️ Variables d’environnement GitHub manquantes (GITHUB_TOKEN ou repo)")

    # Lecture du fichier local
    with open(file_path, "rb") as f:
        content = base64.b64encode(f.read()).decode("utf-8")

    url = f"https://api.github.com/repos/{repo}/contents/{github_path}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    # Vérifie si le fichier existe déjà (pour éviter l’erreur 'sha wasn’t supplied')
    sha = None
    check = requests.get(url, headers=headers)
    if check.status_code == 200:
        sha = check.json().get("sha")

    # Corps de la requête
    payload = {
        "message": f"Upload {os.path.basename(file_path)}",
        "content": content,
        "branch": branch
    }

    # Ajoute le SHA si le fichier existe déjà
    if sha:
        payload["sha"] = sha

    # Upload / mise à jour
    response = requests.put(url, json=payload, headers=headers)

    # Vérifie le succès
    if response.status_code not in (200, 201):
        raise Exception(f"❌ Échec upload GitHub : {response.json()}")

    js = response.json()
    html_url = js["content"]["html_url"]
    raw_url = f"https://raw.githubusercontent.com/{repo}/{branch}/{github_path}"

    return html_url, raw_url

import base64
import json
import os
import urllib.error
import urllib.request


GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_OWNER = os.getenv("GITHUB_OWNER", "peach-vpn")
GITHUB_REPO = os.getenv("GITHUB_REPO", "Free-VPN-")
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main")


def api_url(path):
    return f"https://api.github.com{path}"


def request(method, path, data=None):
    if not GITHUB_TOKEN:
        raise RuntimeError("GITHUB_TOKEN не задан")

    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "PeachVPN-Bot",
    }

    body = None

    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(
        api_url(path),
        data=body,
        headers=headers,
        method=method,
    )

    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            raw = response.read().decode("utf-8")
            return response.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")

        try:
            error_json = json.loads(error_body)
            message = error_json.get("message", error_body)
        except Exception:
            message = error_body

        raise RuntimeError(
            f"GitHub API HTTP {e.code}: {message}"
        )


def github_raw_url(path):
    return (
        f"https://raw.githubusercontent.com/"
        f"{GITHUB_OWNER}/{GITHUB_REPO}/"
        f"{GITHUB_BRANCH}/{path}"
    )


def upload_subscription(filename, content):
    path = f"subscriptions/{filename}"

    encoded = base64.b64encode(
        content.encode("utf-8")
    ).decode("ascii")

    sha = None

    try:
        _, existing = request(
            "GET",
            f"/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{path}"
            f"?ref={GITHUB_BRANCH}"
        )

        sha = existing.get("sha")

    except RuntimeError as e:
        if "HTTP 404" not in str(e):
            raise

    payload = {
        "message": f"Update subscription {filename}",
        "content": encoded,
        "branch": GITHUB_BRANCH,
    }

    if sha:
        payload["sha"] = sha

    request(
        "PUT",
        f"/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{path}",
        payload
    )

    return github_raw_url(path)

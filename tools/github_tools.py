"""
GitHub REST API tools for the GitHub Agent.

All functions use the token from settings. Rate limits:
  - Authenticated: 5,000 requests/hour
  - Unauthenticated: 60 requests/hour (fallback if token missing)

Public API — no PyGithub dependency needed.
"""

import base64
import re
from typing import Optional

import requests
from loguru import logger

from config.settings import settings

_API = "https://api.github.com"


def _headers() -> dict:
    h = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if settings.github_token and not settings.github_token.startswith("your_"):
        h["Authorization"] = f"Bearer {settings.github_token}"
    return h


def _get(path: str, params: dict | None = None) -> dict | list | None:
    """GET from GitHub API. Returns parsed JSON or None on error."""
    url = f"{_API}{path}"
    try:
        r = requests.get(url, headers=_headers(), params=params, timeout=15)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        logger.warning(f"[GitHub] GET {path} failed: {exc}")
        return None


# ── URL parsing ────────────────────────────────────────────────────────────────

def parse_repo_url(text: str) -> tuple[str, str] | None:
    """
    Extract (owner, repo) from any GitHub URL or 'owner/repo' mention in text.

    Handles:
      https://github.com/owner/repo
      https://github.com/owner/repo/tree/main/subdir
      github.com/owner/repo
      owner/repo  (plain text)
    """
    patterns = [
        r"github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)",
        r"\b([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            owner, repo = match.group(1), match.group(2)
            # Strip trailing .git
            repo = repo.rstrip(".git") if repo.endswith(".git") else repo
            # Skip common false positives
            if owner.lower() in ("http", "https", "www"):
                continue
            return owner, repo
    return None


# ── Data fetchers ──────────────────────────────────────────────────────────────

def fetch_repo_info(owner: str, repo: str) -> dict:
    """Fetch core repository metadata."""
    data = _get(f"/repos/{owner}/{repo}")
    if not data:
        return {}

    languages = _get(f"/repos/{owner}/{repo}/languages") or {}
    total_bytes = sum(languages.values()) or 1
    lang_pct = {
        lang: f"{round(bytes_ / total_bytes * 100, 1)}%"
        for lang, bytes_ in sorted(languages.items(), key=lambda x: -x[1])
    }

    return {
        "full_name": data.get("full_name", ""),
        "description": data.get("description", "No description"),
        "stars": data.get("stargazers_count", 0),
        "forks": data.get("forks_count", 0),
        "open_issues": data.get("open_issues_count", 0),
        "watchers": data.get("watchers_count", 0),
        "default_branch": data.get("default_branch", "main"),
        "created_at": data.get("created_at", "")[:10],
        "updated_at": data.get("updated_at", "")[:10],
        "license": (data.get("license") or {}).get("name", "None"),
        "topics": data.get("topics", []),
        "languages": lang_pct,
        "size_kb": data.get("size", 0),
        "has_wiki": data.get("has_wiki", False),
        "has_discussions": data.get("has_discussions", False),
    }


def fetch_readme(owner: str, repo: str, max_chars: int = 3000) -> str:
    """Fetch and decode the repository README."""
    data = _get(f"/repos/{owner}/{repo}/readme")
    if not data or "content" not in data:
        return "No README found."

    try:
        content = base64.b64decode(data["content"]).decode("utf-8", errors="ignore")
        if len(content) > max_chars:
            content = content[:max_chars] + f"\n\n... (truncated — {len(content):,} total chars)"
        return content
    except Exception:
        return "README could not be decoded."


def fetch_file_tree(owner: str, repo: str, branch: str = "HEAD", max_files: int = 120) -> list[str]:
    """
    Fetch the repository file tree recursively.
    Returns a list of file paths, capped at max_files.
    """
    data = _get(f"/repos/{owner}/{repo}/git/trees/{branch}", params={"recursive": "1"})
    if not data or "tree" not in data:
        return []

    paths = [
        item["path"]
        for item in data["tree"]
        if item["type"] == "blob"
    ]

    if len(paths) > max_files:
        paths = paths[:max_files]
        paths.append(f"... ({len(data['tree'])} total files, showing first {max_files})")

    return paths


def fetch_recent_commits(owner: str, repo: str, n: int = 10) -> list[dict]:
    """Fetch the n most recent commits with author and message."""
    data = _get(f"/repos/{owner}/{repo}/commits", params={"per_page": n})
    if not data:
        return []

    commits = []
    for c in data:
        commit = c.get("commit", {})
        commits.append({
            "sha": c.get("sha", "")[:7],
            "author": commit.get("author", {}).get("name", "unknown"),
            "date": commit.get("author", {}).get("date", "")[:10],
            "message": commit.get("message", "").split("\n")[0][:100],
        })
    return commits


def fetch_file_content(owner: str, repo: str, path: str, max_chars: int = 2000) -> str:
    """Fetch the content of a specific file in the repo."""
    data = _get(f"/repos/{owner}/{repo}/contents/{path}")
    if not data or "content" not in data:
        return f"Could not read file: {path}"

    try:
        content = base64.b64decode(data["content"]).decode("utf-8", errors="ignore")
        if len(content) > max_chars:
            content = content[:max_chars] + f"\n... (truncated)"
        return content
    except Exception:
        return f"Could not decode: {path}"


def fetch_workflows(owner: str, repo: str) -> list[str]:
    """Return names of GitHub Actions workflow files."""
    data = _get(f"/repos/{owner}/{repo}/contents/.github/workflows")
    if not data or not isinstance(data, list):
        return []
    return [item["name"] for item in data if item.get("type") == "file"]


# ── Context builder ────────────────────────────────────────────────────────────

def build_repo_context(owner: str, repo: str) -> tuple[str, list[str]]:
    """
    Fetch all repo data and format it as a single context string for the LLM.
    Returns (context_string, list_of_source_urls).
    """
    logger.info(f"[GitHub] Fetching repo data | {owner}/{repo}")

    info = fetch_repo_info(owner, repo)
    if not info:
        return f"Repository '{owner}/{repo}' not found or is private.", []

    readme = fetch_readme(owner, repo)
    tree = fetch_file_tree(owner, repo)
    commits = fetch_recent_commits(owner, repo)
    workflows = fetch_workflows(owner, repo)

    # Pick 2-3 interesting files to read (config, main entry, setup)
    interesting_patterns = [
        "pyproject.toml", "setup.py", "package.json", "Cargo.toml", "go.mod",
        "docker-compose.yml", "Dockerfile", "requirements.txt",
        "main.py", "app.py", "index.js", "index.ts", "main.go",
        ".github/workflows",
    ]
    files_to_read = []
    for pattern in interesting_patterns:
        for path in tree:
            if pattern in path and path not in files_to_read:
                files_to_read.append(path)
                if len(files_to_read) >= 3:
                    break
        if len(files_to_read) >= 3:
            break

    file_contents: dict[str, str] = {}
    for path in files_to_read:
        file_contents[path] = fetch_file_content(owner, repo, path)

    # Format context
    lang_str = ", ".join(f"{k} ({v})" for k, v in info.get("languages", {}).items())
    topics_str = ", ".join(info.get("topics", [])) or "none"
    commit_lines = "\n".join(
        f"  {c['sha']} [{c['date']}] {c['author']}: {c['message']}"
        for c in commits
    )
    tree_str = "\n".join(f"  {p}" for p in tree[:80])
    workflow_str = ", ".join(workflows) if workflows else "none"

    context = f"""## Repository: {info['full_name']}

**Description:** {info['description']}
**Stars:** {info['stars']:,} | **Forks:** {info['forks']:,} | **Open Issues:** {info['open_issues']}
**Languages:** {lang_str}
**Topics:** {topics_str}
**License:** {info['license']}
**Created:** {info['created_at']} | **Last updated:** {info['updated_at']}
**Size:** {info['size_kb']:,} KB
**CI/CD Workflows:** {workflow_str}

---

## README
{readme}

---

## File Structure ({len([t for t in tree if '...' not in t])} files)
{tree_str}

---

## Recent Commits (last 10)
{commit_lines}
"""

    if file_contents:
        context += "\n---\n\n## Key File Contents\n"
        for path, content in file_contents.items():
            context += f"\n### `{path}`\n```\n{content}\n```\n"

    sources = [f"https://github.com/{owner}/{repo}"]
    logger.info(f"[GitHub] Context built | {len(context):,} chars")
    return context, sources

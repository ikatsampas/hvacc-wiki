"""
setup_wiki.py
--------------
Creates/updates your Wiki.js home page via its GraphQL API.

SETUP (one-time, in your Wiki.js admin panel):
1. Log in as admin -> Administration -> API Access
2. Toggle "Enable API" on
3. Click "New API Key"
   - Name it whatever (e.g. "setup script")
   - Expiration: pick anything (e.g. never, or 1 day if you just want it for this run)
   - Full Access: checked
   - Click Generate, COPY the key immediately (shown only once)
4. Set it as an environment variable and run this script:

   PowerShell:
     $env:WIKIJS_API_KEY="paste-your-key-here"
     python setup_wiki.py

   (Optional) if your wiki isn't at http://localhost, also set:
     $env:WIKIJS_URL="http://your-wiki-address"
"""

import os
import sys
import requests

WIKI_URL = os.environ.get("WIKIJS_URL", "http://localhost").rstrip("/")
API_KEY = os.environ.get("WIKIJS_API_KEY")

if not API_KEY:
    sys.exit("Set WIKIJS_API_KEY as an environment variable first (see instructions at top of this file).")

GRAPHQL_ENDPOINT = f"{WIKI_URL}/graphql"
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

HOME_CONTENT = """# Welcome

**Welcome** to the **VATSIM Greece wiki!** Here you will find all the documentation you'll need to fly and control in the Greek virtual skies (Athinai FIR - LGGG).

### Are you a virtual pilot?

Learn about your first steps, our airspace, VFR and airport procedures.

- [First steps](/pilots-firststeps)
- [Airspace](/airspace)
- [VFR procedures](/vfr)
- [Pilot briefings](/briefings)

### Are you a virtual ATCO?

Learn about ATC training, EuroScope, letters of agreement, standard operating procedures.

- [First steps](/firststeps)
- [EuroScope](/euroscope-installation)
- [ATC Training Manual](/atc-training-manual)
- [Letters of Agreement](/loa)
- [Standard Operating Procedures](/sops)
"""


def graphql(query: str, variables: dict = None):
    resp = requests.post(GRAPHQL_ENDPOINT, headers=HEADERS, json={"query": query, "variables": variables or {}})
    resp.raise_for_status()
    data = resp.json()
    if "errors" in data:
        print("GraphQL errors:", data["errors"])
    return data.get("data")


def find_page_by_path(path: str, locale: str = "en"):
    data = graphql("{ pages { list(orderBy: PATH) { id path locale } } }")
    for p in data["pages"]["list"]:
        if p["path"] == path and p["locale"] == locale:
            return p["id"]
    return None


CREATE_MUTATION = """
mutation Create($content: String!, $description: String!, $path: String!, $title: String!) {
  pages {
    create(
      content: $content
      description: $description
      editor: "markdown"
      isPublished: true
      isPrivate: false
      locale: "en"
      path: $path
      tags: []
      title: $title
    ) {
      responseResult { succeeded errorCode message }
      page { id path }
    }
  }
}
"""

UPDATE_MUTATION = """
mutation Update($id: Int!, $content: String!, $title: String!) {
  pages {
    update(id: $id, content: $content, title: $title, isPublished: true) {
      responseResult { succeeded errorCode message }
    }
  }
}
"""


def upsert_page(path: str, title: str, description: str, content: str):
    existing_id = find_page_by_path(path)
    if existing_id:
        print(f"Updating existing page at '{path}' (id={existing_id})...")
        result = graphql(UPDATE_MUTATION, {"id": existing_id, "content": content, "title": title})
        status = result["pages"]["update"]["responseResult"]
    else:
        print(f"Creating new page at '{path}'...")
        result = graphql(
            CREATE_MUTATION,
            {"content": content, "description": description, "path": path, "title": title},
        )
        status = result["pages"]["create"]["responseResult"]

    if status["succeeded"]:
        print(f"  -> success: {WIKI_URL}/en/{path}".replace("//", "/").replace(":/", "://"))
    else:
        print(f"  -> FAILED: {status['message']}")


def main():
    upsert_page(
        path="home",
        title="Home",
        description="VATSIM Greece wiki home page",
        content=HOME_CONTENT,
    )


if __name__ == "__main__":
    main()

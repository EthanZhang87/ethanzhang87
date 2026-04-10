import requests
import os
import re
from datetime import datetime, timezone

TOKEN = os.environ["GH_TOKEN"]
USERNAME = os.environ["GH_USERNAME"]
HEADERS = {"Authorization": f"bearer {TOKEN}"}

STATS_QUERY = """
query($login: String!) {
  user(login: $login) {
    repositories(ownerAffiliations: OWNER, isFork: false, first: 100) {
      nodes { stargazerCount }
    }
    contributionsCollection {
      totalCommitContributions
    }
    repositoriesContributedTo(first: 1, contributionTypes: [COMMIT]) {
      totalCount
    }
    pullRequests { totalCount }
  }
}
"""

LANGS_QUERY = """
query($login: String!) {
  user(login: $login) {
    repositories(ownerAffiliations: OWNER, isFork: false, first: 100) {
      nodes {
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name } }
        }
      }
    }
  }
}
"""

def run_query(query, variables):
    r = requests.post("https://api.github.com/graphql",
                      json={"query": query, "variables": variables},
                      headers=HEADERS)
    return r.json()

def build_bar(pct, width=20):
    filled = round(pct / 100 * width)
    empty = width - filled
    return "[" + "█" * filled + "░" * empty + "]"

now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")

data = run_query(STATS_QUERY, {"login": USERNAME})["data"]["user"]
stars = sum(r["stargazerCount"] for r in data["repositories"]["nodes"])
commits = data["contributionsCollection"]["totalCommitContributions"]
prs = data["pullRequests"]["totalCount"]
contribs = data["repositoriesContributedTo"]["totalCount"]

stats_block = f"Last updated: {now}\n\n"
stats_block += f"Total Stars:     {stars}\n"
stats_block += f"Total Commits:   {commits}\n"
stats_block += f"Total PRs:       {prs}\n"
stats_block += f"Contributed to:  {contribs}\n"

data2 = run_query(LANGS_QUERY, {"login": USERNAME})["data"]["user"]
lang_totals = {}
for repo in data2["repositories"]["nodes"]:
    for edge in repo["languages"]["edges"]:
        name = edge["node"]["name"]
        lang_totals[name] = lang_totals.get(name, 0) + edge["size"]

total = sum(lang_totals.values())
sorted_langs = sorted(lang_totals.items(), key=lambda x: x[1], reverse=True)[:10]

langs_block = ""
for name, size in sorted_langs:
    pct = size / total * 100
    bar = build_bar(pct)
    langs_block += f"{name:<12} {bar} {pct:.2f}%\n"

with open("README.md", "r") as f:
    content = f.read()

content = re.sub(r"(?<=<!--START_SECTION:stats-->\n).*?(?=<!--END_SECTION:stats-->)",
                 f"```\n{stats_block}```\n", content, flags=re.DOTALL)
content = re.sub(r"(?<=<!--START_SECTION:langs-->\n).*?(?=<!--END_SECTION:langs-->)",
                 f"```\n{langs_block}```\n", content, flags=re.DOTALL)

with open("README.md", "w") as f:
    f.write(content)

print("README updated.")

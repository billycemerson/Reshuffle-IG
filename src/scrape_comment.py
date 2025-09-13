import requests
import json
import re
import csv
from tqdm import tqdm
import cookie
import os

# Configurations
PARENT_QUERY_HASH = "97b41c52301f77ce508f55e66d17620e"
COMMENTS_PER_PAGE = 50

sessionid = cookie.sessionid
ds_user_id = cookie.ds_user_id
csrftoken = cookie.csrftoken
mid = cookie.mid
cookies_str = f"sessionid={sessionid}; ds_user_id={ds_user_id}; csrftoken={csrftoken}; mid={mid};"


# Helpers
def extract_shortcode(url):
    m = re.search(r"instagram\.com/(?:p|reel|tv)/([^/?]+)", url)
    return m.group(1) if m else None

def build_headers(shortcode):
    return {
        "User-Agent": "Mozilla/5.0",
        "X-Requested-With": "XMLHttpRequest",
        "X-IG-App-ID": "936619743392459",
        "Referer": f"https://www.instagram.com/p/{shortcode}/",
        "Cookie": cookies_str
    }

def graphql_request(query_hash, variables, headers):
    url = f"https://www.instagram.com/graphql/query/?query_hash={query_hash}&variables={json.dumps(variables)}"
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        return r.json()
    return None

def scrape_comments(shortcode, link, writer):
    """
    Scrape all comments (and their replies) from a post
    """
    headers = build_headers(shortcode)
    has_next_page = True
    end_cursor = None

    pbar = tqdm(desc=f"Comments {shortcode}", unit="page")

    while has_next_page:
        variables = {
            "shortcode": shortcode,
            "first": COMMENTS_PER_PAGE
        }
        if end_cursor:
            variables["after"] = end_cursor

        data = graphql_request(PARENT_QUERY_HASH, variables, headers)
        if not data:
            break

        edges = data.get("data", {}).get("shortcode_media", {}).get("edge_media_to_parent_comment", {}).get("edges", [])
        page_info = data.get("data", {}).get("shortcode_media", {}).get("edge_media_to_parent_comment", {}).get("page_info", {})

        for edge in edges:
            c = edge["node"]
            parent_id = c["id"]
            writer.writerow([
                link, c["id"], "",  # parent_id empty
                c["owner"]["username"], c["text"].replace("\n", " "),
                c["created_at"], c["edge_liked_by"]["count"], c["edge_threaded_comments"]["count"]
            ])

            # handle replies
            for reply_edge in c.get("edge_threaded_comments", {}).get("edges", []):
                r = reply_edge["node"]
                writer.writerow([
                    link, r["id"], parent_id,
                    r["owner"]["username"], r["text"].replace("\n", " "),
                    r["created_at"], r["edge_liked_by"]["count"], r.get("edge_threaded_comments", {}).get("count", 0)
                ])

        has_next_page = page_info.get("has_next_page", False)
        end_cursor = page_info.get("end_cursor", None)
        pbar.update(1)

    pbar.close()


# Main
post_links = [
    # Put your Instagram post URLs here
    "https://www.instagram.com/p/DOV0Rn2DNf-/",
    "https://www.instagram.com/p/DOV5e_PE1Ao/",
    "https://www.instagram.com/p/DOVdRH0E5hk/",
    "https://www.instagram.com/p/DOVmYdDEkge/",
    "https://www.instagram.com/p/DOVetPYEkCk/",
    "https://www.instagram.com/p/DOVkQ2Sk5FW/",
    "https://www.instagram.com/p/DOVgH1REW8G/",
    "https://www.instagram.com/p/DOVdhgZEt9g/"
]

os.makedirs("../data/", exist_ok=True)

with open("../data/comments_data.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["link", "comment_id", "parent_id", "username", "text", "created_at", "like_count", "reply_count"])

    for link in tqdm(post_links, desc="All posts"):
        shortcode = extract_shortcode(link)
        if shortcode:
            scrape_comments(shortcode, link, writer)
        else:
            print(f"Could not extract shortcode from: {link}")
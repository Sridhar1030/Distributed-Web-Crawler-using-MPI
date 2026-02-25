"""
Distributed web crawler using MPI.
Master distributes URLs; workers fetch pages, extract links, and report results.
"""
import warnings
warnings.filterwarnings("ignore", message=".*OpenSSL.*LibreSSL.*", module="urllib3")

import argparse
import json
import time
from urllib.parse import urljoin, urlparse

from mpi4py import MPI
import requests
from bs4 import BeautifulSoup

comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()

# Defaults (overridden by CLI)
DEFAULT_URL = "https://www.google.com"
DEFAULT_MAX_PAGES = 20
DEFAULT_MAX_LINKS_PER_PAGE = 10
USER_AGENT = "MPI-Crawler/1.0 (educational)"


def parse_args():
    """Parse command-line args (all ranks run this; only rank 0 uses some)."""
    p = argparse.ArgumentParser(description="Distributed web crawler using MPI")
    p.add_argument("--url", default=DEFAULT_URL, help="Seed URL(s), comma-separated")
    p.add_argument("--max-pages", type=int, default=DEFAULT_MAX_PAGES, help="Max pages to crawl")
    p.add_argument("--max-links", type=int, default=DEFAULT_MAX_LINKS_PER_PAGE, help="Max links to extract per page")
    p.add_argument("--same-domain", action="store_true", help="Only follow links within the seed domain")
    p.add_argument("--output", default="", help="Write results to this file (JSON lines)")
    p.add_argument("--delay", type=float, default=0.0, help="Delay in seconds between requests per worker")
    return p.parse_args()


def normalize_url(url):
    """Strip fragment and normalize for deduplication."""
    parsed = urlparse(url)
    # Remove fragment, normalize path (strip trailing slash for same path)
    path = parsed.path.rstrip("/") or "/"
    return f"{parsed.scheme}://{parsed.netloc}{path}"


def get_domain(url):
    """Return scheme + netloc for same-domain checks."""
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}".lower()


def fetch_page(url, timeout=5):
    """
    Fetch URL and return (success, title, list of absolute http(s) links).
    Uses a polite User-Agent.
    """
    links = []
    title = ""
    try:
        resp = requests.get(
            url,
            timeout=timeout,
            headers={"User-Agent": USER_AGENT},
            allow_redirects=True,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        title = (soup.title and soup.title.string or "").strip() or url

        for a in soup.find_all("a", href=True):
            full = urljoin(url, a["href"])
            if full.startswith("http://") or full.startswith("https://"):
                links.append(full)
    except Exception:
        pass
    return title, links


# ================= MASTER =================
if rank == 0:
    args = parse_args()
    seed_urls = [u.strip() for u in args.url.split(",") if u.strip()]
    if not seed_urls:
        seed_urls = [DEFAULT_URL]

    task_queue = []
    for u in seed_urls:
        task_queue.append(normalize_url(u))
    visited = set()
    allowed_domain = get_domain(seed_urls[0]) if args.same_domain else None
    active_workers = size - 1
    results = []  # list of {"url", "title", "link_count"}
    total_links_discovered = 0
    start_time = time.perf_counter()

    print(f"Master: {active_workers} workers, max_pages={args.max_pages}, same_domain={args.same_domain}")
    print(f"Seeds: {seed_urls}")

    while active_workers > 0:
        status = MPI.Status()
        data = comm.recv(source=MPI.ANY_SOURCE, tag=MPI.ANY_TAG, status=status)
        worker = status.Get_source()

        if data == "REQUEST":
            url = None
            while task_queue and len(visited) < args.max_pages:
                candidate = task_queue.pop(0)
                if candidate not in visited:
                    url = candidate
                    break
            if url is not None:
                visited.add(url)
                comm.send((url, args.max_links, allowed_domain), dest=worker)
            else:
                comm.send("STOP", dest=worker)
                active_workers -= 1

        else:
            # (url, title, links)
            page_url, title, links = data
            results.append({"url": page_url, "title": title[:200], "link_count": len(links)})
            total_links_discovered += len(links)
            for link in links:
                norm = normalize_url(link)
                if norm in visited:
                    continue
                if allowed_domain and get_domain(norm) != allowed_domain:
                    continue
                if norm not in visited and norm not in task_queue:
                    task_queue.append(norm)

    elapsed = time.perf_counter() - start_time
    print("Crawling finished")
    print(f"  Pages visited: {len(visited)}")
    print(f"  Total links discovered: {total_links_discovered}")
    print(f"  Time: {elapsed:.2f}s")

    if args.output:
        with open(args.output, "w") as f:
            for r in results:
                f.write(json.dumps(r) + "\n")
        print(f"  Results written to {args.output}")


# ================= WORKERS =================
else:
    args = parse_args()
    allowed_domain = None  # set by master per task

    while True:
        comm.send("REQUEST", dest=0)
        msg = comm.recv(source=0)

        if msg == "STOP":
            break

        url, max_links, allowed_domain = msg
        if args.delay > 0:
            time.sleep(args.delay)

        title, links = fetch_page(url)
        links = links[:max_links]
        print(f"Worker {rank} crawled: {url}")

        comm.send((url, title, links), dest=0)

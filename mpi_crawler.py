import warnings
warnings.filterwarnings("ignore", message=".*OpenSSL.*LibreSSL.*", module="urllib3")

from mpi4py import MPI
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()

MAX_PAGES = 20


def fetch_links(url):
    """Fetch page and extract links"""
    links = []
    try:
        response = requests.get(url, timeout=3)
        soup = BeautifulSoup(response.text, "html.parser")

        for a in soup.find_all("a", href=True):
            full_url = urljoin(url, a["href"])
            if full_url.startswith("http"):
                links.append(full_url)

    except:
        pass

    return links[:5]  # limit links to keep it light


# ================= MASTER =================
if rank == 0:
    task_queue = ["https://example.com"]
    visited = set()
    active_workers = size - 1

    print(f"Master started with {active_workers} workers")

    while active_workers > 0:

        # Receive message from any worker
        status = MPI.Status()
        data = comm.recv(source=MPI.ANY_SOURCE, tag=MPI.ANY_TAG, status=status)
        worker = status.Get_source()

        if data == "REQUEST":
            # Give task if available
            if task_queue and len(visited) < MAX_PAGES:
                url = task_queue.pop(0)
                visited.add(url)
                comm.send(url, dest=worker)
            else:
                comm.send("STOP", dest=worker)
                active_workers -= 1

        else:
            # Received new links from worker
            for link in data:
                if link not in visited:
                    task_queue.append(link)

    print("Crawling finished")
    print("Total pages visited:", len(visited))


# ================= WORKERS =================
else:
    while True:
        # Request work
        comm.send("REQUEST", dest=0)
        url = comm.recv(source=0)

        if url == "STOP":
            break

        links = fetch_links(url)
        print(f"Worker {rank} crawled: {url}")

        # Send discovered links back
        comm.send(links, dest=0)
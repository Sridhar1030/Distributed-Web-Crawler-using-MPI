# Distributed Web Crawler using MPI

A simple **distributed web crawler** that uses [MPI](https://www.mpi-forum.org/) (Message Passing Interface) to coordinate multiple processes. One process acts as a **master** that distributes URLs; the others act as **workers** that fetch pages and extract links.

## How it works

- **Master (rank 0)**  
  Holds a queue of URLs to crawl and a set of visited URLs. It receives work requests from workers, hands out one URL at a time, and collects newly discovered links. When the crawl limit is reached or the queue is empty, it tells each worker to stop.

- **Workers (rank 1, 2, …)**  
  Each worker repeatedly asks the master for a URL, fetches the page over HTTP, parses the HTML with BeautifulSoup, and extracts up to 5 outbound links. Those links are sent back to the master to be added to the queue.

The crawl starts from `https://example.com` and is limited to **20 pages** to keep runs short and predictable.

## Requirements

- Python 3
- [mpi4py](https://mpi4py.readthedocs.io/)
- [requests](https://requests.readthedocs.io/)
- [beautifulsoup4](https://www.crummy.com/software/BeautifulSoup/)

Install dependencies:

pip install mpi4py requests beautifulsoup4

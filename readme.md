<p align="center">
  <strong>Distributed Web Crawler using MPI</strong>
</p>
<p align="center">
  <em>Multi-process web crawler coordinated via Message Passing Interface</em>
</p>

---

## Table of contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Requirements](#requirements)
- [Quick start](#quick-start)
- [Usage & options](#usage--options)
- [Example output](#example-output)

---

## Overview

This project is a **distributed web crawler** that uses [MPI](https://www.mpi-forum.org/) to run one **master** process and multiple **worker** processes. The master holds a URL queue and hands out work; workers fetch pages, extract links, and send them back. New links are added to the queue and crawled until a page limit is reached or the queue is empty.

---

## Architecture

<p align="center">
  <img src="workflow.gif" alt="MPI Crawler: how master and workers talk" width="640">
</p>

```
                    ┌─────────────────────────────────────────┐
                    │              MASTER (rank 0)             │
                    │  • URL queue                             │
                    │  • Visited set (normalized URLs)         │
                    │  • Same-domain filter (optional)         │
                    │  • Writes results to file (optional)     │
                    └─────────────────┬───────────────────────┘
                                      │
         ┌────────────────────────────┼────────────────────────────┐
         │                            │                            │
         ▼                            ▼                            ▼
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│  WORKER (rank 1) │         │  WORKER (rank 2) │         │  WORKER (rank 3) │
│  GET url        │         │  GET url        │         │  GET url        │
│  Fetch page     │         │  Fetch page     │         │  Fetch page     │
│  Parse HTML     │         │  Parse HTML     │         │  Parse HTML     │
│  Extract links  │         │  Extract links  │         │  Extract links  │
│  SEND (url,     │         │  SEND (url,     │         │  SEND (url,     │
│   title, links) │         │   title, links) │         │   title, links) │
└─────────────────┘         └─────────────────┘         └─────────────────┘
```

**Flow:** Workers send `"REQUEST"` → Master replies with a URL or `"STOP"` → Worker fetches page, parses with BeautifulSoup, sends back `(url, title, links)` → Master enqueues new links and repeats.

---

## Features

| Feature | Description |
|--------|-------------|
| **Configurable seeds** | One or more start URLs (comma-separated). |
| **URL normalization** | Deduplicates by normalizing paths and stripping fragments. |
| **Same-domain mode** | Optional `--same-domain` to stay on the seed’s domain. |
| **Result export** | Save URL, title, and link count per page to a JSON-lines file. |
| **Politeness** | Custom User-Agent and optional delay between requests. |
| **Stats** | Prints pages visited, total links found, and runtime. |

---

## Requirements

- **Python 3**
- **MPI** implementation ([Open MPI](https://www.open-mpi.org/) or [MPICH](https://www.mpich.org/))
- Python packages: `mpi4py`, `requests`, `beautifulsoup4`

Install dependencies:

```bash
pip install mpi4py requests beautifulsoup4
```

---

## Quick start

```bash
# 4 processes (1 master + 3 workers), default seed and 20 pages
mpirun -np 4 python mpi_crawler.py
```

---

## Usage & options

**Basic run with custom seed and page limit:**

```bash
mpirun -np 4 python mpi_crawler.py --url https://example.com --max-pages 30 --max-links 15
```

**Same-domain crawl and save results:**

```bash
mpirun -np 4 python mpi_crawler.py --url https://example.com --same-domain --output results.jsonl
```

**Multiple seeds with delay and output:**

```bash
mpirun -np 4 python mpi_crawler.py \
  --url "https://example.com,https://example.org" \
  --max-pages 50 \
  --delay 0.5 \
  --output crawl.jsonl
```

### Option reference

| Option | Default | Description |
|--------|--------|-------------|
| `--url` | `https://example.com` | Seed URL(s), comma-separated |
| `--max-pages` | `20` | Maximum pages to crawl |
| `--max-links` | `10` | Max links to extract per page |
| `--same-domain` | off | Only follow links on the seed domain |
| `--output` | — | Output file path (JSON lines) |
| `--delay` | `0` | Delay in seconds between requests per worker |

Process **rank 0** is always the master; all others are workers.

---

## Example output

```
Master: 3 workers, max_pages=20, same_domain=False
Seeds: ['https://example.com']
Worker 1 crawled: https://example.com
Worker 2 crawled: https://www.iana.org/domains/example
...
Crawling finished
  Pages visited: 20
  Total links discovered: 87
  Time: 12.34s
  Results written to results.jsonl
```

Output file format (one JSON object per line):

```json
{"url": "https://example.com", "title": "Example Domain", "link_count": 5}
{"url": "https://www.iana.org/domains/example", "title": "IANA — Example domains", "link_count": 10}
```

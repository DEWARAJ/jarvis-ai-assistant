"""Firecrawl integration for JARVIS — advanced web scraping and crawling.

Firecrawl converts any website into clean LLM-ready markdown or structured data.
Handles JavaScript-heavy sites, waits for dynamic content, follows pagination.

Features:
- Scrape: single URL → clean markdown
- Crawl: entire domain → all pages as markdown
- Map: discover all URLs on a site
"""
from __future__ import annotations
import os
from tools.base_tool import BaseTool

try:
    import requests
    _REQUESTS_OK = True
except ImportError:
    _REQUESTS_OK = False


class FirecrawlTool(BaseTool):
    name = "firecrawl"
    scope = "advanced web scraping, crawling, and data extraction via Firecrawl API"

    def __init__(self, context=None, logger=None):
        super().__init__(context, logger)
        self.api_key = os.getenv("FIRECRAWL_API_KEY", "")
        self.base_url = "https://api.firecrawl.dev/v1"
    
    def _check_ready(self) -> tuple[bool, str]:
        """Check if Firecrawl is ready to use."""
        if not _REQUESTS_OK:
            return False, "requests library not installed. Run: pip install requests"
        if not self.api_key:
            return False, "FIRECRAWL_API_KEY not set in .env"
        return True, ""
    
    def _call_api(self, endpoint: str, method: str = "POST", data: dict = None) -> dict:
        """Make API call to Firecrawl."""
        ready, msg = self._check_ready()
        if not ready:
            return {"success": False, "error": msg}
        
        url = f"{self.base_url}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            if method == "POST":
                resp = requests.post(url, json=data or {}, headers=headers, timeout=60)
            elif method == "GET":
                resp = requests.get(url, headers=headers, timeout=60)
            else:
                return {"success": False, "error": f"Unknown method: {method}"}
            
            resp.raise_for_status()
            return {"success": True, "data": resp.json()}
        
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": str(e)}
    
    def scrape(self, url: str, formats: list[str] = None, wait_for: str = None, 
               remove_tags: list[str] = None, only_main_content: bool = True) -> dict:
        """Scrape a single URL and return clean markdown.
        
        Args:
            url: The webpage URL to scrape
            formats: Output formats, e.g. ["markdown", "html", "screenshot"]
            wait_for: Milliseconds to wait for page load (default: 0)
            remove_tags: HTML tags to remove, e.g. ["nav", "footer", "aside"]
            only_main_content: Extract only main content, skip nav/footer
        
        Returns:
            {
                "started": bool,
                "spoken": str,  # For JARVIS voice output
                "text": str,    # Clean markdown content
                "url": str,
                "title": str,
                "debug": str
            }
        """
        url = (url or "").strip()
        if not url:
            return {
                "started": False,
                "spoken": "Which URL should I scrape, sir?",
                "text": "",
                "debug": "no_url"
            }
        
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        
        payload = {
            "url": url,
            "formats": formats or ["markdown"],
            "onlyMainContent": only_main_content
        }
        
        if wait_for:
            payload["waitFor"] = int(wait_for)
        if remove_tags:
            payload["removeTags"] = remove_tags
        
        result = self._call_api("/scrape", "POST", payload)
        
        if not result["success"]:
            return {
                "started": False,
                "spoken": f"Couldn't scrape that page, sir — {result['error']}",
                "text": "",
                "debug": result["error"]
            }
        
        data = result["data"].get("data", {})
        markdown = data.get("markdown", "")
        title = data.get("metadata", {}).get("title", url)
        
        return {
            "started": True,
            "spoken": f"Scraped '{title}', sir. {len(markdown)} characters of content.",
            "text": markdown,
            "url": url,
            "title": title,
            "debug": "firecrawl_scrape_ok"
        }
    
    def crawl(self, url: str, max_depth: int = 2, limit: int = 10, 
              exclude_paths: list[str] = None, include_paths: list[str] = None) -> dict:
        """Crawl an entire website and extract all pages as markdown.
        
        Args:
            url: Starting URL / domain to crawl
            max_depth: How deep to follow links (default: 2)
            limit: Max pages to crawl (default: 10)
            exclude_paths: URL patterns to skip, e.g. ["/login", "/admin"]
            include_paths: Only crawl URLs matching these patterns
        
        Returns:
            {
                "started": bool,
                "spoken": str,
                "pages": list[dict],  # Each: {url, title, markdown}
                "total": int,
                "debug": str
            }
        """
        url = (url or "").strip()
        if not url:
            return {
                "started": False,
                "spoken": "Which website should I crawl, sir?",
                "pages": [],
                "total": 0,
                "debug": "no_url"
            }
        
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        
        payload = {
            "url": url,
            "limit": limit,
            "maxDepth": max_depth,
            "scrapeOptions": {
                "formats": ["markdown"],
                "onlyMainContent": True
            }
        }
        
        if exclude_paths:
            payload["excludePaths"] = exclude_paths
        if include_paths:
            payload["includePaths"] = include_paths
        
        result = self._call_api("/crawl", "POST", payload)
        
        if not result["success"]:
            return {
                "started": False,
                "spoken": f"Couldn't start the crawl, sir — {result['error']}",
                "pages": [],
                "total": 0,
                "debug": result["error"]
            }
        
        # Firecrawl returns a job ID for async crawling
        job_id = result["data"].get("id")
        if not job_id:
            return {
                "started": False,
                "spoken": "Firecrawl didn't return a job ID, sir.",
                "pages": [],
                "total": 0,
                "debug": "no_job_id"
            }
        
        # Poll for results (simplified - production would use webhooks)
        import time
        max_wait = 180  # 3 minutes max
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            status_result = self._call_api(f"/crawl/{job_id}", "GET")
            
            if not status_result["success"]:
                break
            
            status_data = status_result["data"]
            state = status_data.get("status")
            
            if state == "completed":
                pages = []
                for item in status_data.get("data", []):
                    pages.append({
                        "url": item.get("metadata", {}).get("sourceURL", ""),
                        "title": item.get("metadata", {}).get("title", ""),
                        "markdown": item.get("markdown", "")
                    })
                
                return {
                    "started": True,
                    "spoken": f"Crawled {len(pages)} pages from {url}, sir.",
                    "pages": pages,
                    "total": len(pages),
                    "debug": "firecrawl_crawl_ok"
                }
            
            elif state == "failed":
                error = status_data.get("error", "Unknown error")
                return {
                    "started": False,
                    "spoken": f"Crawl failed, sir — {error}",
                    "pages": [],
                    "total": 0,
                    "debug": error
                }
            
            # Still running
            time.sleep(5)
        
        return {
            "started": False,
            "spoken": f"Crawl timed out after {max_wait} seconds, sir.",
            "pages": [],
            "total": 0,
            "debug": "timeout"
        }
    
    def map_site(self, url: str, include_subdomains: bool = False) -> dict:
        """Discover all URLs on a website without scraping content.
        
        Args:
            url: Website to map
            include_subdomains: Include subdomain URLs
        
        Returns:
            {
                "started": bool,
                "spoken": str,
                "urls": list[str],
                "total": int,
                "debug": str
            }
        """
        url = (url or "").strip()
        if not url:
            return {
                "started": False,
                "spoken": "Which site should I map, sir?",
                "urls": [],
                "total": 0,
                "debug": "no_url"
            }
        
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        
        payload = {
            "url": url,
            "includeSubdomains": include_subdomains
        }
        
        result = self._call_api("/map", "POST", payload)
        
        if not result["success"]:
            return {
                "started": False,
                "spoken": f"Couldn't map that site, sir — {result['error']}",
                "urls": [],
                "total": 0,
                "debug": result["error"]
            }
        
        urls = result["data"].get("links", [])
        
        return {
            "started": True,
            "spoken": f"Found {len(urls)} URLs on {url}, sir.",
            "urls": urls,
            "total": len(urls),
            "debug": "firecrawl_map_ok"
        }

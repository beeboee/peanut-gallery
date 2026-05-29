from __future__ import annotations

import json
import random
import re
import shutil
import time
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "close",
}
IMAGE_HEADERS = {
    **HEADERS,
    "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
}
MIN_IMAGE_BYTES = 10000
FETCH_ATTEMPTS = 3
DEFAULT_SOURCE_URL = "https://www.gocomics.com/peanuts/1950/10/02"


@dataclass(frozen=True)
class GoComicsSource:
    slug: str
    start_date: date


@dataclass
class PeanutGalleryResult:
    day: date
    image_path: Path
    image_url: str
    date_text: str
    queue_size: int
    slug: str = "peanuts"


class PeanutGalleryClient:
    def __init__(
        self,
        config_dir: Path,
        cache_dir: str,
        current_image: str,
        date_file: str,
        queue_file: str,
        cache_size: int,
        start_date: date,
        source_url: str = DEFAULT_SOURCE_URL,
    ) -> None:
        self.config_dir = config_dir
        self.cache_dir = self._resolve_path(cache_dir)
        self.current_file = self._resolve_path(current_image)
        self.date_file = self._resolve_path(date_file)
        self.queue_file = self._resolve_path(queue_file)
        self.archive_state_file = self.config_dir / "peanut_gallery_archive_state.json"
        self.cache_size = cache_size
        self.start_date = start_date
        self.source = self.parse_source_url(source_url)
        self.archive_root = self.config_dir / "www" / "gocomics"

        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.current_file.parent.mkdir(parents=True, exist_ok=True)
        self.date_file.parent.mkdir(parents=True, exist_ok=True)
        self.archive_root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def parse_source_url(source_url: str | None) -> GoComicsSource:
        value = source_url or DEFAULT_SOURCE_URL
        parsed = urlparse(value)
        parts = [part for part in parsed.path.split("/") if part]

        if len(parts) < 4:
            raise ValueError("GoComics source_url must look like https://www.gocomics.com/peanuts/1950/10/02")

        slug = parts[0]
        year, month, day = parts[1:4]

        if not re.fullmatch(r"[a-z0-9-]+", slug):
            raise ValueError("GoComics comic slug contains unsupported characters")

        return GoComicsSource(slug=slug, start_date=date(int(year), int(month), int(day)))

    def _source(self, source_url: str | None = None) -> GoComicsSource:
        return self.parse_source_url(source_url) if source_url else self.source

    def _resolve_path(self, value: str) -> Path:
        path = Path(value)
        if path.is_absolute():
            return path
        return self.config_dir / path

    def _public_url_for(self, path: Path) -> str:
        try:
            rel = path.relative_to(self.config_dir / "www")
            return f"/local/{rel.as_posix()}"
        except ValueError:
            return str(path)

    def _dated_url(self, source: GoComicsSource, day: date) -> str:
        return f"https://www.gocomics.com/{source.slug}/{day:%Y/%m/%d}"

    def _archive_path_for(self, source: GoComicsSource, day: date) -> Path:
        return self.archive_root / source.slug / f"{day:%Y}" / f"{day:%m}" / f"{source.slug}_{day:%Y-%m-%d}.jpg"

    def _legacy_cache_path_for(self, day: date) -> Path:
        return self.cache_dir / f"peanuts_{day:%Y-%m-%d}.jpg"

    def _archive_files(self, source: GoComicsSource) -> list[Path]:
        root = self.archive_root / source.slug
        if not root.exists():
            return []
        return sorted(
            path
            for path in root.glob(f"*/*/{source.slug}_*.jpg")
            if path.exists() and path.stat().st_size > MIN_IMAGE_BYTES
        )

    def _day_from_archive_path(self, source: GoComicsSource, path: Path) -> date:
        prefix = f"{source.slug}_"
        stem = path.stem
        if not stem.startswith(prefix):
            raise ValueError(f"Unexpected archive filename {path.name}")
        return date.fromisoformat(stem.removeprefix(prefix))

    def _load_archive_state(self) -> dict:
        if not self.archive_state_file.exists():
            return {}

        try:
            data = json.loads(self.archive_state_file.read_text())
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _save_archive_state(self, state: dict) -> None:
        self.archive_state_file.write_text(json.dumps(state, indent=2, sort_keys=True))

    def archive_step(self, source_url: str | None = None, max_items: int = 5) -> dict:
        source = self._source(source_url)
        state = self._load_archive_state()
        source_state = state.setdefault(source.slug, {})

        current = date.fromisoformat(
            source_state.get("next_date", source.start_date.isoformat())
        )
        end = date.today()

        checked = 0
        saved = 0
        skipped = 0
        failed = 0
        last_error = None

        while current <= end and checked < max_items:
            checked += 1

            try:
                path = self._archive_path_for(source, current)

                if path.exists() and path.stat().st_size > MIN_IMAGE_BYTES:
                    skipped += 1
                else:
                    self._fetch_day(source, current)
                    saved += 1

            except Exception as err:
                failed += 1
                last_error = str(err)
                break

            current += timedelta(days=1)

        source_state["slug"] = source.slug
        source_state["next_date"] = current.isoformat()
        source_state["checked"] = int(source_state.get("checked", 0)) + checked
        source_state["saved"] = int(source_state.get("saved", 0)) + saved
        source_state["skipped"] = int(source_state.get("skipped", 0)) + skipped
        source_state["failed"] = int(source_state.get("failed", 0)) + failed
        source_state["last_error"] = last_error
        source_state["archive_count"] = len(self._archive_files(source))

        self._save_archive_state(state)

        return dict(source_state)
        
    def _get(self, url: str, headers: dict[str, str], allow_redirects: bool = True) -> requests.Response:
        last_error: Exception | None = None

        for attempt in range(FETCH_ATTEMPTS):
            try:
                response = requests.get(url, headers=headers, timeout=30, allow_redirects=allow_redirects)
                response.raise_for_status()
                return response
            except Exception as err:
                last_error = err
                if attempt < FETCH_ATTEMPTS - 1:
                    time.sleep(1 + attempt)

        if last_error is not None:
            raise last_error
        raise RuntimeError(f"Failed to fetch {url}")

    def _extract_comic_url(self, page_url: str) -> str:
        resp = self._get(page_url, HEADERS, allow_redirects=False)
        if resp.is_redirect or resp.is_permanent_redirect:
            raise RuntimeError(f"Skipping redirected comic page {page_url}")

        soup = BeautifulSoup(resp.text, "html.parser")
        candidates: list[str] = []

        for img in soup.find_all("img"):
            src = (img.get("src") or "").replace("&amp;", "&")
            srcset = (img.get("srcset") or "").replace("&amp;", "&")

            if "featureassets.gocomics.com/assets/" in src:
                candidates.append(src)

            if "featureassets.gocomics.com/assets/" in srcset:
                parts = [
                    p.strip().split(" ")[0]
                    for p in srcset.split(",")
                    if "featureassets.gocomics.com/assets/" in p
                ]
                if parts:
                    candidates.append(parts[-1])

        for url in candidates:
            if "optimizer=image" in url:
                return url

        if candidates:
            return candidates[0]

        raise RuntimeError(f"No comic asset image found on {page_url}")

    def _fetch_day(self, source: GoComicsSource, day: date) -> Path:
        path = self._archive_path_for(source, day)
        legacy_path = self._legacy_cache_path_for(day)

        if path.exists() and path.stat().st_size > MIN_IMAGE_BYTES:
            return path

        path.parent.mkdir(parents=True, exist_ok=True)

        if source.slug == "peanuts" and legacy_path.exists() and legacy_path.stat().st_size > MIN_IMAGE_BYTES:
            shutil.copyfile(legacy_path, path)
            return path

        page_url = self._dated_url(source, day)
        img_url = self._extract_comic_url(page_url)
        img_resp = self._get(img_url, IMAGE_HEADERS)

        if "image" not in img_resp.headers.get("Content-Type", ""):
            raise RuntimeError(f"Downloaded content was not an image from {img_url}")

        if len(img_resp.content) < MIN_IMAGE_BYTES:
            raise RuntimeError(f"Downloaded file too small from {img_url}")

        path.write_bytes(img_resp.content)
        return path

    def _load_queue(self) -> list[str]:
        if not self.queue_file.exists():
            return []

        try:
            data = json.loads(self.queue_file.read_text())
            if not isinstance(data, list):
                return []
            return [str(item) for item in data]
        except Exception:
            return []

    def _save_queue(self, queue: list[str]) -> None:
        self.queue_file.write_text(json.dumps(queue))

    def _pick_random_day(self, source: GoComicsSource) -> date:
        end = date.today()
        return source.start_date + timedelta(days=random.randint(0, (end - source.start_date).days))

    def _save_current_date(self, day: date) -> None:
        self.date_file.write_text(day.strftime("%b %d, %Y"))

    def _result(self, source: GoComicsSource, day: date, image_path: Path) -> PeanutGalleryResult:
        return PeanutGalleryResult(
            day=day,
            image_path=image_path,
            image_url=self._public_url_for(image_path),
            date_text=day.strftime("%b %d, %Y"),
            queue_size=len(self._archive_files(source)),
            slug=source.slug,
        )

    def refill(self) -> int:
        source = self.source
        queue = self._load_queue()
        queued = set(queue)

        attempts = 0
        while len(queue) < self.cache_size and attempts < 200:
            attempts += 1
            day = self._pick_random_day(source)
            key = day.isoformat()

            if key in queued:
                continue

            try:
                self._fetch_day(source, day)
                queue.append(key)
                queued.add(key)
            except Exception:
                continue

        self._save_queue(queue)
        return len(queue)

    def serve_day(self, day: date, source_url: str | None = None) -> PeanutGalleryResult:
        source = self._source(source_url)
        image_path = self._fetch_day(source, day)
        self._save_current_date(day)
        return self._result(source, day, image_path)

    def serve_today(self, source_url: str | None = None) -> PeanutGalleryResult:
        return self.serve_day(date.today(), source_url)

    def serve_random(self, source_url: str | None = None) -> PeanutGalleryResult:
        source = self._source(source_url)
        files = self._archive_files(source)

        if files:
            image_path = random.choice(files)
            day = self._day_from_archive_path(source, image_path)
            self._save_current_date(day)
            return self._result(source, day, image_path)

        return self.serve_today(source_url)

    def archive_day_range(self, source_url: str | None, start: date, end: date, max_items: int = 250) -> dict:
        source = self._source(source_url)
        current = max(start, source.start_date)
        downloaded = 0
        skipped = 0
        failed = 0
        last_error = None

        while current <= end and downloaded + skipped + failed < max_items:
            try:
                path = self._archive_path_for(source, current)
                if path.exists() and path.stat().st_size > MIN_IMAGE_BYTES:
                    skipped += 1
                else:
                    self._fetch_day(source, current)
                    downloaded += 1
            except Exception as err:
                failed += 1
                last_error = str(err)

            current += timedelta(days=1)
            time.sleep(2)

        return {
            "slug": source.slug,
            "next_date": current.isoformat(),
            "downloaded": downloaded,
            "skipped": skipped,
            "failed": failed,
            "last_error": last_error,
        }

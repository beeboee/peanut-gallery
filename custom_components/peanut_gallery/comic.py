from __future__ import annotations

import json
import random
import shutil
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0"}
MIN_IMAGE_BYTES = 10000


@dataclass
class PeanutGalleryResult:
    day: date
    image_path: Path
    image_url: str
    date_text: str
    queue_size: int


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
    ) -> None:
        self.config_dir = config_dir
        self.cache_dir = self._resolve_path(cache_dir)
        self.current_file = self._resolve_path(current_image)
        self.date_file = self._resolve_path(date_file)
        self.queue_file = self._resolve_path(queue_file)
        self.cache_size = cache_size
        self.start_date = start_date

        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.current_file.parent.mkdir(parents=True, exist_ok=True)
        self.date_file.parent.mkdir(parents=True, exist_ok=True)

    def _resolve_path(self, value: str) -> Path:
        path = Path(value)
        if path.is_absolute():
            return path
        return self.config_dir / path

    def _public_url_for_current(self) -> str:
        try:
            rel = self.current_file.relative_to(self.config_dir / "www")
            return f"/local/{rel.as_posix()}"
        except ValueError:
            return str(self.current_file)

    def _dated_url(self, day: date) -> str:
        return f"https://www.gocomics.com/peanuts/{day:%Y/%m/%d}"

    def _cache_path_for(self, day: date) -> Path:
        return self.cache_dir / f"peanuts_{day:%Y-%m-%d}.jpg"

    def _extract_comic_url(self, page_url: str) -> str:
        resp = requests.get(page_url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
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

    def _fetch_day(self, day: date) -> Path:
        path = self._cache_path_for(day)

        if path.exists() and path.stat().st_size > MIN_IMAGE_BYTES:
            return path

        page_url = self._dated_url(day)
        img_url = self._extract_comic_url(page_url)

        img_resp = requests.get(img_url, headers=HEADERS, timeout=30)
        img_resp.raise_for_status()

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

            cleaned: list[str] = []
            for item in data:
                try:
                    day = date.fromisoformat(str(item))
                    if self._cache_path_for(day).exists():
                        cleaned.append(day.isoformat())
                except Exception:
                    continue
            return cleaned
        except Exception:
            return []

    def _save_queue(self, queue: list[str]) -> None:
        self.queue_file.write_text(json.dumps(queue))

    def _pick_random_day(self) -> date:
        end = date.today()
        return self.start_date + timedelta(days=random.randint(0, (end - self.start_date).days))

    def _save_current_date(self, day: date) -> None:
        self.date_file.write_text(day.strftime("%b %d, %Y"))

    def _result(self, day: date) -> PeanutGalleryResult:
        return PeanutGalleryResult(
            day=day,
            image_path=self.current_file,
            image_url=self._public_url_for_current(),
            date_text=day.strftime("%b %d, %Y"),
            queue_size=len(self._load_queue()),
        )

    def refill(self) -> int:
        queue = self._load_queue()
        queued = set(queue)

        attempts = 0
        while len(queue) < self.cache_size and attempts < 200:
            attempts += 1
            day = self._pick_random_day()
            key = day.isoformat()

            if key in queued:
                continue

            try:
                self._fetch_day(day)
                queue.append(key)
                queued.add(key)
            except Exception:
                continue

        self._save_queue(queue)
        return len(queue)

    def serve_day(self, day: date) -> PeanutGalleryResult:
        src = self._fetch_day(day)
        shutil.copyfile(src, self.current_file)
        self._save_current_date(day)
        return self._result(day)

    def serve_today(self) -> PeanutGalleryResult:
        return self.serve_day(date.today())

    def serve_random(self) -> PeanutGalleryResult:
        queue = self._load_queue()

        if not queue:
            self.refill()
            queue = self._load_queue()
            if not queue:
                raise RuntimeError("Queue is empty and refill failed")

        day_str = queue.pop(0)
        self._save_queue(queue)
        day = date.fromisoformat(day_str)
        result = self.serve_day(day)
        self.refill()
        return result

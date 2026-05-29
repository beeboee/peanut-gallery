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
DAILY_MODE_MONTHLY_RANDOM_YEAR = "monthly_random_year"


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
        self.daily_state_file = self.config_dir / "peanut_gallery_daily_state.json"
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

    def _parse_date(self, value: str | None) -> date | None:
        if not value:
            return None
        return date.fromisoformat(value)

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

    def _result_from_file(self, source: GoComicsSource, path: Path) -> PeanutGalleryResult:
        day = self._day_from_archive_path(source, path)
        self._save_current_date(day)
        return self._result(source, day, path)

    def _files_for_month_day(self, source: GoComicsSource, target_day: date) -> list[Path]:
        files = []
        for path in self._archive_files(source):
            try:
                day = self._day_from_archive_path(source, path)
            except Exception:
                continue
            if day.month == target_day.month and day.day == target_day.day:
                files.append(path)
        return files

    def _is_sunday_type(self, day: date) -> bool:
        return day.weekday() == 6

    def _files_for_month_weekday_type(self, source: GoComicsSource, target_day: date) -> list[Path]:
        wanted_sunday = self._is_sunday_type(target_day)
        files = []
        for path in self._archive_files(source):
            try:
                day = self._day_from_archive_path(source, path)
            except Exception:
                continue
            if day.month == target_day.month and self._is_sunday_type(day) == wanted_sunday:
                files.append(path)
        return files

    def _files_for_weekday_type(self, source: GoComicsSource, target_day: date) -> list[Path]:
        wanted_sunday = self._is_sunday_type(target_day)
        files = []
        for path in self._archive_files(source):
            try:
                day = self._day_from_archive_path(source, path)
            except Exception:
                continue
            if self._is_sunday_type(day) == wanted_sunday:
                files.append(path)
        return files

    def _available_matching_years_for_month(
        self,
        source: GoComicsSource,
        target_day: date,
        archive_end_date: str | None = None,
    ) -> list[int]:
        end_limit = self._parse_date(archive_end_date)
        end = min(date.today(), end_limit) if end_limit else date.today()
        target_month_start_weekday = date(target_day.year, target_day.month, 1).weekday()
        years: set[int] = set()

        for path in self._archive_files(source):
            try:
                day = self._day_from_archive_path(source, path)
            except Exception:
                continue

            if day.month != target_day.month:
                continue
            if day < source.start_date or day > end:
                continue
            if date(day.year, target_day.month, 1).weekday() != target_month_start_weekday:
                continue
            years.add(day.year)

        return sorted(years)

    def _load_json_file(self, path: Path) -> dict:
        if not path.exists():
            return {}
        try:
            data = json.loads(path.read_text())
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _save_json_file(self, path: Path, state: dict) -> None:
        path.write_text(json.dumps(state, indent=2, sort_keys=True))

    def _load_archive_state(self) -> dict:
        return self._load_json_file(self.archive_state_file)

    def _save_archive_state(self, state: dict) -> None:
        self._save_json_file(self.archive_state_file, state)

    def _load_daily_state(self) -> dict:
        return self._load_json_file(self.daily_state_file)

    def _save_daily_state(self, state: dict) -> None:
        self._save_json_file(self.daily_state_file, state)

    def archive_step(
        self,
        source_url: str | None = None,
        max_items: int = 5,
        delay_seconds: float = 12.0,
        max_failures_per_date: int = 3,
        archive_end_date: str | None = None,
    ) -> dict:
        source = self._source(source_url)
        state = self._load_archive_state()
        source_state = state.setdefault(source.slug, {})

        current = date.fromisoformat(
            source_state.get("next_date", source.start_date.isoformat())
        )
        end_limit = self._parse_date(archive_end_date)
        end = min(date.today(), end_limit) if end_limit else date.today()

        failed_dates = source_state.setdefault("failed_dates", {})
        skipped_failed_dates = source_state.setdefault("skipped_failed_dates", [])

        checked = 0
        saved = 0
        skipped = 0
        failed = 0
        last_error = None

        while current <= end and checked < max_items:
            checked += 1
            current_key = current.isoformat()

            try:
                path = self._archive_path_for(source, current)

                if path.exists() and path.stat().st_size > MIN_IMAGE_BYTES:
                    skipped += 1
                else:
                    self._fetch_day(source, current)
                    saved += 1

                failed_dates.pop(current_key, None)
                current += timedelta(days=1)

            except Exception as err:
                failed += 1
                last_error = str(err)

                fail_count = int(failed_dates.get(current_key, 0)) + 1
                failed_dates[current_key] = fail_count

                if fail_count >= max_failures_per_date:
                    if current_key not in skipped_failed_dates:
                        skipped_failed_dates.append(current_key)
                    current += timedelta(days=1)

                break

            if checked < max_items and current <= end and delay_seconds > 0:
                time.sleep(delay_seconds)

        complete = current > end
        source_state["slug"] = source.slug
        source_state["next_date"] = current.isoformat()
        source_state["archive_end_date"] = end.isoformat()
        source_state["complete"] = complete
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

    def serve_today(
        self,
        source_url: str | None = None,
        archive_end_date: str | None = None,
        daily_mode: str | None = None,
        card_id: str | None = None,
    ) -> PeanutGalleryResult:
        source = self._source(source_url)

        if archive_end_date and daily_mode == DAILY_MODE_MONTHLY_RANDOM_YEAR:
            result = self._serve_monthly_random_year_today(source, archive_end_date, card_id)
            if result is not None:
                return result

        return self.serve_day(date.today(), source_url)

    def _serve_monthly_random_year_today(
        self,
        source: GoComicsSource,
        archive_end_date: str | None,
        card_id: str | None,
    ) -> PeanutGalleryResult | None:
        today = date.today()
        month_key = today.strftime("%Y-%m")
        instance_key = card_id or source.slug
        state = self._load_daily_state()
        instance_state = state.setdefault(instance_key, {})

        years = self._available_matching_years_for_month(source, today, archive_end_date)
        selected_year = instance_state.get(month_key)

        if selected_year not in years:
            selected_year = random.choice(years) if years else None
            if selected_year is not None:
                instance_state[month_key] = selected_year
                self._save_daily_state(state)

        if selected_year is not None:
            try:
                chosen_day = date(int(selected_year), today.month, today.day)
                path = self._archive_path_for(source, chosen_day)
                if path.exists() and path.stat().st_size > MIN_IMAGE_BYTES:
                    return self._result_from_file(source, path)
            except ValueError:
                pass

        for candidates in (
            self._files_for_month_weekday_type(source, today),
            self._files_for_weekday_type(source, today),
            self._archive_files(source),
        ):
            if candidates:
                return self._result_from_file(source, random.choice(candidates))

        return None

    def serve_random(
        self,
        source_url: str | None = None,
        same_date: bool = False,
        target_date: str | None = None,
    ) -> PeanutGalleryResult:
        source = self._source(source_url)
        files = self._archive_files(source)

        if same_date and target_date:
            target_day = date.fromisoformat(target_date)
            same_day_files = self._files_for_month_day(source, target_day)
            if same_day_files:
                return self._result_from_file(source, random.choice(same_day_files))

        if files:
            return self._result_from_file(source, random.choice(files))

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

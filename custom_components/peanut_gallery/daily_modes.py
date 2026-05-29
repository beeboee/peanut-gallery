from __future__ import annotations

import random
from datetime import date

MIN_IMAGE_BYTES = 10000


def apply_daily_mode_patches(client_cls):
    """Patch archive-daily behavior without exposing a user-facing mode switch."""

    def _archive_years_for_month(self, source, target_day: date, archive_end_date: str | None = None) -> list[int]:
        end_limit = self._parse_date(archive_end_date)
        end = min(date.today(), end_limit) if end_limit else date.today()
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
            years.add(day.year)

        return sorted(years)

    def serve_today(
        self,
        source_url: str | None = None,
        archive_end_date: str | None = None,
        daily_mode: str | None = None,
        card_id: str | None = None,
    ):
        source = self._source(source_url)

        # A set archive end date means this card is operating from a finite archive.
        # Use archive-daily behavior automatically; no frontend daily_mode needed.
        if archive_end_date:
            result = self._serve_monthly_random_year_today(source, archive_end_date, card_id)
            if result is not None:
                return result

        return self.serve_day(date.today(), source_url)

    def _serve_monthly_random_year_today(self, source, archive_end_date: str | None, card_id: str | None):
        today = date.today()
        month_key = today.strftime("%Y-%m")
        instance_key = card_id or source.slug
        state = self._load_daily_state()
        instance_state = state.setdefault(instance_key, {})

        matching_years = self._available_matching_years_for_month(source, today, archive_end_date)
        month_years = self._archive_years_for_month(source, today, archive_end_date)
        usable_years = matching_years or month_years
        selected_year = instance_state.get(month_key)

        if selected_year not in usable_years:
            selected_year = random.choice(usable_years) if usable_years else None
            if selected_year is not None:
                instance_state[month_key] = selected_year
                instance_state[f"{month_key}_selection"] = "weekday_aligned" if matching_years else "same_month_fallback"
                self._save_daily_state(state)

        if selected_year is not None:
            chosen_day = date(int(selected_year), today.month, today.day)
            path = self._archive_path_for(source, chosen_day)

            if not path.exists() or path.stat().st_size <= MIN_IMAGE_BYTES:
                try:
                    path = self._fetch_day(source, chosen_day)
                except Exception:
                    month_candidates = [
                        candidate
                        for candidate in self._archive_files(source)
                        if self._day_from_archive_path(source, candidate).year == int(selected_year)
                        and self._day_from_archive_path(source, candidate).month == today.month
                    ]
                    if month_candidates:
                        return self._result_from_file(source, random.choice(month_candidates))
                    raise

            return self._result_from_file(source, path)

        files = self._archive_files(source)
        if files:
            return self._result_from_file(source, random.choice(files))

        return None

    def serve_random(self, source_url: str | None = None, same_date: bool = False, target_date: str | None = None):
        source = self._source(source_url)
        files = self._archive_files(source)

        if same_date:
            # Same-date shuffle is based on the real current calendar date, not the displayed comic date.
            same_day_files = self._files_for_month_day(source, date.today())
            if same_day_files:
                return self._result_from_file(source, random.choice(same_day_files))

        if files:
            return self._result_from_file(source, random.choice(files))

        return self.serve_today(source_url)

    client_cls._archive_years_for_month = _archive_years_for_month
    client_cls.serve_today = serve_today
    client_cls._serve_monthly_random_year_today = _serve_monthly_random_year_today
    client_cls.serve_random = serve_random

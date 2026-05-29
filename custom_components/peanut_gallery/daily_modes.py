from __future__ import annotations

import random
from datetime import date

MIN_IMAGE_BYTES = 10000
DAILY_MODE_MONTHLY_RANDOM_YEAR = "monthly_random_year"


def apply_daily_mode_patches(client_cls):
    """Patch daily-mode behavior without changing the main comic client shape."""

    def _serve_monthly_random_year_today(self, source, archive_end_date: str | None, card_id: str | None):
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
            chosen_day = date(int(selected_year), today.month, today.day)
            path = self._archive_path_for(source, chosen_day)

            if not path.exists() or path.stat().st_size <= MIN_IMAGE_BYTES:
                path = self._fetch_day(source, chosen_day)

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

    client_cls._serve_monthly_random_year_today = _serve_monthly_random_year_today
    client_cls.serve_random = serve_random

from __future__ import annotations

from datetime import date


def apply_navigation_patches(client_cls):
    """Add archive-based previous/next navigation to the client."""

    def _archive_entries(self, source):
        entries = []
        for path in self._archive_files(source):
            try:
                entries.append((self._day_from_archive_path(source, path), path))
            except Exception:
                continue
        return sorted(entries, key=lambda item: item[0])

    def serve_adjacent(
        self,
        source_url: str | None = None,
        current_date: str | None = None,
        direction: str = "previous",
        same_date: bool = False,
    ):
        source = self._source(source_url)
        entries = self._archive_entries(source)

        if not entries:
            raise RuntimeError(f"No archived comics found for {source.slug}")

        current = date.fromisoformat(current_date) if current_date else date.today()

        if same_date:
            entries = [(day, path) for day, path in entries if day.month == current.month and day.day == current.day]
            if not entries:
                raise RuntimeError(f"No archived same-date comics
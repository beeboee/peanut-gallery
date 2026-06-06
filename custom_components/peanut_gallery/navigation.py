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
    ):
        source = self._source(source_url)
        entries = self._archive_entries(source)

        if not entries:
            raise RuntimeError(f"No archived comics found for {source.slug}")

        current = date.fromisoformat(current_date) if current_date else date.today()

        if direction == "next":
            for day, path in entries:
                if day > current:
                    return self._result_from_file(source, path)
            return self._result_from_file(source, entries[0][1])

        for day, path in reversed(entries):
            if day < current:
                return self._result_from_file(source, path)
        return self._result_from_file(source, entries[-1][1])

    client_cls._archive_entries = _archive_entries
    client_cls.serve_adjacent = serve_adjacent

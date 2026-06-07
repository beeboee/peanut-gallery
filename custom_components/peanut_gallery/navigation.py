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

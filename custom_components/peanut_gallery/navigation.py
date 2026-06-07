from datetime import date


def apply_navigation_patches(client_cls):
    def _archive_entries(self, source):
        out = []
        for path in self._archive_files(source):
            try:
                out.append((self._day_from_archive_path(source, path), path))
            except Exception:
                pass
        return sorted(out, key=lambda x: x[0])

    def serve_adjacent(self, source_url=None, current_date=None, direction="previous", same_date=False):
        source = self._source(source_url)
        entries = self._archive_entries(source)
        if not entries:
            raise RuntimeError("No archived comics found")
        current = date.fromisoformat(current_date) if current_date else date.today()
        if same_date:
            entries = [(d, p) for d, p in entries if d.month == current
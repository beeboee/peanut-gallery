# Peanut Gallery

Peanut Gallery is a Home Assistant custom integration and Lovelace card for reading GoComics strips from inside a dashboard.

It was built for Peanuts, but the card can work with other GoComics comic URLs too, such as Garfield, as long as you provide the comic's first-published GoComics URL.

This is an unofficial personal-use integration. It reads GoComics pages and saves images locally, so it may break if GoComics changes its page markup. Use a reasonable download rate.

## Features

- Custom Lovelace card: `custom:peanut-gallery-card`
- Card-specific comic source URLs
- Card-specific IDs, so multiple cards can behave independently
- Today, shuffle, date picker, and open-image controls
- Horizontal comic scrolling with pinned controls
- Hide/show controls by tapping the comic
- Local archive storage under `/config/www/gocomics/<comic>/<year>/<month>/`
- Random shuffle prefers local archived files
- Optional archive end date, useful for finished comics like Peanuts
- Same-date shuffle toggle for holidays and recurring calendar dates
- Native mobile date picker for Time Machine
- Archive progress sensor

## HACS install

1. Open **HACS**.
2. Go to **Integrations**.
3. Open the three-dot menu.
4. Choose **Custom repositories**.
5. Add this repository:

   ```text
   https://github.com/beeboee/peanut-gallery
   ```

6. Category: **Integration**.
7. Install **Peanut Gallery**.
8. Restart Home Assistant.
9. Go to **Settings → Devices & services → Add integration**.
10. Search for **Peanut Gallery** and add it.

## Add the Lovelace card resource

Home Assistant also needs to load the card JavaScript as a dashboard resource.

Go to:

```text
Settings → Dashboards → Resources → Add resource
```

Add:

```text
/peanut_gallery_static/peanut-gallery-card.js
```

Resource type:

```text
JavaScript module
```

After saving, hard-refresh the dashboard or restart Home Assistant.

## Basic card

```yaml
type: custom:peanut-gallery-card
card_id: peanuts_main
source_url: "https://www.gocomics.com/peanuts/1950/10/02"
archive_end_date: "2000-02-13"
auto_today_minutes: 30
```

For Garfield:

```yaml
type: custom:peanut-gallery-card
card_id: garfield_main
source_url: "https://www.gocomics.com/garfield/1978/06/19"
auto_today_minutes: 30
```

## Card options

| Option | Example | What it does |
|---|---|---|
| `card_id` | `peanuts_main` | Unique ID for this card instance. Use a different ID for each independent card. |
| `source_url` | `https://www.gocomics.com/peanuts/1950/10/02` | First-published GoComics URL. The integration extracts the comic slug and start date from this. |
| `archive_end_date` | `2000-02-13` | Optional final archive date. For Peanuts, this prevents downloading post-2000 reruns. |
| `auto_today_minutes` | `30` | After shuffle/date use, return to Today after this many minutes. Use `0` to disable. |
| `auto_load_today` | `true` | If no comic is loaded for this card, automatically load Today. |
| `same_date_shuffle` | `false` | Initial same-date shuffle state. The UI toggle remembers its state per `card_id` in the browser. |
| `action_timeout_seconds` | `75` | Prevents the card from staying disabled forever if a request hangs. |

## Card controls

- **Calendar button**: load Today.
- **Shuffle button**: pick a random local archived comic for this card's source.
- **Three-dot menu**:
  - open image in browser
  - firework toggle for same-date shuffle
  - Time Machine date picker

### Same-date shuffle

Same-date shuffle is useful for fixed-date holidays and seasonal dates.

When enabled, Shuffle uses the displayed comic's month/day and chooses a random archived comic from that same month/day across years.

Examples:

- Feb 14 → random Valentine's Day strip from archived Feb 14 strips
- Oct 31 → random Halloween strip from archived Oct 31 strips
- Dec 25 → random Christmas strip from archived Dec 25 strips
- Jan 1 → random New Year's Day strip from archived Jan 1 strips

Same-date shuffle intentionally ignores weekday/Sunday matching.

The toggle is stored per `card_id` in browser local storage, so `peanuts_main` and `garfield_main` remember separate states on the same device. This setting is not synced between browsers or phones.

## Services

### Today

```yaml
action: peanut_gallery.today
data:
  card_id: peanuts_main
  source_url: "https://www.gocomics.com/peanuts/1950/10/02"
```

### Random

```yaml
action: peanut_gallery.random
data:
  card_id: peanuts_main
  source_url: "https://www.gocomics.com/peanuts/1950/10/02"
```

### Same-date random

```yaml
action: peanut_gallery.random
data:
  card_id: peanuts_main
  source_url: "https://www.gocomics.com/peanuts/1950/10/02"
  same_date: true
  target_date: "2026-12-25"
```

### Specific date

```yaml
action: peanut_gallery.date
data:
  card_id: peanuts_main
  source_url: "https://www.gocomics.com/peanuts/1950/10/02"
  date: "1997-10-22"
```

### Archive step

`archive_step` downloads a small batch and saves progress. Run it repeatedly with an automation to build a local archive.

```yaml
action: peanut_gallery.archive_step
data:
  source_url: "https://www.gocomics.com/peanuts/1950/10/02"
  archive_end_date: "2000-02-13"
  max_items: 5
  delay_seconds: 10
  max_failures_per_date: 1
```

`max_items` is the batch size per call, not the total archive size. The next call resumes from the saved `next_date`.

## Archive automation example

This archives Peanuts only, stopping at the final original strip.

```yaml
alias: Peanut Gallery Archive Grabber
description: Slowly archive original Peanuts into /config/www/gocomics.
mode: single

trigger:
  - platform: time_pattern
    minutes: "/1"

condition: []

action:
  - action: peanut_gallery.archive_step
    data:
      source_url: "https://www.gocomics.com/peanuts/1950/10/02"
      archive_end_date: "2000-02-13"
      max_items: 5
      delay_seconds: 10
      max_failures_per_date: 1
```

This is roughly 300 checked dates per hour when stable. If you see connection resets, increase `delay_seconds` or run the automation less often.

## Local archive paths

Files are stored as:

```text
/config/www/gocomics/<comic>/<year>/<month>/<comic>_<YYYY-MM-DD>.jpg
```

Example:

```text
/config/www/gocomics/peanuts/1950/10/peanuts_1950-10-02.jpg
```

In the browser, `/config/www` is exposed as `/local`, so that file is available at:

```text
/local/gocomics/peanuts/1950/10/peanuts_1950-10-02.jpg
```

Home Assistant does not show folder listings for `/local/` paths. Open a specific file URL or check the files from the terminal.

## Sensors

The integration creates:

```text
sensor.peanut_gallery_date
sensor.peanut_gallery_image_url
sensor.peanut_gallery_queue_size
sensor.peanut_gallery_archive
```

The image sensor exposes per-card results under `attributes.instances`.

Example shape:

```yaml
instances:
  peanuts_main:
    slug: peanuts
    image_url: /local/gocomics/peanuts/1950/10/peanuts_1950-10-02.jpg?1950-10-02
    date: "1950-10-02"
    date_text: Oct 02, 1950
```

The archive sensor exposes archive progress under `attributes.sources`.

## Notes for Peanuts

Peanuts started daily publication on `1950-10-02`.

The original run ended with the final Sunday strip on `2000-02-13`.

Early Peanuts Sundays may show as missing because Sunday Peanuts did not exist yet. Those missing early Sundays are expected and are not the same as network or rate-limit errors.

Use this for a clean original Peanuts archive:

```yaml
source_url: "https://www.gocomics.com/peanuts/1950/10/02"
archive_end_date: "2000-02-13"
```

Without `archive_end_date`, GoComics dates after 2000 may be reruns/reprints rather than new original Peanuts strips.

## Troubleshooting

### Custom element does not exist

Make sure the dashboard resource exists:

```text
/peanut_gallery_static/peanut-gallery-card.js
```

Resource type must be:

```text
JavaScript module
```

Then hard-refresh the dashboard or restart Home Assistant.

### Cache-bust the card resource

Most users should not need this. It is only useful if the browser is stuck on an old card file after an update.

Change the resource URL to include a version query, for example:

```text
/peanut_gallery_static/peanut-gallery-card.js?v=0.3.9
```

### Check archive progress from terminal

```bash
cat /config/peanut_gallery_archive_state.json
```

Count downloaded files:

```bash
find /config/www/gocomics/peanuts -type f | wc -l
```

### Browser URL for local files

Use `/local/...`, not `/config/www/...`.

Correct:

```text
http://ha.local:8123/local/gocomics/peanuts/1950/10/peanuts_1950-10-02.jpg
```

Wrong:

```text
http://ha.local:8123/config/www/gocomics/peanuts/1950/10/
```

## What still requires setup?

Normal users should not need terminal commands.

The only required setup outside HACS is adding the Lovelace resource so Home Assistant loads the custom card JavaScript. That can be done from the Home Assistant UI under **Settings → Dashboards → Resources**.

The terminal commands used during development were mainly for cache-busting and debugging. They are not part of the normal install path.

# Peanut Gallery

Peanut Gallery is a Home Assistant custom integration and Lovelace card for displaying and archiving GoComics comics.

It started as a Peanuts card, but the goal is broader: one dashboard card that can work with any GoComics comic by using that comic's first-published GoComics URL. The project is structured with future source websites in mind, but GoComics is the only supported source right now.

This is an unofficial personal-use integration. It reads GoComics pages and saves images locally, so it may break if GoComics changes its page markup. Use a reasonable download rate and respect the source site.

## Features

- Custom Lovelace card: `custom:peanut-gallery-card`
- Works with GoComics source URLs such as Peanuts, Garfield, and other GoComics comics
- Card-specific comic source URLs
- Card-specific IDs, so multiple cards can behave independently
- Today, shuffle, date picker, and open-image controls
- Horizontal comic scrolling with pinned controls
- Hide/show controls by tapping the comic
- Local archive storage under `/config/www/gocomics/<comic>/<year>/<month>/`
- Random shuffle prefers local archived files
- Optional archive end date for finished comic runs or curated archives
- Monthly random-year daily mode for seasonal finished archives
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

## Basic cards

### Finished archive example: Peanuts

Peanuts has a finished original run, so this card caps the archive at the final original strip and uses `monthly_random_year` for Today.

```yaml
type: custom:peanut-gallery-card
card_id: peanuts_main
source_url: "https://www.gocomics.com/peanuts/1950/10/02"
archive_end_date: "2000-02-13"
daily_mode: monthly_random_year
auto_today_minutes: 30
```

### Ongoing comic example: Garfield

Garfield is ongoing, so this example does not set an archive end date or special daily mode.

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
| `archive_end_date` | `2000-02-13` | Optional final archive date. Useful for finished runs or avoiding modern rerun pages. |
| `daily_mode` | `monthly_random_year` | Optional Today behavior. See daily modes below. |
| `auto_today_minutes` | `30` | After shuffle/date use, return to Today after this many minutes. Use `0` to disable. |
| `auto_load_today` | `true` | If no comic is loaded for this card, automatically load Today. |
| `same_date_shuffle` | `false` | Initial same-date shuffle state. The UI toggle remembers its state per `card_id` in the browser. |
| `action_timeout_seconds` | `75` | Prevents the card from staying disabled forever if a request hangs. |

## Daily modes

### Default / live date

If no `daily_mode` is set, Today requests the comic for the current calendar date from the source.

This is best for ongoing comics.

### `monthly_random_year`

```yaml
daily_mode: monthly_random_year
```

This mode is intended for finished archives, especially comics where you do not want to collect modern rerun pages.

On the first Today request for a card/month, the integration chooses one archived year whose month starts on the same weekday as the current month. It saves that chosen year in:

```text
/config/peanut_gallery_daily_state.json
```

For the rest of the month, Today maps the current month/day onto that chosen archive year.

Example:

```text
Current date: 2026-12-25
Chosen December archive year: 1987
Displayed comic: 1987-12-25
```

This keeps weekday alignment and seasonality while avoiding duplicate post-run reruns.

Fallbacks, in order:

1. exact chosen-year date if locally archived
2. same month + same Sunday/non-Sunday type
3. any archived Sunday/non-Sunday type
4. any archived local comic
5. live Today fetch if no local fallback exists

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
  archive_end_date: "2000-02-13"
  daily_mode: monthly_random_year
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

## Notes for finished comics

For a finished comic, set `archive_end_date` so the archive does not continue into reruns, reposts, or unrelated modern publication dates.

For Peanuts:

```yaml
source_url: "https://www.gocomics.com/peanuts/1950/10/02"
archive_end_date: "2000-02-13"
daily_mode: monthly_random_year
```

Early Peanuts Sundays may show as missing because Sunday Peanuts did not exist yet. Those missing early Sundays are expected and are not the same as network or rate-limit errors.

## Future source support

The current implementation supports GoComics only.

The card and archive folder structure are intentionally generic enough to support other comic sources later. Future source support should keep the same card-facing ideas:

- source URL identifies the comic
- local archive files are stored by comic/date
- cards display by `card_id`
- source-specific scraping stays in backend code

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
/peanut_gallery_static/peanut-gallery-card.js?v=0.4.0
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

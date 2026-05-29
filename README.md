# Peanut Gallery

Peanut Gallery is a Home Assistant integration and Lovelace card for displaying and archiving web comics.

Right now it supports GoComics. The card is source-URL driven, so each card can point at a different comic. The archive is stored locally and can be used for random browsing, fixed-date shuffling, and daily archive-style displays.

This project is unofficial and is not affiliated with GoComics or any comic publisher.

## Features

- **One card, many comics** — point each card at its own GoComics URL.
- **Built in Daily Comics** — Every month, Peanut Gallery picks one archived year per card, and keeps using it for the rest of that month. It prefers years where the month starts on the same weekday as the current month. That keeps the daily reading order seasonal and weekday-aware without archiving duplicates 
- **Flexible groups** — group or seperate cards by giving them the same or different `card_id`.
- **Archive shuffle** — randomize through saved comics.
- **Date-lock shuffle** — shuffle through todays comics of yester-year.
- **Archive daily mode** — pick a matching archive year each month and read it day by day.
- **Time Machine** — choose a specific strip by date, limited to the comic's publish range.
<details>
<summary>Backend functions</summary>
   
- **Local comic archive** — save strips into `/config/www/gocomics/` for fast browsing.
- **Batch archive service** — crawl a comic gradually with configurable batch size and delay.
- **Archive caps** — stop at a chosen end date for finite runs or curated sets.
- **Archive status sensor** — expose date, image URL, queue size, and archive progress in Home Assistant.
- **This month's year** — stored at `/config/peanut_gallery_daily_state.json`

</details>

## Install with HACS

1. Open **HACS**.
2. Go to **Integrations**.
3. Open the three-dot menu.
4. Choose **Custom repositories**.
5. Add this repository:

   ```text
   https://github.com/beeboee/peanut-gallery
   ```

6. Set the category to **Integration**.
7. Install **Peanut Gallery**.
8. Restart Home Assistant.
9. Go to **Settings → Devices & services → Add integration**.
10. Search for **Peanut Gallery** and add it.

## Add the dashboard resource

Home Assistant needs the card JavaScript added as a dashboard resource.

1. Go to: **Settings → Dashboards → Resources → Add resource**
2. Add this URL:
   ```text
   /peanut_gallery_static/peanut-gallery-card.js
   ```
   Resource type: **JavaScript module**

3. Save and Ctrl+F5 Dashboard

## Basic card

Minimum for an ongoing comic:

```yaml
type: custom:peanut-gallery-card
card_id: <anything>
source_url: "https://www.gocomics.com/<comic>/YYYY/MM/DD"
```
<details>
<summary>Example</summary>
   
```yaml
type: custom:peanut-gallery-card
card_id: main_ziggy
source_url: https://www.gocomics.com/ziggy/1971/06/27
```
</details>

For an inactive comic, add an end date:

```yaml
archive_end_date: "YYYY-MM-DD"
```
<details>
<summary>Example</summary>
   
```yaml
type: custom:peanut-gallery-card
source_url: https://www.gocomics.com/peanuts/1950/10/02
card_id: main_peanut
archive_end_date: "2000-02-14"
```
</details>

## Card options

| Option | Required | Description |
|---|---:|---|
| `source_url` | Yes | First published GoComics URL. The "comic slug" and start date are read from this URL. |
| `card_id` | Recommended | Group or seperate cards by giving them the same or different card_id. |
| `archive_end_date` | No | Date of final publication (If applicable)|
| `auto_today_minutes` | No | Returns the card to Today after `x` minutes. Default is `30`. Use `0` to disable. |
| `auto_load_today` | No | Loads Today automatically when the card has no current image. Defaults to `true`. |
| `same_date_shuffle` | No | Initial state for same-date shuffle. The card remembers changes per browser. |
| `action_timeout_seconds` | No | Timeout for card actions. Defaults to `75`. |

## Card controls

- **Calendar**: show  today's comic
- **Shuffle**: show a random comic.
- **Comic image**: tap to hide or show controls.
- **More (•••)**:
  - open image
  - date lock toggle
  - time machine

### Shuffle

Same-date shuffle is controlled by the calendar-lock button in the `More` menu.

When enabled, Shuffle chooses from archived comics with the same month and day as the current calendar date.

For example, on `12-25`, shuffle chooses from archived `12-25` comics across different years.

The toggle is stored in browser local storage per `card_id`. It is not synced between devices.


### Time Machine

The date picker (time machine) is limited by the comic's start date and, when set, `archive_end_date`.


## Home Assistant 
<details>
<summary>Services</summary>

### Today

```yaml
action: peanut_gallery.today
data:
  card_id: my_comic
  source_url: "https://www.gocomics.com/comic-slug/YYYY/MM/DD"
```

With archive daily mode:

```yaml
action: peanut_gallery.today
data:
  card_id: my_archive
  source_url: "https://www.gocomics.com/comic-slug/YYYY/MM/DD"
  archive_end_date: "YYYY-MM-DD"
  daily_mode: monthly_random_year
```

### Random

```yaml
action: peanut_gallery.random
data:
  card_id: my_comic
  source_url: "https://www.gocomics.com/comic-slug/YYYY/MM/DD"
```

### Same-date random

```yaml
action: peanut_gallery.random
data:
  card_id: my_comic
  source_url: "https://www.gocomics.com/comic-slug/YYYY/MM/DD"
  same_date: true
```

### Specific date

```yaml
action: peanut_gallery.date
data:
  card_id: my_comic
  source_url: "https://www.gocomics.com/comic-slug/YYYY/MM/DD"
  date: "YYYY-MM-DD"
```

### Archive step

`archive_step` downloads a small batch and saves progress. Run it repeatedly with an automation to build a local archive.

```yaml
action: peanut_gallery.archive_step
data:
  source_url: "https://www.gocomics.com/comic-slug/YYYY/MM/DD"
  archive_end_date: "YYYY-MM-DD"
  max_items: 5
  delay_seconds: 10
  max_failures_per_date: 1
```

`max_items` is the number of dates checked per call. It is not the total archive size.

</details>

<details>
<summary>Archive automation</summary>

```yaml
alias: Comic Archive Grabber
mode: single

trigger:
  - platform: time_pattern
    minutes: "/1"

condition: []

action:
  - action: peanut_gallery.archive_step
    data:
      source_url: "https://www.gocomics.com/comic-slug/YYYY/MM/DD"
      archive_end_date: "YYYY-MM-DD"
      max_items: 5
      delay_seconds: 10
      max_failures_per_date: 1
```

Adjust the interval, `max_items`, and `delay_seconds` to match how aggressively you want to archive.

</details>

<details>
<summary>Local files and sensors</summary>

Archived images are stored here:

```text
/config/www/gocomics/<comic-slug>/<year>/<month>/<comic-slug>_<YYYY-MM-DD>.jpg
```

Home Assistant exposes `/config/www` as `/local`, so an archived file is available at:

```text
/local/gocomics/<comic-slug>/<year>/<month>/<comic-slug>_<YYYY-MM-DD>.jpg
```

The integration creates these sensors:

```text
sensor.peanut_gallery_date
sensor.peanut_gallery_image_url
sensor.peanut_gallery_queue_size
sensor.peanut_gallery_archive
```

Per-card image data is stored in the image sensor's `instances` attribute.

Archive progress is stored in the archive sensor's `sources` attribute and in:

```text
/config/peanut_gallery_archive_state.json
```

</details>

## Troubleshooting

### The card does not load

Check that this dashboard resource exists:

```text
/peanut_gallery_static/peanut-gallery-card.js
```

It must be a JavaScript module.

### The browser is using an old card file

Add a query string to the dashboard resource URL:

```text
/peanut_gallery_static/peanut-gallery-card.js?v=0.4.0
```

Change the version string after updating if the browser keeps using a cached copy.

### Check archive progress

From the Home Assistant terminal:

```bash
cat /config/peanut_gallery_archive_state.json
```

Count downloaded files for a comic:

```bash
find /config/www/gocomics/<comic-slug> -type f | wc -l
```

## Source support

GoComics is the only supported source today.

The project is intended to support additional comic sources later without changing the card configuration style. A source URL should identify the comic, and source-specific fetching should stay in the backend.

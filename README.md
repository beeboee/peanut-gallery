# Peanut Gallery

A small Home Assistant custom integration for showing Peanuts comics from GoComics.

It can:

- download today's comic
- download a specific dated comic
- keep a small random-comic queue
- expose the current comic date and image URL as sensors
- save the current comic image under `/config/www/peanut_gallery/peanuts.jpg`

This is an unofficial personal-use integration. It scrapes GoComics pages, so it may break if GoComics changes its page markup.

## Install with HACS

1. Open HACS.
2. Go to **Integrations**.
3. Open the three-dot menu.
4. Choose **Custom repositories**.
5. Add this repository URL:

   ```text
   https://github.com/beeboee/peanut-gallery
   ```

6. Category: **Integration**.
7. Install **Peanut Gallery**.
8. Restart Home Assistant.

## Configure

Add this to `configuration.yaml`:

```yaml
peanut_gallery:
```

Optional full config:

```yaml
peanut_gallery:
  cache_size: 3
  start_date: "1950-10-02"
  cache_dir: "www/peanut_gallery/cache"
  current_image: "www/peanut_gallery/peanuts.jpg"
  date_file: "www/peanut_gallery/peanuts_date.txt"
  queue_file: "peanut_gallery_queue.json"
```

Restart Home Assistant after editing `configuration.yaml`.

## Services

### Today's comic

```yaml
action: peanut_gallery.today
```

### Random comic

```yaml
action: peanut_gallery.random
```

### Specific date

```yaml
action: peanut_gallery.date
data:
  date: "1997-10-22"
```

### Refill random cache

```yaml
action: peanut_gallery.refill
```

## Sensors

The integration creates:

```text
sensor.peanut_gallery_date
sensor.peanut_gallery_image_url
sensor.peanut_gallery_queue_size
```

The image URL sensor points to the current saved comic image. By default that image is available at:

```text
/local/peanut_gallery/peanuts.jpg
```

## Example dashboard card

```yaml
type: custom:button-card
entity: sensor.peanut_gallery_image_url
show_name: false
show_icon: false
show_entity_picture: false
grid_options:
  columns: full
styles:
  card:
    - padding: 0
    - border-radius: 6px
    - overflow: hidden
    - width: 100%
  grid:
    - grid-template-areas: '"comic" "date"'
    - grid-template-columns: 1fr
    - grid-template-rows: 1fr auto
  custom_fields:
    comic:
      - width: 100%
    date:
      - padding: 6px
      - font-size: 13px
custom_fields:
  comic: |
    [[[
      const src = states['sensor.peanut_gallery_image_url']?.state || '/local/peanut_gallery/peanuts.jpg';
      return `
        <div style="
          width: 100%;
          overflow-x: auto;
          overflow-y: hidden;
          -webkit-overflow-scrolling: touch;
          scrollbar-width: thin;
        ">
          <img
            src="${src}"
            style="
              display: block;
              height: auto;
              width: 100%;
              max-width: none;
            "
            onload="
              const ratio = this.naturalWidth / this.naturalHeight;
              this.style.width = ratio > 2.2 ? '280%' : '100%';
            "
          />
        </div>
      `;
    ]]]
  date: |
    [[[
      return states['sensor.peanut_gallery_date']?.state || '';
    ]]]
tap_action:
  action: perform-action
  perform_action: peanut_gallery.random

double_tap_action:
  action: url
  url_path: |
    [[[
      return states['sensor.peanut_gallery_image_url']?.state || '/local/peanut_gallery/peanuts.jpg';
    ]]]
```

## Example automation

Refill the cache on Home Assistant start:

```yaml
- alias: Refill Peanut Gallery Cache On Start
  triggers:
    - trigger: homeassistant
      event: start
  actions:
    - action: peanut_gallery.refill
  mode: single
```

## Notes

Peanuts started publication on 1950-10-02, so the default random range starts there.

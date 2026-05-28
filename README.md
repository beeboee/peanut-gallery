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

You can also change these settings from the integration's **Configure** menu in Home Assistant. The repo already includes a config flow and options flow, so this is not limited to add-ons or apps.

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

This card keeps the controls pinned to the visible comic window, not the comic image itself. The comic can be horizontally scrolled while the today, shuffle, and action-menu buttons stay visible.

The bottom-right three-dot button opens a small action menu. The menu contains a download button and a **Time machine** date picker. On phones, the Time machine control uses the operating system's native date picker.

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
    - position: relative
  grid:
    - grid-template-areas: '"comic"'
    - grid-template-columns: 1fr
    - grid-template-rows: 1fr
  custom_fields:
    comic:
      - width: 100%
      - min-width: 0
    today:
      - position: absolute
      - top: 8px
      - left: 8px
      - z-index: 5
    shuffle:
      - position: absolute
      - top: 8px
      - right: 8px
      - z-index: 5
    menu:
      - position: absolute
      - right: 8px
      - bottom: 8px
      - z-index: 5
custom_fields:
  comic: |
    [[[
      const src = states['sensor.peanut_gallery_image_url']?.state || '/local/peanut_gallery/peanuts.jpg';
      const date = states['sensor.peanut_gallery_date']?.state || '';

      return `
        <div style="position: relative; width: 100%;">
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
          <div style="
            position: absolute;
            left: 8px;
            bottom: 8px;
            z-index: 4;
            padding: 6px 10px;
            border-radius: 999px;
            background: rgba(0, 0, 0, 0.55);
            color: white;
            font-size: 13px;
            line-height: 1;
            pointer-events: none;
          ">${date}</div>
        </div>
      `;
    ]]]
  today:
    card:
      type: custom:button-card
      icon: mdi:calendar-today
      show_name: false
      tap_action:
        action: perform-action
        perform_action: peanut_gallery.today
      styles:
        card:
          - width: 42px
          - height: 42px
          - border-radius: 999px
          - background: rgba(0, 0, 0, 0.55)
          - box-shadow: none
          - backdrop-filter: blur(4px)
        icon:
          - color: white
          - width: 24px
  shuffle:
    card:
      type: custom:button-card
      icon: mdi:shuffle-variant
      show_name: false
      tap_action:
        action: perform-action
        perform_action: peanut_gallery.random
      styles:
        card:
          - width: 42px
          - height: 42px
          - border-radius: 999px
          - background: rgba(0, 0, 0, 0.55)
          - box-shadow: none
          - backdrop-filter: blur(4px)
        icon:
          - color: white
          - width: 24px
  menu: |
    [[[
      const src = states['sensor.peanut_gallery_image_url']?.state || '/local/peanut_gallery/peanuts.jpg';
      const currentDate = states['sensor.peanut_gallery_image_url']?.attributes?.date || '';
      const startDate = '1950-10-02';
      const now = new Date();
      const localToday = new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
      const dateValue = currentDate || localToday;
      const pickerId = `peanut-gallery-date-${Math.random().toString(36).slice(2)}`;

      setTimeout(() => {
        const root = this.shadowRoot || this;
        const picker = root.querySelector(`#${pickerId}`);
        if (!picker || picker.dataset.peanutGalleryBound === 'true') return;

        picker.dataset.peanutGalleryBound = 'true';
        picker.addEventListener('click', (event) => event.stopPropagation());
        picker.addEventListener('change', (event) => {
          event.stopPropagation();
          const date = event.target.value;
          if (!date) return;
          hass.callService('peanut_gallery', 'date', { date });
        });
      }, 0);

      return `
        <style>
          .peanut-gallery-menu {
            position: relative;
            outline: none;
          }
          .peanut-gallery-trigger,
          .peanut-gallery-action {
            display: flex;
            align-items: center;
            justify-content: center;
            min-width: 42px;
            height: 42px;
            border-radius: 999px;
            background: rgba(0, 0, 0, 0.55);
            color: white;
            text-decoration: none;
            border: 0;
            box-sizing: border-box;
            backdrop-filter: blur(4px);
          }
          .peanut-gallery-trigger {
            width: 42px;
          }
          .peanut-gallery-panel {
            display: none;
            flex-direction: column-reverse;
            align-items: flex-end;
            gap: 8px;
          }
          .peanut-gallery-menu:focus-within .peanut-gallery-trigger {
            display: none;
          }
          .peanut-gallery-menu:focus-within .peanut-gallery-panel {
            display: flex;
          }
          .peanut-gallery-time-machine {
            position: relative;
            gap: 8px;
            width: max-content;
            padding: 0 14px;
            font-size: 13px;
            line-height: 1;
            font-weight: 500;
          }
          .peanut-gallery-date-input {
            position: absolute;
            inset: 0;
            width: 100%;
            height: 100%;
            opacity: 0;
            cursor: pointer;
          }
        </style>
        <div class="peanut-gallery-menu" tabindex="0" aria-label="Comic actions">
          <div class="peanut-gallery-trigger">
            <ha-icon icon="mdi:dots-horizontal" style="--mdc-icon-size: 24px;"></ha-icon>
          </div>
          <div class="peanut-gallery-panel">
            <a
              class="peanut-gallery-action"
              href="${src}"
              download="peanuts-${dateValue}.jpg"
              target="_blank"
              aria-label="Download comic"
              onclick="event.stopPropagation();"
            >
              <ha-icon icon="mdi:download" style="--mdc-icon-size: 24px;"></ha-icon>
            </a>
            <label class="peanut-gallery-action peanut-gallery-time-machine" aria-label="Pick comic date">
              <ha-icon icon="mdi:calendar-search" style="--mdc-icon-size: 20px;"></ha-icon>
              <span>Time machine</span>
              <input
                id="${pickerId}"
                class="peanut-gallery-date-input"
                type="date"
                min="${startDate}"
                max="${localToday}"
                value="${dateValue}"
              />
            </label>
          </div>
        </div>
      `;
    ]]]
tap_action:
  action: none
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

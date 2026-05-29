class PeanutGalleryCard extends HTMLElement {
  setConfig(config) {
    this.config = {
      card_id: "",
      source_url: "https://www.gocomics.com/peanuts/1950/10/02",
      image_entity: "sensor.peanut_gallery_image_url",
      date_entity: "sensor.peanut_gallery_date",
      today_action: "peanut_gallery.today",
      random_action: "peanut_gallery.random",
      date_action: "peanut_gallery.date",
      fallback_image: "",
      start_date: "1950-10-02",
      show_today_label: true,
      auto_today_minutes: 30,
      auto_load_today: true,
      action_timeout_seconds: 75,
      ...config,
    };

    if (!this.config.card_id) this.config.card_id = this.defaultCardId();
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });

    this.controlsVisible = true;
    this.lastImageSrc = "";
    this.lastDateLabel = "";
    this.actionInProgress = false;
    this.autoTodayTimer = null;
    this.didAutoLoadToday = false;
    this.renderBase();
  }

  static getStubConfig() {
    return {
      card_id: "peanuts_main",
      source_url: "https://www.gocomics.com/peanuts/1950/10/02",
      auto_today_minutes: 30,
      auto_load_today: true,
    };
  }

  static getConfigElement() {
    return document.createElement("peanut-gallery-card-editor");
  }

  set hass(hass) {
    this._hass = hass;
    this.updateFromHass();
  }

  getCardSize() { return 3; }
  $(selector) { return this.shadowRoot.querySelector(selector); }

  todayIso() {
    return new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 10);
  }

  sourceSlugFromUrl(sourceUrl = this.config.source_url) {
    try {
      const url = new URL(sourceUrl);
      return url.pathname.split("/").filter(Boolean)[0] || "peanuts";
    } catch {
      return "peanuts";
    }
  }

  defaultCardId() {
    return `${this.sourceSlugFromUrl()}_main`;
  }

  instanceData() {
    const entity = this._hass?.states?.[this.config.image_entity];
    return entity?.attributes?.instances?.[this.config.card_id] || null;
  }

  serviceData(extra = {}) {
    const data = { ...extra };
    if (this.config.source_url) data.source_url = this.config.source_url;
    if (this.config.card_id) data.card_id = this.config.card_id;
    return data;
  }

  clearAutoToday() {
    if (this.autoTodayTimer) {
      window.clearTimeout(this.autoTodayTimer);
      this.autoTodayTimer = null;
    }
  }

  scheduleAutoToday() {
    this.clearAutoToday();
    const minutes = Number(this.config.auto_today_minutes ?? 30);
    if (!minutes || minutes <= 0) return;
    this.autoTodayTimer = window.setTimeout(() => this.showToday(), minutes * 60 * 1000);
  }

  getImageSrc() {
    const instance = this.instanceData();
    if (instance?.image_url) return instance.image_url;
    return this.config.fallback_image || "";
  }

  getIsoDate() {
    const instance = this.instanceData();
    return instance?.date || "";
  }

  getDateLabel() {
    const instance = this.instanceData();
    const isoDate = this.getIsoDate();
    if (this.config.show_today_label && isoDate === this.todayIso()) return "Today";
    if (instance?.date_text) return instance.date_text;
    return isoDate || "";
  }

  updateFromHass() {
    if (!this.shadowRoot || !this._hass) return;
    const imageSrc = this.getImageSrc();
    const dateLabel = this.getDateLabel();

    if (imageSrc !== this.lastImageSrc) {
      this.lastImageSrc = imageSrc;
      this.setImage(imageSrc);
      this.setImageLink(imageSrc);
    }

    if (dateLabel !== this.lastDateLabel) {
      this.lastDateLabel = dateLabel;
      this.setDateLabel(dateLabel);
      this.setImageLink(imageSrc);
    }

    this.maybeAutoLoadToday(imageSrc);
  }

  maybeAutoLoadToday(imageSrc) {
    if (imageSrc || this.didAutoLoadToday || this.actionInProgress) return;
    if (this.config.auto_load_today === false) return;
    this.didAutoLoadToday = true;
    window.setTimeout(() => this.showToday(), 250);
  }

  setImage(src) {
    const img = this.$("#comic");
    const placeholder = this.$(".placeholder");
    const scroll = this.$(".comic-scroll");
    const card = this.$("ha-card");
    if (!img || !placeholder || !scroll || !card) return;

    const hasImage = Boolean(src);
    card.classList.toggle("no-image", !hasImage);

    if (!hasImage) {
      img.removeAttribute("src");
      scroll.hidden = true;
      placeholder.hidden = false;
      return;
    }

    img.src = src;
    scroll.hidden = false;
    placeholder.hidden = true;
    if (img.complete) this.adjustImageWidth(img);
  }

  setImageLink(src) {
    const link = this.$(".open-image");
    if (!link) return;

    if (!src) {
      link.removeAttribute("href");
      return;
    }

    link.href = src;
    link.removeAttribute("download");
  }

  setDateLabel(text) {
    const label = this.$(".date-label");
    if (label) label.textContent = text || "";
  }

  adjustImageWidth(img) {
    if (!img?.naturalWidth || !img?.naturalHeight) return;
    img.style.width = img.naturalWidth / img.naturalHeight > 2.2 ? "280%" : "100%";
  }

  withTimeout(promise) {
    const seconds = Number(this.config.action_timeout_seconds ?? 75);
    if (!seconds || seconds <= 0) return promise;

    let timer;
    const timeout = new Promise((_, reject) => {
      timer = window.setTimeout(() => reject(new Error(`Peanut Gallery action timed out after ${seconds} seconds`)), seconds * 1000);
    });

    return Promise.race([promise, timeout]).finally(() => window.clearTimeout(timer));
  }

  async callAction(action, data = {}) {
    if (!this._hass || !action) return;
    const [domain, service] = action.split(".");
    if (!domain || !service) return;
    await this.withTimeout(this._hass.callService(domain, service, data));
  }

  refreshImageSoon() {
    window.setTimeout(() => this.updateFromHass(), 250);
    window.setTimeout(() => this.updateFromHass(), 1000);
    window.setTimeout(() => this.updateFromHass(), 2500);
  }

  toggleControls() {
    if (this.actionInProgress) return;
    this.controlsVisible = !this.controlsVisible;
    const card = this.$("ha-card");
    if (card) card.classList.toggle("controls-hidden", !this.controlsVisible);

    if (!this.controlsVisible) {
      const menu = this.$("details.menu");
      if (menu) menu.open = false;
    }
  }

  async runAction(actionName, callback) {
    if (this.actionInProgress) return;

    this.actionInProgress = true;
    this.shadowRoot.host.classList.add("busy");

    try {
      await callback();
      this.refreshImageSoon();
    } finally {
      this.actionInProgress = false;
      this.shadowRoot.host.classList.remove("busy");
    }
  }

  showToday() {
    this.clearAutoToday();
    this.setDateLabel("Today");
    return this.runAction("today", () => this.callAction(this.config.today_action, this.serviceData()));
  }

  showRandom() {
    return this.runAction("random", async () => {
      await this.callAction(this.config.random_action, this.serviceData());
      this.scheduleAutoToday();
    });
  }

  showDate(date) {
    if (!date) return Promise.resolve();
    return this.runAction("date", async () => {
      await this.callAction(this.config.date_action, this.serviceData({ date }));
      this.scheduleAutoToday();
    });
  }

  renderBase() {
    this.shadowRoot.innerHTML = `
      <style>
        :host(.busy) .today,
        :host(.busy) .shuffle,
        :host(.busy) .date-label,
        :host(.busy) .menu-summary,
        :host(.busy) .menu-action,
        :host(.busy) .date-picker,
        :host(.busy) #comic,
        :host(.busy) .placeholder-button {
          pointer-events: none;
          opacity: 0.6;
        }

        ha-card {
          position: relative;
          overflow: hidden;
          border-radius: 6px;
          padding: 0;
        }

        .comic-scroll {
          width: 100%;
          overflow-x: auto;
          overflow-y: hidden;
          -webkit-overflow-scrolling: touch;
          scrollbar-width: thin;
        }

        .comic-scroll[hidden],
        .placeholder[hidden] {
          display: none !important;
        }

        img {
          display: block;
          width: 100%;
          height: auto;
          max-width: none;
          cursor: pointer;
        }

        .placeholder {
          height: 300px;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          gap: 12px;
          color: var(--secondary-text-color);
          background: var(--ha-card-background, var(--card-background-color, white));
          cursor: default;
        }

        .placeholder ha-icon {
          --mdc-icon-size: 56px;
          opacity: 0.75;
        }

        .placeholder-button {
          border: 0;
          border-radius: 999px;
          padding: 8px 16px;
          background: rgba(0, 0, 0, 0.55);
          color: white;
          cursor: pointer;
          font: inherit;
        }

        .overlay-button,
        .menu-action,
        .menu-summary {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 42px;
          height: 42px;
          border: 0;
          border-radius: 999px;
          background: rgba(0, 0, 0, 0.55);
          color: white;
          box-shadow: none;
          cursor: pointer;
          text-decoration: none;
          backdrop-filter: blur(4px);
          -webkit-backdrop-filter: blur(4px);
          box-sizing: border-box;
        }

        .today { position: absolute; top: 8px; left: 8px; z-index: 5; }
        .shuffle { position: absolute; top: 8px; right: 8px; z-index: 5; }
        .date-label { position: absolute; left: 8px; bottom: 8px; z-index: 4; padding: 6px 10px; border-radius: 999px; background: rgba(0, 0, 0, 0.55); color: white; font-size: 13px; line-height: 1; pointer-events: none; }
        .menu { position: absolute; right: 8px; bottom: 8px; z-index: 5; display: flex; flex-direction: column-reverse; align-items: flex-end; gap: 8px; }
        .menu-summary { list-style: none; }
        .menu-summary::-webkit-details-marker { display: none; }
        .menu-panel { display: flex; flex-direction: column-reverse; align-items: flex-end; gap: 8px; margin-bottom: 8px; }
        .time-machine { position: relative; }
        input[type="date"] { position: absolute; inset: 0; width: 100%; height: 100%; opacity: 0; cursor: pointer; }
        ha-card.controls-hidden .today,
        ha-card.controls-hidden .shuffle,
        ha-card.controls-hidden .date-label,
        ha-card.controls-hidden .menu,
        ha-card.no-image .today,
        ha-card.no-image .shuffle,
        ha-card.no-image .date-label,
        ha-card.no-image .menu {
          display: none;
        }
      </style>

      <ha-card class="no-image">
        <div class="placeholder">
          <ha-icon icon="mdi:newspaper-variant-outline"></ha-icon>
          <button class="placeholder-button" type="button">Reload</button>
        </div>
        <div class="comic-scroll" hidden><img id="comic" alt="GoComics comic" /></div>
        <button class="overlay-button today" title="Today" type="button"><ha-icon icon="mdi:calendar-today"></ha-icon></button>
        <button class="overlay-button shuffle" title="Random" type="button"><ha-icon icon="mdi:shuffle-variant"></ha-icon></button>
        <div class="date-label"></div>
        <details class="menu">
          <summary class="menu-summary" title="More"><ha-icon icon="mdi:dots-horizontal"></ha-icon></summary>
          <div class="menu-panel">
            <a class="menu-action open-image" target="_blank" rel="noopener noreferrer" title="Open image"><ha-icon icon="mdi:open-in-new"></ha-icon></a>
            <label class="menu-action time-machine" title="Time machine"><ha-icon icon="mdi:history"></ha-icon><input class="date-picker" type="date" min="${this.config.start_date}" max="${this.todayIso()}" /></label>
          </div>
        </details>
      </ha-card>
    `;

    this.$("#comic").addEventListener("load", (event) => this.adjustImageWidth(event.currentTarget));
    this.$("#comic").addEventListener("click", (event) => { event.stopPropagation(); this.toggleControls(); });
    this.$(".placeholder-button").addEventListener("click", (event) => { event.preventDefault(); event.stopPropagation(); this.showToday(); });
    this.$(".today").addEventListener("click", (event) => { event.preventDefault(); event.stopPropagation(); this.showToday(); });
    this.$(".shuffle").addEventListener("click", (event) => { event.preventDefault(); event.stopPropagation(); this.showRandom(); });
    this.$(".menu").addEventListener("click", (event) => event.stopPropagation());
    this.$(".date-picker").addEventListener("change", (event) => {
      event.stopPropagation();
      this.showDate(event.currentTarget.value);
      const menu = this.$("details.menu");
      if (menu) menu.open = false;
    });
  }
}

class PeanutGalleryCardEditor extends HTMLElement {
  setConfig(config) {
    this.config = { ...config };
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
    this.render();
  }

  set hass(hass) { this._hass = hass; }
  value(key, fallback = "") { return this.config?.[key] ?? fallback; }

  fireChanged() {
    this.dispatchEvent(new CustomEvent("config-changed", { detail: { config: this.config }, bubbles: true, composed: true }));
  }

  updateValue(key, value) {
    this.config = { ...this.config, [key]: value };
    this.fireChanged();
  }

  render() {
    this.shadowRoot.innerHTML = `
      <style>
        .editor { display: grid; gap: 12px; }
        label { display: grid; gap: 4px; font-size: 14px; }
        input { box-sizing: border-box; width: 100%; padding: 8px; border: 1px solid var(--divider-color); border-radius: 4px; background: var(--card-background-color); color: var(--primary-text-color); }
      </style>
      <div class="editor">
        <label>Card ID<input class="card-id" value="${this.value("card_id")}" placeholder="peanuts_main"></label>
        <label>First published GoComics URL<input class="source-url" value="${this.value("source_url", "https://www.gocomics.com/peanuts/1950/10/02")}" placeholder="https://www.gocomics.com/peanuts/1950/10/02"></label>
        <label>Auto-return to Today minutes<input class="auto-today" type="number" min="0" value="${this.value("auto_today_minutes", 30)}"></label>
        <label>Action timeout seconds<input class="action-timeout" type="number" min="0" value="${this.value("action_timeout_seconds", 75)}"></label>
      </div>
    `;

    this.shadowRoot.querySelector(".card-id").addEventListener("change", (event) => this.updateValue("card_id", event.currentTarget.value.trim()));
    this.shadowRoot.querySelector(".source-url").addEventListener("change", (event) => this.updateValue("source_url", event.currentTarget.value.trim()));
    this.shadowRoot.querySelector(".auto-today").addEventListener("change", (event) => this.updateValue("auto_today_minutes", Number(event.currentTarget.value || 0)));
    this.shadowRoot.querySelector(".action-timeout").addEventListener("change", (event) => this.updateValue("action_timeout_seconds", Number(event.currentTarget.value || 0)));
  }
}

if (!customElements.get("peanut-gallery-card")) customElements.define("peanut-gallery-card", PeanutGalleryCard);
if (!customElements.get("peanut-gallery-card-editor")) customElements.define("peanut-gallery-card-editor", PeanutGalleryCardEditor);
window.customCards = window.customCards || [];
window.customCards.push({ type: "peanut-gallery-card", name: "Peanut Gallery Card", description: "Shows a GoComics comic with today, shuffle, open image, and date controls." });

class PeanutGalleryCard extends HTMLElement {
  setConfig(config) {
    this.config = {
      source_url: "https://www.gocomics.com/peanuts/1950/10/02",
      image_entity: "sensor.peanut_gallery_image_url",
      date_entity: "sensor.peanut_gallery_date",
      today_action: "peanut_gallery.today",
      random_action: "peanut_gallery.random",
      date_action: "peanut_gallery.date",
      fallback_image: "/local/peanut_gallery/peanuts.jpg",
      start_date: "1950-10-02",
      show_today_label: true,
      ...config,
    };

    if (!this.shadowRoot) {
      this.attachShadow({ mode: "open" });
    }

    this.controlsVisible = true;
    this.lastImageSrc = "";
    this.lastDateLabel = "";
    this.actionInProgress = false;
    this.renderBase();
  }

  set hass(hass) {
    this._hass = hass;
    this.updateFromHass();
  }

  getCardSize() {
    return 3;
  }

  $(selector) {
    return this.shadowRoot.querySelector(selector);
  }

  todayIso() {
    return new Date(Date.now() - new Date().getTimezoneOffset() * 60000)
      .toISOString()
      .slice(0, 10);
  }
  serviceData(extra = {}) {
    const data = { ...extra };
    if (this.config.source_url) data.source_url = this.config.source_url;
    return data;
  }

  getImageEntity() {
    return this._hass?.states?.[this.config.image_entity];
  }

  getDateEntity() {
    return this._hass?.states?.[this.config.date_entity];
  }

  getImageSrc() {
    const state = this.getImageEntity()?.state;

    if (state && state !== "unknown" && state !== "unavailable") {
      return state;
    }

    return `${this.config.fallback_image}?${Date.now()}`;
  }

  getIsoDate() {
    return this.getImageEntity()?.attributes?.date || "";
  }

  getDateLabel() {
    const isoDate = this.getIsoDate();

    if (this.config.show_today_label && isoDate === this.todayIso()) {
      return "Today";
    }

    const dateText = this.getDateEntity()?.state;
    if (dateText && dateText !== "unknown" && dateText !== "unavailable") {
      return dateText;
    }

    return isoDate || "";
  }

  updateFromHass() {
    if (!this.shadowRoot || !this._hass) return;

    const imageSrc = this.getImageSrc();
    const dateLabel = this.getDateLabel();

    if (imageSrc !== this.lastImageSrc) {
      this.lastImageSrc = imageSrc;
      this.setImage(imageSrc);
      this.setDownload(imageSrc);
    }

    if (dateLabel !== this.lastDateLabel) {
      this.lastDateLabel = dateLabel;
      this.setDateLabel(dateLabel);
      this.setDownload(imageSrc);
    }
  }

  setImage(src) {
    const img = this.$("#comic");
    if (!img || !src) return;

    img.src = src;

    if (img.complete) {
      this.adjustImageWidth(img);
    }
  }

  downloadDatePart() {
    const isoDate = this.getIsoDate();
    if (isoDate) return isoDate;

    const label = this.lastDateLabel || this.getDateLabel();
    const parsed = Date.parse(label);
    if (!Number.isNaN(parsed)) {
      return new Date(parsed).toISOString().slice(0, 10);
    }

    return this.todayIso();
  }

  setDownload(src) {
    const link = this.$(".download");
    if (!link || !src) return;

    link.href = src;
    link.download = `peanuts - ${this.downloadDatePart()}.jpg`;
  }

  setDateLabel(text) {
    const label = this.$(".date-label");
    if (label) label.textContent = text || "";
  }

  adjustImageWidth(img) {
    if (!img?.naturalWidth || !img?.naturalHeight) return;

    const ratio = img.naturalWidth / img.naturalHeight;
    img.style.width = ratio > 2.2 ? "280%" : "100%";
  }

  async callAction(action, data = {}) {
    if (!this._hass || !action) return;

    const [domain, service] = action.split(".");
    if (!domain || !service) return;

    await this._hass.callService(domain, service, data);
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

    if (card) {
      card.classList.toggle("controls-hidden", !this.controlsVisible);
    }

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
    this.setDateLabel("Today");
    return this.runAction("today", () =>
      this.callAction(this.config.today_action, this.serviceData())
    );
  }
  
  showRandom() {
    return this.runAction("random", () =>
      this.callAction(this.config.random_action, this.serviceData())
    );
  }
  
  showDate(date) {
    if (!date) return Promise.resolve();
    return this.runAction("date", () =>
      this.callAction(this.config.date_action, this.serviceData({ date }))
    );
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
        :host(.busy) #comic {
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

        img {
          display: block;
          width: 100%;
          height: auto;
          max-width: none;
          cursor: pointer;
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

        .today {
          position: absolute;
          top: 8px;
          left: 8px;
          z-index: 5;
        }

        .shuffle {
          position: absolute;
          top: 8px;
          right: 8px;
          z-index: 5;
        }

        .date-label {
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
        }

        .menu {
          position: absolute;
          right: 8px;
          bottom: 8px;
          z-index: 5;
          display: flex;
          flex-direction: column-reverse;
          align-items: flex-end;
          gap: 8px;
        }

        .menu-summary {
          list-style: none;
        }

        .menu-summary::-webkit-details-marker {
          display: none;
        }

        .menu-panel {
          display: flex;
          flex-direction: column-reverse;
          align-items: flex-end;
          gap: 8px;
          margin-bottom: 8px;
        }

        .time-machine {
          position: relative;
        }

        input[type="date"] {
          position: absolute;
          inset: 0;
          width: 100%;
          height: 100%;
          opacity: 0;
          cursor: pointer;
        }

        ha-card.controls-hidden .today,
        ha-card.controls-hidden .shuffle,
        ha-card.controls-hidden .date-label,
        ha-card.controls-hidden .menu {
          display: none;
        }
      </style>

      <ha-card>
        <div class="comic-scroll">
          <img id="comic" alt="Peanuts comic" />
        </div>

        <button class="overlay-button today" title="Today" type="button">
          <ha-icon icon="mdi:calendar-today"></ha-icon>
        </button>

        <button class="overlay-button shuffle" title="Random" type="button">
          <ha-icon icon="mdi:shuffle-variant"></ha-icon>
        </button>

        <div class="date-label"></div>

        <details class="menu">
          <summary class="menu-summary" title="More">
            <ha-icon icon="mdi:dots-horizontal"></ha-icon>
          </summary>

          <div class="menu-panel">
            <a class="menu-action download" download="peanuts.jpg" target="_blank" title="Download">
              <ha-icon icon="mdi:download"></ha-icon>
            </a>

            <label class="menu-action time-machine" title="Time machine">
              <ha-icon icon="mdi:history"></ha-icon>
              <input class="date-picker" type="date" min="${this.config.start_date}" max="${this.todayIso()}" />
            </label>
          </div>
        </details>
      </ha-card>
    `;

    this.$("#comic").addEventListener("load", (event) => this.adjustImageWidth(event.currentTarget));
    this.$("#comic").addEventListener("click", (event) => {
      event.stopPropagation();
      this.toggleControls();
    });

    this.$(".today").addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      this.showToday();
    });

    this.$(".shuffle").addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      this.showRandom();
    });

    this.$(".menu").addEventListener("click", (event) => {
      event.stopPropagation();
    });

    this.$(".date-picker").addEventListener("change", (event) => {
      event.stopPropagation();
      this.showDate(event.currentTarget.value);
      const menu = this.$("details.menu");
      if (menu) menu.open = false;
    });
  }
}

if (!customElements.get("peanut-gallery-card")) {
  customElements.define("peanut-gallery-card", PeanutGalleryCard);
}

window.customCards = window.customCards || [];
window.customCards.push({
  type: "peanut-gallery-card",
  name: "Peanut Gallery Card",
  description: "Shows a Peanuts comic with today, shuffle, download, and date controls.",
});

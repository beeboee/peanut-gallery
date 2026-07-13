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
      previous_action: "peanut_gallery.previous",
      next_action: "peanut_gallery.next",
      fallback_image: "",
      start_date: "1950-10-02",
      archive_end_date: "",
      show_today_label: true,
      auto_today_minutes: 30,
      auto_load_today: true,
      action_timeout_seconds: 75,
      same_date_shuffle: false,
      shuffle_mode: false,
      ...config,
    };

    if (!this.config.card_id) this.config.card_id = this.defaultCardId();

    this.sameDateStorageKey = this.sameDateStorageKeyFor(this.config.card_id);
    this.shuffleModeStorageKey = this.shuffleModeStorageKeyFor(this.config.card_id);

    if (!this.shadowRoot) this.attachShadow({ mode: "open" });

    this.controlsVisible = true;
    this.sameDateShuffle = this.loadSameDateShuffle();
    this.shuffleMode = this.loadShuffleMode();

    this.lastImageSrc = "";
    this.lastDateLabel = "";
    this.lastIsoDate = "";
    this.actionInProgress = false;
    this.autoTodayTimer = null;
    this.didAutoLoadToday = false;
    this.onTodayView = false;

    this.shuffleHistory = [];
    this.shuffleIndex = -1;
    this.pendingShuffleRecord = null;

    this.renderBase();
  }

  static getStubConfig() {
    return {
      card_id: "peanuts_main",
      source_url: "https://www.gocomics.com/peanuts/1950/10/02",
      archive_end_date: "2000-02-13",
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

  sourceSlugFromUrl(sourceUrl = this.config.source_url) {
    try {
      const url = new URL(sourceUrl);
      return url.pathname.split("/").filter(Boolean)[0] || "peanuts";
    } catch {
      return "peanuts";
    }
  }

  sourceStartDateFromUrl(sourceUrl = this.config.source_url) {
    try {
      const url = new URL(sourceUrl);
      const parts = url.pathname.split("/").filter(Boolean);
      if (parts.length >= 4) return `${parts[1]}-${parts[2]}-${parts[3]}`;
    } catch {
      // Fall through to configured fallback.
    }

    return this.config.start_date || "1950-10-02";
  }

  datePickerMin() {
    return this.sourceStartDateFromUrl();
  }

  datePickerMax() {
    return this.config.archive_end_date || this.todayIso();
  }

  defaultCardId() {
    return `${this.sourceSlugFromUrl()}_main`;
  }

  sameDateStorageKeyFor(cardId) {
    return `peanut_gallery_same_date_shuffle_${cardId || this.defaultCardId()}`;
  }

  shuffleModeStorageKeyFor(cardId) {
    return `peanut_gallery_shuffle_mode_${cardId || this.defaultCardId()}`;
  }

  loadSameDateShuffle() {
    try {
      const stored = window.localStorage.getItem(this.sameDateStorageKey);
      if (stored === "true") return true;
      if (stored === "false") return false;
    } catch {
      // Ignore localStorage failures and use config default.
    }

    return Boolean(this.config.same_date_shuffle);
  }

  saveSameDateShuffle() {
    try {
      window.localStorage.setItem(this.sameDateStorageKey, this.sameDateShuffle ? "true" : "false");
    } catch {
      // Ignore localStorage failures. The in-memory toggle still works.
    }
  }

  loadShuffleMode() {
    try {
      const stored = window.localStorage.getItem(this.shuffleModeStorageKey);
      if (stored === "true") return true;
      if (stored === "false") return false;
    } catch {
      // Ignore localStorage failures and use config default.
    }

    return Boolean(this.config.shuffle_mode);
  }

  saveShuffleMode() {
    try {
      window.localStorage.setItem(this.shuffleModeStorageKey, this.shuffleMode ? "true" : "false");
    } catch {
      // Ignore localStorage failures. The in-memory toggle still works.
    }
  }

  instanceData() {
    const entity = this._hass?.states?.[this.config.image_entity];
    return entity?.attributes?.instances?.[this.config.card_id] || null;
  }

  serviceData(extra = {}) {
    const data = { ...extra };

    if (this.config.source_url) data.source_url = this.config.source_url;
    if (this.config.card_id) data.card_id = this.config.card_id;
    if (this.config.archive_end_date) data.archive_end_date = this.config.archive_end_date;

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

  clearShuffleHistory() {
    this.shuffleHistory = [];
    this.shuffleIndex = -1;
    this.pendingShuffleRecord = null;
    this.updateNavigationButtons();
  }

  seedShuffleHistoryFromCurrent() {
    const isoDate = this.getIsoDate();
    const imageSrc = this.getImageSrc();

    if (!isoDate) return;

    this.shuffleHistory = [{ date: isoDate, image_url: imageSrc }];
    this.shuffleIndex = 0;
    this.pendingShuffleRecord = null;
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

  targetDateForShuffle() {
    return this.getIsoDate() || this.todayIso();
  }

  updateNavigationButtons() {
    const card = this.$("ha-card");
    const next = this.$(".next");
    const previous = this.$(".previous");

    const hasImage = Boolean(this.getImageSrc());
    const canGoBackInShuffle = this.shuffleMode && this.shuffleHistory.length > 0 && this.shuffleIndex > 0;

    if (card) {
      card.classList.toggle("shuffle-mode", this.shuffleMode);
      card.classList.toggle("same-date-mode", this.sameDateShuffle);
    }

    if (previous) {
      previous.hidden = !hasImage || (this.shuffleMode && !canGoBackInShuffle);

      if (this.shuffleMode) {
        previous.title = "Previous shuffled comic";
      } else if (this.sameDateShuffle) {
        previous.title = "Previous year for this date";
      } else {
        previous.title = "Previous comic";
      }
    }

    if (next) {
      next.hidden = !hasImage;

      if (this.shuffleMode) {
        const canGoForwardInHistory =
          this.shuffleHistory.length > 0 &&
          this.shuffleIndex >= 0 &&
          this.shuffleIndex < this.shuffleHistory.length - 1;

        next.title = canGoForwardInHistory ? "Next shuffled comic" : "Shuffle";
        next.querySelector("ha-icon")?.setAttribute(
          "icon",
          canGoForwardInHistory ? "mdi:arrow-right" : "mdi:shuffle-variant"
        );
      } else {
        next.title = this.sameDateShuffle ? "Next year for this date" : "Next comic";
        next.querySelector("ha-icon")?.setAttribute("icon", "mdi:arrow-right");
      }
    }
  }

  resetComicScroll() {
    const scroll = this.$(".comic-scroll");
    if (!scroll) return;

    const reset = () => {
      scroll.scrollLeft = 0;
      scroll.scrollTop = 0;
    };

    reset();
    window.requestAnimationFrame(reset);
    window.setTimeout(reset, 100);
  }

  recordPendingShuffle() {
    if (!this.pendingShuffleRecord) return;

    const isoDate = this.getIsoDate();
    const imageSrc = this.getImageSrc();

    if (!isoDate || !imageSrc) return;

    const changed =
      isoDate !== this.pendingShuffleRecord.fromDate ||
      imageSrc !== this.pendingShuffleRecord.fromImage;

    if (!changed) return;

    this.shuffleHistory = this.shuffleHistory.slice(0, this.shuffleIndex + 1);

    const last = this.shuffleHistory[this.shuffleHistory.length - 1];
    if (!last || last.date !== isoDate || last.image_url !== imageSrc) {
      this.shuffleHistory.push({ date: isoDate, image_url: imageSrc });
    }

    this.shuffleIndex = this.shuffleHistory.length - 1;
    this.pendingShuffleRecord = null;
  }

  updateFromHass() {
    if (!this.shadowRoot || !this._hass) return;

    const imageSrc = this.getImageSrc();
    const isoDate = this.getIsoDate();
    const dateLabel = this.getDateLabel();

    if (imageSrc !== this.lastImageSrc) {
      this.lastImageSrc = imageSrc;
      this.setImage(imageSrc);
      this.setImageLink(imageSrc);
      this.resetComicScroll();
    }

    if (isoDate !== this.lastIsoDate) {
      this.lastIsoDate = isoDate;
    }

    if (dateLabel !== this.lastDateLabel) {
      this.lastDateLabel = dateLabel;
      this.setDateLabel(dateLabel);
      this.setImageLink(imageSrc);
    }

    this.recordPendingShuffle();
    this.maybeAutoLoadToday(imageSrc);
    this.updateShuffleModeButton();
    this.updateSameDateButton();
    this.updateNavigationButtons();
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
    const textNode = this.$(".date-label-text");

    if (textNode) {
      textNode.textContent = text || "";
      return;
    }

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
      timer = window.setTimeout(
        () => reject(new Error(`Peanut Gallery action timed out after ${seconds} seconds`)),
        seconds * 1000
      );
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
      this.updateNavigationButtons();
    }
  }

  showToday() {
    this.clearAutoToday();
    this.clearShuffleHistory();

    this.onTodayView = true;
    this.setDateLabel("Today");

    const menu = this.$("details.menu");
    if (menu) menu.open = false;

    return this.runAction("today", () => this.callAction(this.config.today_action, this.serviceData()));
  }

  showRandom() {
    this.onTodayView = false;

    const data = this.serviceData();

    if (this.sameDateShuffle) {
      data.same_date = true;
      data.target_date = this.targetDateForShuffle();
    }

    return this.runAction("random", async () => {
      if (this.shuffleMode) {
        if (this.shuffleHistory.length === 0) this.seedShuffleHistoryFromCurrent();

        this.pendingShuffleRecord = {
          fromDate: this.getIsoDate(),
          fromImage: this.getImageSrc(),
        };
      } else {
        this.clearShuffleHistory();
      }

      await this.callAction(this.config.random_action, data);
      this.scheduleAutoToday();
    });
  }

  showDate(date, options = {}) {
    if (!date) return Promise.resolve();

    this.onTodayView = false;

    if (!options.fromShuffleHistory) this.clearShuffleHistory();

    return this.runAction("date", async () => {
      await this.callAction(this.config.date_action, this.serviceData({ date }));
      this.scheduleAutoToday();
    });
  }

  showPrevious() {
    if (this.shuffleMode) {
      if (this.shuffleHistory.length > 0 && this.shuffleIndex > 0) {
        this.shuffleIndex -= 1;
        return this.showDate(this.shuffleHistory[this.shuffleIndex].date, { fromShuffleHistory: true });
      }

      return Promise.resolve();
    }

    this.clearShuffleHistory();
    this.onTodayView = false;

    return this.runAction("previous", async () => {
      await this.callAction(
        this.config.previous_action,
        this.serviceData({
          date: this.getIsoDate(),
          same_date: this.sameDateShuffle,
        })
      );

      this.scheduleAutoToday();
    });
  }

  showNext() {
    if (this.shuffleMode) {
      if (this.shuffleHistory.length > 0 && this.shuffleIndex < this.shuffleHistory.length - 1) {
        this.shuffleIndex += 1;
        return this.showDate(this.shuffleHistory[this.shuffleIndex].date, { fromShuffleHistory: true });
      }

      return this.showRandom();
    }

    this.clearShuffleHistory();
    this.onTodayView = false;

    return this.runAction("next", async () => {
      await this.callAction(
        this.config.next_action,
        this.serviceData({
          date: this.getIsoDate(),
          same_date: this.sameDateShuffle,
        })
      );

      this.scheduleAutoToday();
    });
  }

  toggleShuffleMode() {
    this.shuffleMode = !this.shuffleMode;
    this.saveShuffleMode();

    if (this.shuffleMode) {
      this.seedShuffleHistoryFromCurrent();
    } else {
      this.clearShuffleHistory();
    }

    this.updateShuffleModeButton();
    this.updateSameDateButton();
    this.updateNavigationButtons();
  }

  toggleSameDateShuffle() {
    this.sameDateShuffle = !this.sameDateShuffle;
    this.saveSameDateShuffle();
    this.updateSameDateButton();
    this.updateNavigationButtons();
  }

  updateShuffleModeButton() {
    const button = this.$(".shuffle-mode-toggle");
    if (!button) return;

    button.classList.toggle("active", this.shuffleMode);
    button.title = this.shuffleMode ? "Shuffle mode on" : "Shuffle mode off";
  }

  updateSameDateButton() {
    const button = this.$(".same-date-toggle");
    const datePill = this.$(".date-label");

    if (button) {
      button.hidden = false;
      button.classList.toggle("active", this.sameDateShuffle);
      button.title = this.sameDateShuffle ? "Date-lock on" : "Date-lock off";
    }

    if (datePill) {
      datePill.classList.toggle("locked", this.sameDateShuffle);
    }
  }

  renderBase() {
    this.shadowRoot.innerHTML = `
      <style>
        :host(.busy) .previous,
        :host(.busy) .next,
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

        .menu-action.active {
          background: rgba(255, 255, 255, 0.72);
          color: black;
        }

        .previous {
          position: absolute;
          top: 8px;
          left: 8px;
          z-index: 5;
        }

        .next {
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
          display: inline-flex;
          align-items: center;
          gap: 7px;
          padding: 6px 10px;
          border: 0;
          border-radius: 999px;
          background: rgba(0, 0, 0, 0.55);
          color: white;
          font: inherit;
          font-size: 13px;
          line-height: 1;
          cursor: pointer;
          backdrop-filter: blur(4px);
          -webkit-backdrop-filter: blur(4px);
        }

        .date-label ha-icon {
          --mdc-icon-size: 15px;
          display: none;
        }

        .date-label.locked ha-icon {
          display: block;
        }

        .menu {
          position: absolute;
          right: 8px;
          bottom: 8px;
          z-index: 5;
          width: 92px;
          height: 92px;
          pointer-events: none;
        }

        .menu-summary {
          position: absolute;
          right: 0;
          bottom: 0;
          list-style: none;
          pointer-events: auto;
        }

        .menu-summary::-webkit-details-marker {
          display: none;
        }

        .open-image {
          position: absolute;
          right: 50px;
          bottom: 0;
          pointer-events: auto;
        }

        .menu-panel {
          position: absolute;
          right: 0;
          bottom: 50px;
          display: grid;
          grid-template-columns: repeat(2, 42px);
          gap: 8px;
          justify-content: end;
          pointer-events: auto;
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

        .menu:not([open]) .open-image,
        .menu:not([open]) .menu-panel {
          display: none !important;
        }

        [hidden],
        ha-card.controls-hidden .previous,
        ha-card.controls-hidden .next,
        ha-card.controls-hidden .date-label,
        ha-card.controls-hidden .menu,
        ha-card.no-image .previous,
        ha-card.no-image .next,
        ha-card.no-image .date-label,
        ha-card.no-image .menu {
          display: none !important;
        }
      </style>

      <ha-card class="no-image">
        <div class="placeholder">
          <ha-icon icon="mdi:newspaper-variant-outline"></ha-icon>
          <button class="placeholder-button" type="button">Reload</button>
        </div>

        <div class="comic-scroll" hidden>
          <img id="comic" alt="GoComics comic" />
        </div>

        <button class="overlay-button previous" title="Previous comic" type="button" hidden>
          <ha-icon icon="mdi:arrow-left"></ha-icon>
        </button>

        <button class="overlay-button next" title="Next comic" type="button" hidden>
          <ha-icon icon="mdi:arrow-right"></ha-icon>
        </button>

        <button class="date-label" title="Today" type="button">
          <span class="date-label-text"></span>
          <ha-icon icon="mdi:lock"></ha-icon>
        </button>

        <details class="menu">
          <summary class="menu-summary" title="More">
            <ha-icon icon="mdi:dots-horizontal"></ha-icon>
          </summary>

          <a class="menu-action open-image" target="_blank" rel="noopener noreferrer" title="Open image">
            <ha-icon icon="mdi:open-in-new"></ha-icon>
          </a>

          <div class="menu-panel">
            <button class="menu-action same-date-toggle" type="button" title="Date-lock">
              <ha-icon icon="mdi:calendar-lock"></ha-icon>
            </button>

            <button class="menu-action shuffle-mode-toggle" type="button" title="Shuffle mode">
              <ha-icon icon="mdi:shuffle"></ha-icon>
            </button>

            <label class="menu-action time-machine" title="Time machine">
              <ha-icon icon="mdi:history"></ha-icon>
              <input class="date-picker" type="date" min="${this.datePickerMin()}" max="${this.datePickerMax()}" />
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

    this.$(".placeholder-button").addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      this.showToday();
    });

    this.$(".previous").addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      this.showPrevious();
    });

    this.$(".next").addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      this.showNext();
    });

    this.$(".date-label").addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      this.showToday();
    });

    this.$(".shuffle-mode-toggle").addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      this.toggleShuffleMode();
    });

    this.$(".same-date-toggle").addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      this.toggleSameDateShuffle();
    });

    this.$(".menu").addEventListener("click", (event) => event.stopPropagation());

    this.$(".date-picker").addEventListener("change", (event) => {
      event.stopPropagation();
      this.showDate(event.currentTarget.value);

      const menu = this.$("details.menu");
      if (menu) menu.open = false;
    });

    this.updateShuffleModeButton();
    this.updateSameDateButton();
    this.updateNavigationButtons();
  }
}

class PeanutGalleryCardEditor extends HTMLElement {
  setConfig(config) {
    this.config = { ...config };

    if (!this.shadowRoot) this.attachShadow({ mode: "open" });

    this.render();
  }

  set hass(hass) {
    this._hass = hass;
  }

  value(key, fallback = "") {
    return this.config?.[key] ?? fallback;
  }

  fireChanged() {
    this.dispatchEvent(
      new CustomEvent("config-changed", {
        detail: { config: this.config },
        bubbles: true,
        composed: true,
      })
    );
  }

  updateValue(key, value) {
    this.config = { ...this.config, [key]: value };
    this.fireChanged();
  }

  render() {
    this.shadowRoot.innerHTML = `
      <style>
        .editor {
          display: grid;
          gap: 12px;
        }

        label {
          display: grid;
          gap: 4px;
          font-size: 14px;
        }

        input {
          box-sizing: border-box;
          width: 100%;
          padding: 8px;
          border: 1px solid var(--divider-color);
          border-radius: 4px;
          background: var(--card-background-color);
          color: var(--primary-text-color);
        }
      </style>

      <div class="editor">
        <label>
          Card ID
          <input class="card-id" value="${this.value("card_id")}" placeholder="peanuts_main">
        </label>

        <label>
          First published GoComics URL
          <input class="source-url" value="${this.value("source_url", "https://www.gocomics.com/peanuts/1950/10/02")}" placeholder="https://www.gocomics.com/peanuts/1950/10/02">
        </label>

        <label>
          Archive end date
          <input class="archive-end" type="date" value="${this.value("archive_end_date", "")}">
        </label>

        <label>
          Auto-return to Today minutes
          <input class="auto-today" type="number" min="0" value="${this.value("auto_today_minutes", 30)}">
        </label>

        <label>
          Action timeout seconds
          <input class="action-timeout" type="number" min="0" value="${this.value("action_timeout_seconds", 75)}">
        </label>
      </div>
    `;

    this.shadowRoot.querySelector(".card-id").addEventListener("change", (event) => {
      this.updateValue("card_id", event.currentTarget.value.trim());
    });

    this.shadowRoot.querySelector(".source-url").addEventListener("change", (event) => {
      this.updateValue("source_url", event.currentTarget.value.trim());
    });

    this.shadowRoot.querySelector(".archive-end").addEventListener("change", (event) => {
      this.updateValue("archive_end_date", event.currentTarget.value.trim());
    });

    this.shadowRoot.querySelector(".auto-today").addEventListener("change", (event) => {
      this.updateValue("auto_today_minutes", Number(event.currentTarget.value || 0));
    });

    this.shadowRoot.querySelector(".action-timeout").addEventListener("change", (event) => {
      this.updateValue("action_timeout_seconds", Number(event.currentTarget.value || 0));
    });
  }
}

if (!customElements.get("peanut-gallery-card")) {
  customElements.define("peanut-gallery-card", PeanutGalleryCard);
}

if (!customElements.get("peanut-gallery-card-editor")) {
  customElements.define("peanut-gallery-card-editor", PeanutGalleryCardEditor);
}

window.customCards = window.customCards || [];
window.customCards.push({
  type: "peanut-gallery-card",
  name: "Peanut Gallery Card",
  description: "Shows a GoComics comic with today, shuffle, open image, and date controls.",
});

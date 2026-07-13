import "./peanut-gallery-card-base.js";

const PeanutGalleryCard = customElements.get("peanut-gallery-card");

if (PeanutGalleryCard && !PeanutGalleryCard.__curvedMenuPatched) {
  PeanutGalleryCard.__curvedMenuPatched = true;

  const prototype = PeanutGalleryCard.prototype;
  const originalRenderBase = prototype.renderBase;

  prototype.renderBase = function () {
    originalRenderBase.call(this);

    const menu = this.$("details.menu");
    const panel = this.$(".menu-panel");
    const openImage = this.$(".open-image");
    const sameDate = this.$(".same-date-toggle");
    const shuffleMode = this.$(".shuffle-mode-toggle");
    const timeMachine = this.$(".time-machine");
    if (!menu || !openImage || !sameDate || !shuffleMode || !timeMachine) return;

    const arc = document.createElement("div");
    arc.className = "menu-arc";

    const addItem = (control, className, label) => {
      const item = document.createElement("div");
      item.className = `menu-item ${className}`;

      const caption = document.createElement("span");
      caption.className = "menu-label";
      caption.textContent = label;

      item.append(control, caption);
      arc.append(item);
    };

    addItem(openImage, "menu-item-open", "Open");
    addItem(sameDate, "menu-item-lock", "Lock");
    addItem(shuffleMode, "menu-item-shuffle", "Shuffle");
    addItem(timeMachine, "menu-item-date", "Date");

    panel?.remove();
    menu.append(arc);

    const style = document.createElement("style");
    style.textContent = `
      .menu {
        width: 174px !important;
        height: 166px !important;
        overflow: visible !important;
      }

      .menu-summary {
        right: 0 !important;
        bottom: 0 !important;
      }

      .menu-arc {
        position: absolute;
        inset: 0;
        pointer-events: none;
      }

      .menu-item {
        position: absolute;
        width: 50px;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 2px;
        pointer-events: auto;
        transform-origin: center bottom;
      }

      .menu-item .menu-action {
        position: relative !important;
        inset: auto !important;
        right: auto !important;
        bottom: auto !important;
        flex: 0 0 auto;
      }

      .menu-label {
        max-width: 50px;
        overflow: hidden;
        color: white;
        font-size: 8px;
        font-weight: 600;
        line-height: 1;
        letter-spacing: 0.01em;
        text-align: center;
        text-overflow: ellipsis;
        white-space: nowrap;
        text-shadow: 0 1px 3px rgba(0, 0, 0, 0.95);
        user-select: none;
      }

      .menu-item-open {
        right: 51px;
        bottom: -4px;
      }

      .menu-item-lock {
        right: 91px;
        bottom: 28px;
      }

      .menu-item-shuffle {
        right: 79px;
        bottom: 80px;
      }

      .menu-item-date {
        right: 32px;
        bottom: 111px;
      }

      .menu:not([open]) .menu-arc {
        display: none !important;
      }
    `;
    this.shadowRoot.append(style);
  };
}

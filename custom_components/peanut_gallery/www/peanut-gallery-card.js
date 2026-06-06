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
     
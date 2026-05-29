from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SIGNAL_UPDATED


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities(
        [
            PeanutGalleryDateSensor(hass),
            PeanutGalleryImageSensor(hass),
            PeanutGalleryQueueSensor(hass),
        ],
        True,
    )


class PeanutGalleryBaseSensor(SensorEntity):
    _attr_should_poll = False

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_UPDATED, self.async_write_ha_state)
        )

    @property
    def result(self):
        return self.hass.data.get(DOMAIN, {}).get("last_result")

    @property
    def results(self):
        return self.hass.data.get(DOMAIN, {}).get("results", {})


class PeanutGalleryDateSensor(PeanutGalleryBaseSensor):
    _attr_name = "Peanut Gallery Date"
    _attr_unique_id = "peanut_gallery_date"
    _attr_icon = "mdi:calendar"

    @property
    def native_value(self):
        result = self.result
        return result.date_text if result else None

    @property
    def extra_state_attributes(self):
        return {
            "sources": {
                slug: {
                    "date": result.day.isoformat(),
                    "date_text": result.date_text,
                }
                for slug, result in self.results.items()
            }
        }


class PeanutGalleryImageSensor(PeanutGalleryBaseSensor):
    _attr_name = "Peanut Gallery Image URL"
    _attr_unique_id = "peanut_gallery_image_url"
    _attr_icon = "mdi:image"

    @property
    def native_value(self):
        result = self.result
        if not result:
            return None
        return f"{result.image_url}?{result.day.isoformat()}"

    @property
    def extra_state_attributes(self):
        result = self.result
        attrs = {}

        if result:
            attrs.update(
                {
                    "image_url": result.image_url,
                    "date": result.day.isoformat(),
                    "date_text": result.date_text,
                    "slug": result.slug,
                    "path": str(result.image_path),
                }
            )

        attrs["sources"] = {
            slug: {
                "image_url": f"{item.image_url}?{item.day.isoformat()}",
                "raw_image_url": item.image_url,
                "date": item.day.isoformat(),
                "date_text": item.date_text,
                "path": str(item.image_path),
            }
            for slug, item in self.results.items()
        }

        return attrs


class PeanutGalleryQueueSensor(PeanutGalleryBaseSensor):
    _attr_name = "Peanut Gallery Queue Size"
    _attr_unique_id = "peanut_gallery_queue_size"
    _attr_icon = "mdi:tray-full"

    @property
    def native_value(self):
        result = self.result
        return result.queue_size if result else None

    @property
    def extra_state_attributes(self):
        return {
            "sources": {
                slug: {
                    "queue_size": result.queue_size,
                }
                for slug, result in self.results.items()
            }
        }

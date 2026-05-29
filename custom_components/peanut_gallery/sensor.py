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


def _result_dict(result) -> dict:
    return {
        "slug": result.slug,
        "image_url": f"{result.image_url}?{result.day.isoformat()}",
        "raw_image_url": result.image_url,
        "date": result.day.isoformat(),
        "date_text": result.date_text,
        "path": str(result.image_path),
        "queue_size": result.queue_size,
    }


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

    @property
    def instances(self):
        return self.hass.data.get(DOMAIN, {}).get("instances", {})


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
            },
            "instances": {
                card_id: {
                    "slug": result.slug,
                    "date": result.day.isoformat(),
                    "date_text": result.date_text,
                }
                for card_id, result in self.instances.items()
            },
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
            attrs.update(_result_dict(result))

        attrs["sources"] = {
            slug: _result_dict(item)
            for slug, item in self.results.items()
        }
        attrs["instances"] = {
            card_id: _result_dict(item)
            for card_id, item in self.instances.items()
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
            },
            "instances": {
                card_id: {
                    "slug": result.slug,
                    "queue_size": result.queue_size,
                }
                for card_id, result in self.instances.items()
            },
        }

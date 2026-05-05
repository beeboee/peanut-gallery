from __future__ import annotations

from datetime import date
from pathlib import Path

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .comic import PeanutGalleryClient, PeanutGalleryResult
from .const import (
    CONF_CACHE_DIR,
    CONF_CACHE_SIZE,
    CONF_CURRENT_IMAGE,
    CONF_DATE_FILE,
    CONF_QUEUE_FILE,
    CONF_START_DATE,
    DEFAULT_CACHE_DIR,
    DEFAULT_CACHE_SIZE,
    DEFAULT_CURRENT_IMAGE,
    DEFAULT_DATE_FILE,
    DEFAULT_QUEUE_FILE,
    DEFAULT_START_DATE,
    DOMAIN,
    SERVICE_DATE,
    SERVICE_RANDOM,
    SERVICE_REFILL,
    SERVICE_TODAY,
    SIGNAL_UPDATED,
)

PLATFORMS = ["sensor"]


def _parse_start_date(value: str) -> date:
    return date.fromisoformat(value)


def _build_client(hass: HomeAssistant, data: dict) -> PeanutGalleryClient:
    return PeanutGalleryClient(
        config_dir=Path(hass.config.path()),
        cache_dir=data.get(CONF_CACHE_DIR, DEFAULT_CACHE_DIR),
        current_image=data.get(CONF_CURRENT_IMAGE, DEFAULT_CURRENT_IMAGE),
        date_file=data.get(CONF_DATE_FILE, DEFAULT_DATE_FILE),
        queue_file=data.get(CONF_QUEUE_FILE, DEFAULT_QUEUE_FILE),
        cache_size=int(data.get(CONF_CACHE_SIZE, DEFAULT_CACHE_SIZE)),
        start_date=_parse_start_date(data.get(CONF_START_DATE, DEFAULT_START_DATE)),
    )


async def _async_register_services(hass: HomeAssistant) -> None:
    if hass.data[DOMAIN].get("services_registered"):
        return

    async def _run_and_update(func) -> PeanutGalleryResult | None:
        result = await hass.async_add_executor_job(func)
        if isinstance(result, PeanutGalleryResult):
            hass.data[DOMAIN]["last_result"] = result
        async_dispatcher_send(hass, SIGNAL_UPDATED)
        return result

    async def handle_today(call: ServiceCall) -> None:
        client = hass.data[DOMAIN]["client"]
        await _run_and_update(client.serve_today)

    async def handle_random(call: ServiceCall) -> None:
        client = hass.data[DOMAIN]["client"]
        await _run_and_update(client.serve_random)

    async def handle_date(call: ServiceCall) -> None:
        client = hass.data[DOMAIN]["client"]
        day = date.fromisoformat(call.data["date"])
        await _run_and_update(lambda: client.serve_day(day))

    async def handle_refill(call: ServiceCall) -> None:
        client = hass.data[DOMAIN]["client"]
        await _run_and_update(client.refill)

    hass.services.async_register(DOMAIN, SERVICE_TODAY, handle_today)
    hass.services.async_register(DOMAIN, SERVICE_RANDOM, handle_random)
    hass.services.async_register(
        DOMAIN,
        SERVICE_DATE,
        handle_date,
        schema=vol.Schema({vol.Required("date"): cv.string}),
    )
    hass.services.async_register(DOMAIN, SERVICE_REFILL, handle_refill)
    hass.data[DOMAIN]["services_registered"] = True


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})
    data = {**entry.data, **entry.options}
    hass.data[DOMAIN]["client"] = _build_client(hass, data)
    hass.data[DOMAIN].setdefault("last_result", None)

    await _async_register_services(hass)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_update_options))

    return True


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    data = {**entry.data, **entry.options}
    hass.data[DOMAIN]["client"] = _build_client(hass, data)
    async_dispatcher_send(hass, SIGNAL_UPDATED)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    return unload_ok

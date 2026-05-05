from __future__ import annotations

from datetime import date
from pathlib import Path

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.typing import ConfigType

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

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Optional(CONF_CACHE_SIZE, default=DEFAULT_CACHE_SIZE): vol.Coerce(int),
                vol.Optional(CONF_START_DATE, default=DEFAULT_START_DATE): cv.string,
                vol.Optional(CONF_CACHE_DIR, default=DEFAULT_CACHE_DIR): cv.string,
                vol.Optional(CONF_CURRENT_IMAGE, default=DEFAULT_CURRENT_IMAGE): cv.string,
                vol.Optional(CONF_DATE_FILE, default=DEFAULT_DATE_FILE): cv.string,
                vol.Optional(CONF_QUEUE_FILE, default=DEFAULT_QUEUE_FILE): cv.string,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

PLATFORMS = ["sensor"]


def _parse_start_date(value: str) -> date:
    return date.fromisoformat(value)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    conf = config.get(DOMAIN, {})

    client = PeanutGalleryClient(
        config_dir=Path(hass.config.path()),
        cache_dir=conf.get(CONF_CACHE_DIR, DEFAULT_CACHE_DIR),
        current_image=conf.get(CONF_CURRENT_IMAGE, DEFAULT_CURRENT_IMAGE),
        date_file=conf.get(CONF_DATE_FILE, DEFAULT_DATE_FILE),
        queue_file=conf.get(CONF_QUEUE_FILE, DEFAULT_QUEUE_FILE),
        cache_size=conf.get(CONF_CACHE_SIZE, DEFAULT_CACHE_SIZE),
        start_date=_parse_start_date(conf.get(CONF_START_DATE, DEFAULT_START_DATE)),
    )

    hass.data.setdefault(DOMAIN, {})["client"] = client
    hass.data[DOMAIN]["last_result"] = None

    async def _run_and_update(func) -> PeanutGalleryResult | None:
        result = await hass.async_add_executor_job(func)
        if isinstance(result, PeanutGalleryResult):
            hass.data[DOMAIN]["last_result"] = result
            async_dispatcher_send(hass, SIGNAL_UPDATED)
        else:
            async_dispatcher_send(hass, SIGNAL_UPDATED)
        return result

    async def handle_today(call: ServiceCall) -> None:
        await _run_and_update(client.serve_today)

    async def handle_random(call: ServiceCall) -> None:
        await _run_and_update(client.serve_random)

    async def handle_date(call: ServiceCall) -> None:
        day = date.fromisoformat(call.data["date"])
        await _run_and_update(lambda: client.serve_day(day))

    async def handle_refill(call: ServiceCall) -> None:
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

    await hass.helpers.discovery.async_load_platform("sensor", DOMAIN, {}, config)

    return True

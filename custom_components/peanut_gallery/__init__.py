from __future__ import annotations

import asyncio
from datetime import date
from pathlib import Path

import voluptuous as vol
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .comic import PeanutGalleryClient, PeanutGalleryResult
from .const import (
    CONF_ARCHIVE_END_DATE,
    CONF_CACHE_DIR,
    CONF_CACHE_SIZE,
    CONF_CARD_ID,
    CONF_CURRENT_IMAGE,
    CONF_DAILY_MODE,
    CONF_DATE_FILE,
    CONF_QUEUE_FILE,
    CONF_SAME_DATE,
    CONF_SOURCE_URL,
    CONF_START_DATE,
    CONF_TARGET_DATE,
    DEFAULT_CACHE_DIR,
    DEFAULT_CACHE_SIZE,
    DEFAULT_CURRENT_IMAGE,
    DEFAULT_DATE_FILE,
    DEFAULT_QUEUE_FILE,
    DEFAULT_SOURCE_URL,
    DEFAULT_START_DATE,
    DOMAIN,
    SERVICE_ARCHIVE_STEP,
    SERVICE_DATE,
    SERVICE_RANDOM,
    SERVICE_REFILL,
    SERVICE_TODAY,
    SIGNAL_UPDATED,
)

PLATFORMS = ["sensor"]
FRONTEND_URL = f"/{DOMAIN}_static"
SOURCE_FIELD = vol.Optional(CONF_SOURCE_URL)
CARD_ID_FIELD = vol.Optional(CONF_CARD_ID)
ARCHIVE_END_DATE_FIELD = vol.Optional(CONF_ARCHIVE_END_DATE)
DAILY_MODE_FIELD = vol.Optional(CONF_DAILY_MODE)
SAME_DATE_FIELD = vol.Optional(CONF_SAME_DATE)
TARGET_DATE_FIELD = vol.Optional(CONF_TARGET_DATE)


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
        source_url=data.get(CONF_SOURCE_URL, DEFAULT_SOURCE_URL),
    )


async def _async_register_frontend(hass: HomeAssistant) -> None:
    if hass.data[DOMAIN].get("frontend_registered"):
        return

    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                FRONTEND_URL,
                str(Path(__file__).parent / "www"),
                True,
            )
        ]
    )
    hass.data[DOMAIN]["frontend_registered"] = True


def _store_result(hass: HomeAssistant, result: PeanutGalleryResult, card_id: str | None) -> None:
    instance_id = card_id or result.slug
    hass.data[DOMAIN]["last_result"] = result
    hass.data[DOMAIN].setdefault("results", {})[result.slug] = result
    hass.data[DOMAIN].setdefault("instances", {})[instance_id] = result


async def _async_register_services(hass: HomeAssistant) -> None:
    if hass.data[DOMAIN].get("services_registered"):
        return

    async def _run_and_update(func, card_id: str | None = None) -> PeanutGalleryResult | None:
        result = await hass.async_add_executor_job(func)
        if isinstance(result, PeanutGalleryResult):
            _store_result(hass, result, card_id)
        async_dispatcher_send(hass, SIGNAL_UPDATED)
        return result

    async def _refill_in_background(client: PeanutGalleryClient) -> None:
        try:
            await hass.async_add_executor_job(client.refill)
            async_dispatcher_send(hass, SIGNAL_UPDATED)
        except Exception:
            return

    async def handle_today(call: ServiceCall) -> None:
        client = hass.data[DOMAIN]["client"]
        source_url = call.data.get(CONF_SOURCE_URL)
        card_id = call.data.get(CONF_CARD_ID)
        archive_end_date = call.data.get(CONF_ARCHIVE_END_DATE)
        daily_mode = call.data.get(CONF_DAILY_MODE)
        await _run_and_update(
            lambda: client.serve_today(
                source_url,
                archive_end_date=archive_end_date,
                daily_mode=daily_mode,
                card_id=card_id,
            ),
            card_id,
        )

    async def handle_random(call: ServiceCall) -> None:
        client = hass.data[DOMAIN]["client"]
        source_url = call.data.get(CONF_SOURCE_URL)
        card_id = call.data.get(CONF_CARD_ID)
        same_date = bool(call.data.get(CONF_SAME_DATE, False))
        target_date = call.data.get(CONF_TARGET_DATE)
        await _run_and_update(
            lambda: client.serve_random(source_url, same_date=same_date, target_date=target_date),
            card_id,
        )
        asyncio.create_task(_refill_in_background(client))

    async def handle_date(call: ServiceCall) -> None:
        client = hass.data[DOMAIN]["client"]
        day = date.fromisoformat(call.data["date"])
        source_url = call.data.get(CONF_SOURCE_URL)
        card_id = call.data.get(CONF_CARD_ID)
        await _run_and_update(lambda: client.serve_day(day, source_url), card_id)

    async def handle_refill(call: ServiceCall) -> None:
        client = hass.data[DOMAIN]["client"]
        await _run_and_update(client.refill)

    async def handle_archive_step(call: ServiceCall) -> None:
        client = hass.data[DOMAIN]["client"]
        source_url = call.data.get(CONF_SOURCE_URL)
        max_items = int(call.data.get("max_items", 5))
        delay_seconds = float(call.data.get("delay_seconds", 12))
        max_failures_per_date = int(call.data.get("max_failures_per_date", 3))
        archive_end_date = call.data.get(CONF_ARCHIVE_END_DATE)

        status = await hass.async_add_executor_job(
            lambda: client.archive_step(
                source_url,
                max_items=max_items,
                delay_seconds=delay_seconds,
                max_failures_per_date=max_failures_per_date,
                archive_end_date=archive_end_date,
            )
        )

        hass.data[DOMAIN].setdefault("archive_status", {})[status["slug"]] = status
        async_dispatcher_send(hass, SIGNAL_UPDATED)

    optional_fields = {SOURCE_FIELD: cv.string, CARD_ID_FIELD: cv.string}
    hass.services.async_register(
        DOMAIN,
        SERVICE_TODAY,
        handle_today,
        schema=vol.Schema(
            {
                **optional_fields,
                ARCHIVE_END_DATE_FIELD: cv.string,
                DAILY_MODE_FIELD: cv.string,
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_RANDOM,
        handle_random,
        schema=vol.Schema(
            {
                **optional_fields,
                SAME_DATE_FIELD: cv.boolean,
                TARGET_DATE_FIELD: cv.string,
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_DATE,
        handle_date,
        schema=vol.Schema({vol.Required("date"): cv.string, **optional_fields}),
    )
    hass.services.async_register(DOMAIN, SERVICE_REFILL, handle_refill)
    hass.data[DOMAIN]["services_registered"] = True
    hass.services.async_register(
        DOMAIN,
        SERVICE_ARCHIVE_STEP,
        handle_archive_step,
        schema=vol.Schema(
            {
                SOURCE_FIELD: cv.string,
                ARCHIVE_END_DATE_FIELD: cv.string,
                vol.Optional("max_items", default=5): vol.Coerce(int),
                vol.Optional("delay_seconds", default=12): vol.Coerce(float),
                vol.Optional("max_failures_per_date", default=3): vol.Coerce(int),
            }
        ),
    )

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    hass.data.setdefault(DOMAIN, {})
    await _async_register_frontend(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})
    data = {**entry.data, **entry.options}
    hass.data[DOMAIN]["client"] = _build_client(hass, data)
    hass.data[DOMAIN].setdefault("last_result", None)
    hass.data[DOMAIN].setdefault("results", {})
    hass.data[DOMAIN].setdefault("instances", {})
    hass.data[DOMAIN].setdefault("archive_status", {})

    await _async_register_frontend(hass)
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

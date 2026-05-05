from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

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
)


class PeanutGalleryConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is not None:
            return self.async_create_entry(title="Peanut Gallery", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_CACHE_SIZE, default=DEFAULT_CACHE_SIZE): selector.NumberSelector(
                        selector.NumberSelectorConfig(min=1, max=25, mode=selector.NumberSelectorMode.BOX)
                    ),
                    vol.Optional(CONF_START_DATE, default=DEFAULT_START_DATE): selector.TextSelector(),
                    vol.Optional(CONF_CACHE_DIR, default=DEFAULT_CACHE_DIR): selector.TextSelector(),
                    vol.Optional(CONF_CURRENT_IMAGE, default=DEFAULT_CURRENT_IMAGE): selector.TextSelector(),
                    vol.Optional(CONF_DATE_FILE, default=DEFAULT_DATE_FILE): selector.TextSelector(),
                    vol.Optional(CONF_QUEUE_FILE, default=DEFAULT_QUEUE_FILE): selector.TextSelector(),
                }
            ),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return PeanutGalleryOptionsFlow(config_entry)


class PeanutGalleryOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        data = {**self.config_entry.data, **self.config_entry.options}

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_CACHE_SIZE, default=data.get(CONF_CACHE_SIZE, DEFAULT_CACHE_SIZE)): selector.NumberSelector(
                        selector.NumberSelectorConfig(min=1, max=25, mode=selector.NumberSelectorMode.BOX)
                    ),
                    vol.Optional(CONF_START_DATE, default=data.get(CONF_START_DATE, DEFAULT_START_DATE)): selector.TextSelector(),
                    vol.Optional(CONF_CACHE_DIR, default=data.get(CONF_CACHE_DIR, DEFAULT_CACHE_DIR)): selector.TextSelector(),
                    vol.Optional(CONF_CURRENT_IMAGE, default=data.get(CONF_CURRENT_IMAGE, DEFAULT_CURRENT_IMAGE)): selector.TextSelector(),
                    vol.Optional(CONF_DATE_FILE, default=data.get(CONF_DATE_FILE, DEFAULT_DATE_FILE)): selector.TextSelector(),
                    vol.Optional(CONF_QUEUE_FILE, default=data.get(CONF_QUEUE_FILE, DEFAULT_QUEUE_FILE)): selector.TextSelector(),
                }
            ),
        )

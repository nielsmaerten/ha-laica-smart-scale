"""Config flow for Laica Smart Scale."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_ADDRESS, CONF_NAME
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN


class LaicaSmartScaleConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Laica Smart Scale."""

    VERSION = 2

    _discovery_info: BluetoothServiceInfoBleak | None = None

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> dict:
        """Handle Bluetooth discovery."""

        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()

        self._discovery_info = discovery_info
        self.context["title_placeholders"] = {
            "name": discovery_info.name or "Laica Smart Scale",
            "address": discovery_info.address,
        }
        return await self.async_step_confirm()

    async def async_step_confirm(self, user_input: dict | None = None) -> dict:
        """Confirm discovery."""

        assert self._discovery_info is not None

        if user_input is not None:
            name = (
                user_input.get(CONF_NAME)
                or self._discovery_info.name
                or "Laica Smart Scale"
            )
            return self.async_create_entry(
                title=name,
                data={
                    CONF_ADDRESS: self._discovery_info.address,
                    CONF_NAME: name,
                },
            )

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_NAME, default=self._discovery_info.name or "Laica Smart Scale"
                ): cv.string,
            }
        )
        return self.async_show_form(step_id="confirm", data_schema=schema)

    async def async_step_user(self, user_input: dict | None = None) -> dict:
        """Set up the integration manually."""

        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            name = user_input.get(CONF_NAME) or "Laica Smart Scale"

            await self.async_set_unique_id(address)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=name,
                data={
                    CONF_ADDRESS: address,
                    CONF_NAME: name,
                },
            )

        schema = vol.Schema(
            {
                vol.Required(CONF_ADDRESS): cv.string,
                vol.Optional(CONF_NAME): cv.string,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)

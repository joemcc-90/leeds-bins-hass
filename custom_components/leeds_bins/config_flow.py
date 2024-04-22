"""Config flow for Leeds Bins integration."""

from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback

from .const import CONF_NAME, DOMAIN, check_data, create_form

_LOGGER = logging.getLogger(__name__)


@config_entries.HANDLERS.register(DOMAIN)
class LeedsBinsFlowHandler(config_entries.ConfigFlow):
    """Provide the initial setup."""

    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL
    VERSION = 1

    def __init__(self):
        """Provide the init function of the config flow."""
        # Called once the flow is started by the user
        self._errors = {}

    # will be called by sending the form, until configuration is done
    async def async_step_user(self, user_input=None):  # pylint: disable=unused-argument
        """Provide the first page of the config flow."""
        self._errors = {}
        if user_input is not None:
            # there is user input, check and save if valid (see const.py)
            data_check = await check_data(user_input, self.hass)
            self._errors = data_check["errors"]
            if self._errors == {}:
                self.data = data_check["user_input"]
                user_input = data_check["user_input"]
                return self.async_create_entry(
                    title=user_input[CONF_NAME], data=user_input
                )
        # no user input, or error. Show form
        return self.async_show_form(
            data_schema=vol.Schema(create_form(user_input, self.hass)),
            errors=self._errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Call back to start the change flow."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Change an entity via GUI."""

    def __init__(self, config_entry):
        """Set initial parameter to grab them later on."""
        # store old entry for later
        self.data = {}
        self.data.update(config_entry.data.items())

    # will be called by sending the form, until configuration is done
    async def async_step_init(self, user_input=None):  # pylint: disable=unused-argument
        """Call this as first page."""
        self._errors = {}
        if user_input is not None:
            # there is user input, check and save if valid (see const.py)
            data_check = await check_data(user_input, self.hass)
            self._errors = data_check["errors"]

            if self._errors == {}:
                user_input = data_check["user_input"]
                self.data.update(user_input)
                user_input = data_check["user_input"]
                return self.async_create_entry(
                    title=user_input[CONF_NAME], data=user_input
                )
        elif self.data is not None:
            # if we came straight from init
            user_input = self.data
        # no user input, or error. Show form
        return self.async_show_form(
            data_schema=vol.Schema(create_form(user_input, self.hass)),
            errors=self._errors,
        )

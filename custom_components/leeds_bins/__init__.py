"""The Leeds Bins integration."""

from __future__ import annotations

import logging
import os

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN, CONF_HOUSE_ID

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Leeds Bins from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    cache_file = os.path.join(
        hass.config.config_dir,
        'custom_components',
        DOMAIN,
        'cache',
        f'{entry.data[CONF_HOUSE_ID]}.json')
    if os.path.exists(cache_file):
        _LOGGER.info('Removing cache file')
        try:
            os.remove(cache_file)
        except Exception as e:
            _LOGGER.error('Could not remove file - %s', e)
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        _LOGGER.info("Successfully removed sensor from the Leeds Bins integration")
    return unload_ok

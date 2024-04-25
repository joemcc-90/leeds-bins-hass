"""Support for UK Bin Collection Dat sensors."""

from datetime import timedelta
import logging

from dateutil import parser
import os
import json

from homeassistant.components.sensor import ENTITY_ID_FORMAT, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.config import get_default_config_dir
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import async_generate_entity_id
from homeassistant.helpers.storage import Store
from homeassistant.helpers.entity_platform import AddEntitiesCallback  # noqa: E402
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)
import homeassistant.util.dt as dt_util

from .const import (
    DOMAIN,
    CONF_HOUSE_ID,
    CONF_NAME,
    STATE_ATTR_COLOUR,
    STATE_ATTR_DAYS,
    STATE_ATTR_NEXT_COLLECTION,
    STATE_ATTR_URL,
    STATE_ATTR_URLS,
    BIN_TYPES,
    BIN_ICONS,
    DEFAULT_DATA
)
from .leeds_bins_data_ import find_bin_days

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    _LOGGER.debug("Setting up leeds bins data collection platform")
    _LOGGER.debug("Config supplied: %s", config.data)

    _LOGGER.info("Using house id: %s", config.data.get(CONF_HOUSE_ID))

    coordinator = HouseholdBinCoordinator(
        hass, config.data.get(CONF_HOUSE_ID), config.data.get(CONF_NAME)
    )
    cache_file = os.path.join(
        hass.config.config_dir,
        'custom_components',
        DOMAIN,
        'cache',
        f'{config.data.get(CONF_HOUSE_ID)}.json')
    if not os.path.exists(cache_file):
        _LOGGER.info('Starting initial data download')
        await coordinator.async_config_entry_first_refresh()

    async_add_entities([LeedsBinsDataSensor(coordinator, "GREEN")])
    async_add_entities([LeedsBinsDataSensor(coordinator, "BLACK")])
    async_add_entities([LeedsBinsDataSensor(coordinator, "BROWN")])


def get_latest_collection_info(house_id, updated_at, data) -> dict:
    """Get the next bin collection dates."""
    return find_bin_days(house_id, updated_at, data)


class HouseholdBinCoordinator(DataUpdateCoordinator):
    """Househould Waste Data collection agent."""

    def __init__(self, hass, house_id, name):
        """Initiate data collection agent."""
        super().__init__(
            hass,
            _LOGGER,
            name="Leeds Bins",
            update_interval=timedelta(minutes=60),
        )
        _LOGGER.debug("Initiating data collection agent")
        folder = os.path.join(
            self.hass.config.config_dir,
            'custom_components',
            DOMAIN,
            'cache')
        if not os.path.exists(folder):
            os.makedirs(folder)
        self.house_id = house_id
        self.hass = hass
        self.config_name = name
        self.updated_at = None
        self.cache_file = os.path.join(folder, f'{self.house_id}.json')
        if not os.path.exists(self.cache_file):
            self.data = DEFAULT_DATA
        else:
            with open(self.cache_file, 'r') as file:
                self.data = json.load(file)

    async def _async_update_data(self):
        _LOGGER.debug("Updating data")

        data = await self.hass.async_add_executor_job(
            get_latest_collection_info, self.house_id, self.updated_at, self.data
        )
        if self.updated_at != data["updated_at"]:
            _LOGGER.debug('Writing cache file')
            with open(self.cache_file, 'w') as file:
                json.dump(data, file)
        self.updated_at = data["updated_at"]
        if self.updated_at is not None:
            self.data = data
        _LOGGER.debug("Refreshed data: %s", data)
        return data


class LeedsBinsDataSensor(CoordinatorEntity, SensorEntity):
    """Implementation of the UK Bin Collection Data sensor."""

    def __init__(self, coordinator, bin_type) -> None:
        """Initialize a UK Bin Collection Data sensor."""
        self.house_id = coordinator.house_id
        self.config_name = coordinator.config_name
        super().__init__(coordinator)
        self._bin_type = bin_type
        self.apply_values()
        self.entity_id = (
            'sensor.leeds_bins_' +
            str(self.house_id) +
            '_' +
            str(self._bin_type).lower() +
            '_bin'
        )
        self._id = self.entity_id

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.apply_values()
        self.async_write_ha_state()

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return {
            STATE_ATTR_COLOUR: self._colour,
            STATE_ATTR_NEXT_COLLECTION: self._next_collection,
            STATE_ATTR_DAYS: self._days,
            STATE_ATTR_URL: STATE_ATTR_URLS[self._bin_type]
        }

    def apply_values(self):
        """Set sensor values."""
        self._name = (
            f"{self.config_name + ' - ' if self.config_name else ''}"
            f"{BIN_TYPES[self._bin_type]} bin"
        )
        if self.coordinator.data[self._bin_type] == 'no_data':
            self._next_collection = 'Waiting for data'
        elif self.coordinator.data[self._bin_type] is None:
            self._next_collection = "No collection"
        self._hidden = False
        self._icon = BIN_ICONS[self._bin_type]
        self._colour = self._bin_type
        try:
            self._next_collection = parser.parse(
                self.coordinator.data[self._bin_type], dayfirst=True
            ).date()
            self.calculate_state_and_days()
        except:
            _LOGGER.debug(
                "Bin date is not date - %s",
                self.coordinator.data[self._bin_type])
            self._state = self._next_collection
            self._days = self._next_collection

        _LOGGER.debug("Next collection: %s", self._next_collection)

        _LOGGER.debug("Sensor state - %s", self._state)

    @property
    def name(self):
        """Return the name of the bin."""
        return self._name

    @property
    def hidden(self):
        """Return the hidden attribute."""
        return self._hidden

    @property
    def state(self):
        """Return the state of the bin."""
        return self._state

    @property
    def days(self):
        """Return the remaining days until the collection."""
        return self._days

    @property
    def next_collection(self):
        """Return the next collection of the bin."""
        return self._next_collection

    @property
    def icon(self):
        """Return the entity icon."""
        return self._icon

    @property
    def colour(self):
        """Return the entity icon."""
        return self._colour

    @property
    def unique_id(self):
        """Return a unique ID to use for this sensor."""
        return self.entity_id

    @property
    def bin_type(self):
        """Return the bin type."""
        return self._bin_type

    def calculate_state_and_days(self):
        now = dt_util.now()
        this_week_start = now.date() - timedelta(days=now.weekday())
        this_week_end = this_week_start + timedelta(days=6)
        next_week_start = this_week_end + timedelta(days=1)
        next_week_end = next_week_start + timedelta(days=6)
        week_after_next_start = next_week_end + timedelta(days=1)
        week_after_next_end = week_after_next_start + timedelta(days=6)
        self._days = str((self._next_collection - now.date()).days)
        if self._next_collection == now.date():
            self._state = "Today"
        elif self._next_collection == (now + timedelta(days=1)).date():
            self._state = "Tomorrow"
        elif self._next_collection < now.date():
            self._state = "Collected - Waiting new data"
        elif (
            self._next_collection >= this_week_start
            and self._next_collection <= this_week_end
        ):
            self._state = f"This week - {self._next_collection.strftime('%A')}"
        elif (
            self._next_collection >= next_week_start
            and self._next_collection <= next_week_end
        ):
            self._state = f"Next week - {self._next_collection.strftime('%A')}"
        elif (
            self._next_collection >= week_after_next_start
            and self._next_collection <= week_after_next_end
        ):
            self._state = f"Week after next - {self._next_collection.strftime('%A')}"
        elif self._next_collection > week_after_next_end:
            self._state = f"Future - {self._next_collection}"
        else:
            self._state = "Unknown"
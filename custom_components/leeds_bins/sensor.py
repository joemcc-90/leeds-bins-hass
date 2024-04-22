"""Support for UK Bin Collection Dat sensors."""

from datetime import timedelta

from dateutil import parser
import leeds_bins_data

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)
import homeassistant.util.dt as dt_util

from .const import (
    CONF_HOUSE,
    CONF_POSTCODE,
    LOG_PREFIX,
    STATE_ATTR_COLOUR,
    STATE_ATTR_DAYS,
    STATE_ATTR_NEXT_COLLECTION,
    load_house_id,
)

"""The UK Bin Collection Data integration."""
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback  # noqa: E402

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    _LOGGER.info(LOG_PREFIX + "Setting up leeds bins data collection platform.")
    _LOGGER.info(LOG_PREFIX + "Data Supplied: %s", config.data)

    user_input = {}
    user_input[CONF_POSTCODE] = config.data.get("postcode")
    user_input[CONF_HOUSE] = config.data.get("house")

    house_id = await load_house_id(hass, user_input)

    _LOGGER.info(f"{LOG_PREFIX} Leeds Bins args: {house_id}")

    coordinator = HouseholdBinCoordinator(hass, house_id)

    _LOGGER.info(f"{LOG_PREFIX} Leeds Bins Init Refresh")
    await coordinator.async_config_entry_first_refresh()
    _LOGGER.info(f"{LOG_PREFIX} Leeds Bins Init Refresh complete")

    async_add_entities([LeedsBinsDataSensor(coordinator, "GREEN")])
    async_add_entities([LeedsBinsDataSensor(coordinator, "BLACK")])
    async_add_entities([LeedsBinsDataSensor(coordinator, "BROWN")])


def get_latest_collection_info(house_id) -> dict:
    next_collection_dates = leeds_bins_data.find_bin_days(house_id)

    _LOGGER.info(f"{LOG_PREFIX} Next Collection Dates: {next_collection_dates}")
    return next_collection_dates


class HouseholdBinCoordinator(DataUpdateCoordinator):
    """Household Bin Coordinator"""

    def __init__(self, hass, house_id):
        """Initialize my coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="Leeds Bins",
            update_interval=timedelta(minutes=10),
        )
        _LOGGER.info(f"{LOG_PREFIX} Leeds Bins Init")
        self.house_id = house_id
        self.hass = hass

    async def _async_update_data(self):
        _LOGGER.info(f"{LOG_PREFIX} Leeds Bins Updating")

        data = await self.hass.async_add_executor_job(
            get_latest_collection_info, self.house_id
        )

        _LOGGER.info(f"{LOG_PREFIX} Leeds Bins: {data}")

        return data


class LeedsBinsDataSensor(CoordinatorEntity, SensorEntity):
    """Implementation of the UK Bin Collection Data sensor."""

    def __init__(self, coordinator, bin_type) -> None:
        """Initialize a UK Bin Collection Data sensor."""
        super().__init__(coordinator)
        self._bin_type = bin_type
        self.apply_values()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.apply_values()
        self.async_write_ha_state()

    @property
    def extra_state_attributes(self):
        """Return the state attributes of the bins."""
        return {
            STATE_ATTR_COLOUR: self._colour,
            STATE_ATTR_NEXT_COLLECTION: self._next_collection,
            STATE_ATTR_DAYS: self._days,
        }

    def apply_values(self):
        _LOGGER.info(f"{LOG_PREFIX} Applying values for sensor {self._bin_type}")
        name = self._bin_type
        if self.coordinator.name != "":
            name = f"{self.coordinator.name} {self._bin_type}"
        self._id = name
        self._name = name
        self._next_collection = parser.parse(
            self.coordinator.data[self._bin_type], dayfirst=True
        ).date()
        self._hidden = False
        self._icon = "mdi:trash-can"
        self._colour = self._bin_type
        self._state = "unknown"

        _LOGGER.info(
            f"{LOG_PREFIX} Data Stored in self.next_collection: {self._next_collection}"
        )
        _LOGGER.info(f"{LOG_PREFIX} Data Stored in self.name: {self._name}")

        now = dt_util.now()
        this_week_start = now.date() - timedelta(days=now.weekday())
        this_week_end = this_week_start + timedelta(days=6)
        next_week_start = this_week_end + timedelta(days=1)
        next_week_end = next_week_start + timedelta(days=6)

        self._days = (self._next_collection - now.date()).days
        _LOGGER.info(f"{LOG_PREFIX} _days: {self._days}")

        if self._next_collection == now.date():
            self._state = "Today"
        elif self._next_collection == (now + timedelta(days=1)).date():
            self._state = "Tomorrow"
        elif (
            self._next_collection >= this_week_start
            and self._next_collection <= this_week_end
        ):
            self._state = f"This Week: {self._next_collection.strftime('%A')}"
        elif (
            self._next_collection >= next_week_start
            and self._next_collection <= next_week_end
        ):
            self._state = f"Next Week: {self._next_collection.strftime('%A')}"
        elif self._next_collection > next_week_end:
            self._state = f"Future: {self._next_collection}"
        elif self._next_collection < now.date():
            self._state = "Past"
        else:
            self._state = "Unknown"

        _LOGGER.info(f"{LOG_PREFIX} State of the sensor: {self._state}")

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
        return self._id

    @property
    def bin_type(self):
        """Return the bin type."""
        return self._bin_type

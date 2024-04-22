"""Constants for the Leeds Bins integration."""

from collections import OrderedDict
import logging

import voluptuous as vol

from homeassistant.components.date import ENTITY_ID_FORMAT, PLATFORM_SCHEMA
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import async_generate_entity_id

from .leeds_bins_data_ import find_house_id

_LOGGER = logging.getLogger(__name__)

DOMAIN = "leeds_bins"
PLATFORM = "sensor"
VERSION = "0.1"
ISSUE_URL = "https://github.com/joemcc-90/leeds-bins-hass/issues"
LOG_PREFIX = "Leeds Bins"

# configuration
CONF_NAME = "name"
CONF_HOUSE = "house"
CONF_POSTCODE = "postcode"
CONF_HOUSE_ID = "house_id"

# defaults
DEFAULT_NAME = ""
DEFAULT_HOUSE = ""
DEFAULT_POSTCODE = ""
DEFAULT_HOUSE_ID = None

# errors
ERROR_POSTCODE = "invalid_postcode"
ERROR_HOUSE_ID = "house_not_found"

# states
STATE_ATTR_COLOUR = "colour"
STATE_ATTR_NEXT_COLLECTION = "next_collection"
STATE_ATTR_DAYS = "days"
STATE_ATTR_URL = "Info URL"
# what to put in urls
STATE_ATTR_URLS = {
    "GREEN": "https://www.leeds.gov.uk/residents/bins-and-recycling/your-bins/green-recycling-bin",
    "BROWN": "https://www.leeds.gov.uk/residents/bins-and-recycling/your-bins/brown-garden-waste-bin",
    "BLACK": "https://www.leeds.gov.uk/residents/bins-and-recycling/your-bins/black-bin"
}
# bin types
BIN_TYPES = {
    "GREEN": 'Recycling',
    "BLACK": 'General Waste',
    "BROWN": 'Garden Waste'
}

# extend schema to load via YAML
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Required(CONF_HOUSE, default=DEFAULT_HOUSE): cv.string,
        vol.Required(CONF_POSTCODE, default=DEFAULT_POSTCODE): cv.string,
        vol.Optional(CONF_HOUSE_ID, default=DEFAULT_HOUSE_ID): cv.string,
    }
)


def get_next_id(hass):
    """Provide the next unused id."""
    if hass is None:
        return 1
    for i in range(1, 999):
        if async_generate_entity_id(
            ENTITY_ID_FORMAT, "ics_" + str(i), hass=hass
        ) == PLATFORM + ".ics_" + str(i):
            return i
    return 999


def ensure_config(user_input, hass):
    """Make sure that needed Parameter exist and are filled with default if not."""
    out = {}
    out[CONF_NAME] = DEFAULT_NAME
    out[CONF_HOUSE] = ""
    out[CONF_POSTCODE] = ""
    out[CONF_HOUSE_ID] = None

    if user_input is not None:
        if CONF_NAME in user_input:
            out[CONF_NAME] = user_input[CONF_NAME]
        if CONF_HOUSE in user_input:
            out[CONF_HOUSE] = user_input[CONF_HOUSE]
        if CONF_POSTCODE in user_input:
            out[CONF_POSTCODE] = user_input[CONF_POSTCODE]
        if CONF_HOUSE_ID in user_input:
            out[CONF_HOUSE_ID] = user_input[CONF_HOUSE_ID]
        elif CONF_HOUSE_ID not in user_input:
            out[CONF_HOUSE_ID] = ""
    return out


def create_form(user_input, hass):
    """Create form for UI setup."""
    user_input = ensure_config(user_input, hass)

    data_schema = OrderedDict()
    data_schema[vol.Optional(CONF_NAME, default=user_input[CONF_NAME])] = str
    data_schema[vol.Required(CONF_HOUSE, default=user_input[CONF_HOUSE])] = str
    data_schema[vol.Required(CONF_POSTCODE, default=user_input[CONF_POSTCODE])] = str
    return data_schema


async def check_data(user_input, hass, own_id=None):
    """Check validity of the provided date."""
    user_input = ensure_config(user_input, hass)
    return_ = {}
    errors = {}
    if CONF_POSTCODE in user_input:
        if user_input[CONF_POSTCODE].count(" ") != 1:
            if len(user_input[CONF_POSTCODE]) == 6:
                _LOGGER.info(
                    "%s postcode has 6 digits and no space, adding space after 3rd digit",
                    LOG_PREFIX,
                )
                user_input[CONF_POSTCODE] = (
                    user_input[CONF_POSTCODE][:3] + " " + user_input[CONF_POSTCODE][3:]
                )
                _LOGGER.info(user_input[CONF_POSTCODE])
            elif len(user_input[CONF_POSTCODE]) == 7:
                _LOGGER.info(
                    "%s postcode has 7 digits and no space, adding space after 4th digit",
                    LOG_PREFIX,
                )
                user_input[CONF_POSTCODE] = (
                    user_input[CONF_POSTCODE][:4] + " " + user_input[CONF_POSTCODE][4:]
                )
            else:
                _LOGGER.error("%s postcode has neither 6 or 7 digits", LOG_PREFIX)
                errors["postcode"] = ERROR_POSTCODE
                return_["errors"] = errors
                return return_
        elif user_input[CONF_POSTCODE].count(" ") == 1:
            if (
                len(user_input[CONF_POSTCODE]) == 7
                or len(user_input[CONF_POSTCODE]) == 8
            ):
                _LOGGER.info("%s postcode check ok", LOG_PREFIX)
            else:
                errors["postcode"] = ERROR_POSTCODE
                return_["errors"] = errors
                return return_
    _LOGGER.debug(user_input[CONF_POSTCODE])
    if user_input[CONF_HOUSE_ID] == "":
        user_input[CONF_HOUSE_ID] = await load_house_id(hass, user_input)
        if user_input[CONF_HOUSE_ID] is None:
            _LOGGER.error("%s House not found. User input - %s", LOG_PREFIX, user_input)
            errors["base"] = ERROR_HOUSE_ID
            return_["errors"] = errors
            return return_
    _LOGGER.info("%s Validated user input - %s", LOG_PREFIX, user_input)
    return_["errors"] = errors
    return_["user_input"] = user_input
    return return_


async def load_house_id(hass, user_input):
    """Load the house id."""
    return await hass.async_add_executor_job(
        find_house_id, user_input[CONF_POSTCODE], user_input[CONF_HOUSE]
    )

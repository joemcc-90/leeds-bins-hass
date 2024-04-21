"""Constants for the Leeds Bins integration."""

from collections import OrderedDict
import logging

import voluptuous as vol

from homeassistant.components.date import ENTITY_ID_FORMAT, PLATFORM_SCHEMA
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import async_generate_entity_id

from .leeds_bins import find_house_id

DOMAIN = "leeds_bins"
PLATFORM = "sensor"
VERSION = "0.1"
ISSUE_URL = "https://github.com/joemcc-90/leeds-bins-hass/issues"

# configuration
CONF_ICON = "icon"
CONF_NAME = "name"
CONF_HOUSE = "house"
CONF_POSTCODE = "postcode"
CONF_HOUSE_ID = "house_id"
CONF_ID = "id"

# defaults
DEFAULT_ICON = "mdi:delete-empty"
DEFAULT_NAME = "Home"
DEFAULT_HOUSE = ""
DEFAULT_POSTCODE = ""
DEFAULT_HOUSE_ID = None
DEFAULT_ID = 1

# errors
ERROR_POSTCODE = "invalid_postcode"
ERROR_HOUSE_ID = "house_not_found"


# extend schema to load via YAML
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Required(CONF_HOUSE, default=DEFAULT_HOUSE): cv.string,
        vol.Required(CONF_POSTCODE, default=DEFAULT_POSTCODE): cv.string,
        vol.Optional(CONF_HOUSE_ID, default=DEFAULT_HOUSE_ID): cv.string,
        vol.Optional(CONF_ICON, default=DEFAULT_ICON): cv.string,
        vol.Optional(CONF_ID, default=DEFAULT_ID): vol.Coerce(int),
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
    out[CONF_ICON] = DEFAULT_ICON
    out[CONF_NAME] = DEFAULT_NAME
    out[CONF_HOUSE] = ""
    out[CONF_POSTCODE] = ""
    out[CONF_HOUSE_ID] = None
    out[CONF_ID] = get_next_id(hass)

    if user_input is not None:
        if CONF_NAME in user_input:
            out[CONF_NAME] = user_input[CONF_NAME]
        if CONF_ICON in user_input:
            out[CONF_ICON] = user_input[CONF_ICON]
        if CONF_HOUSE in user_input:
            out[CONF_HOUSE] = user_input[CONF_HOUSE]
        if CONF_POSTCODE in user_input:
            out[CONF_POSTCODE] = user_input[CONF_POSTCODE]
        if CONF_HOUSE_ID in user_input:
            out[CONF_HOUSE_ID] = user_input[CONF_HOUSE_ID]
        elif CONF_HOUSE_ID not in user_input:
            out[CONF_HOUSE_ID] = ""
        if CONF_ID in user_input:
            out[CONF_ID] = user_input[CONF_ID]
    return out


def create_form(user_input, hass):
    """Create form for UI setup."""
    user_input = ensure_config(user_input, hass)

    data_schema = OrderedDict()
    data_schema[vol.Required(CONF_NAME, default=user_input[CONF_NAME])] = str
    data_schema[vol.Optional(CONF_ICON, default=user_input[CONF_ICON])] = str
    data_schema[vol.Required(CONF_HOUSE, default=user_input[CONF_HOUSE])] = str
    data_schema[vol.Required(CONF_POSTCODE, default=user_input[CONF_POSTCODE])] = str
    data_schema[vol.Required(CONF_ID, default=user_input[CONF_ID])] = int
    return data_schema


async def check_data(user_input, hass, own_id=None):
    """Check validity of the provided date."""
    user_input = ensure_config(user_input, hass)
    ret = {}
    if CONF_POSTCODE in user_input:
        if user_input[CONF_POSTCODE].count(" ") != 1:
            if len(user_input[CONF_POSTCODE]) == 6:
                logging.debug("postcode has 6 digits")
                user_input[CONF_POSTCODE] = (
                    user_input[CONF_POSTCODE][:3] + " " + user_input[CONF_POSTCODE][3:]
                )
                print(user_input[CONF_POSTCODE])
            elif len(user_input[CONF_POSTCODE]) == 7:
                logging.debug("postcode has 7 digits")
                user_input[CONF_POSTCODE] = (
                    user_input[CONF_POSTCODE][:4] + " " + user_input[CONF_POSTCODE][4:]
                )
            else:
                logging.debug("postcode has neither 6 or 7 digits")
                ret["base"] = ERROR_POSTCODE
                return ret
        elif user_input[CONF_POSTCODE].count(" ") == 1:
            if (
                len(user_input[CONF_POSTCODE]) == 7
                or len(user_input[CONF_POSTCODE]) == 8
            ):
                logging.info("postcode ok")
            else:
                ret["base"] = ERROR_POSTCODE
                return ret
    print(user_input[CONF_POSTCODE])
    if user_input[CONF_HOUSE_ID] == "":
        user_input[CONF_HOUSE_ID] = await load_house_id(hass, user_input)
        if user_input[CONF_HOUSE_ID] is None:
            ret["base"] = ERROR_HOUSE_ID
            return ret
    return ret


async def load_house_id(hass, user_input):
    """Load the house id."""
    return await hass.async_add_executor_job(
        find_house_id, user_input[CONF_POSTCODE], user_input[CONF_HOUSE]
    )

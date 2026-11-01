"""Leeds bins module."""

import csv, os
from datetime import datetime, timezone
from io import StringIO
import logging

import requests

_LOGGER = logging.getLogger(__name__)


# Ways to choose a collection date for a bin colour the address has no data for,
# using other addresses in the same postcode.
FALLBACK_NEAREST_SIDE = "nearest_same_side"
FALLBACK_NEAREST_SEQUENTIAL = "nearest_sequential"
FALLBACK_EARLIEST = "earliest"
FALLBACK_MOST_COMMON = "most_common"
FALLBACK_MODES = [
    FALLBACK_NEAREST_SIDE,
    FALLBACK_NEAREST_SEQUENTIAL,
    FALLBACK_EARLIEST,
    FALLBACK_MOST_COMMON,
]
DEFAULT_FALLBACK_MODE = FALLBACK_NEAREST_SIDE

BIN_COLOURS = ["BROWN", "BLACK", "GREEN"]


def find_postcode_premises(postcode):
    """Return every premises in a postcode, or None if the lookup failed."""
    csv_url = "https://opendata.leeds.gov.uk/downloads/bins/dm_premises.csv"

    try:
        response = requests.get(csv_url, timeout=200)
        if response.status_code != 200:
            _LOGGER.debug("Failed to fetch CSV from the web")
            return None
        postcode = postcode.upper()
        csv_io = StringIO(response.content.decode("utf-8"))
        premises = []
        for row in csv.reader(csv_io):
            if len(row) < 7 or row[6] != postcode:
                continue
            premises.append(
                {
                    "id": row[0],
                    "name": row[1].strip(),
                    "number": row[2].strip(),
                    "street": row[3].strip(),
                    "raw_name": row[1],
                    "raw_number": row[2],
                }
            )
        csv_io.close()
        return premises
    except Exception as e:
        _LOGGER.error("Error occurred: %s", e)
        return None


def match_house_id(premises, house):
    """Find the premises id for a house number or name within a postcode."""
    if premises is None:
        return None
    if house.isdigit():
        key = "raw_number"
    else:
        key = "raw_name"
        house = house.upper()
    for premise in premises:
        if premise[key] == house:
            return premise["id"]
    return None


def find_house_id(postcode, house):
    """Find house ID."""
    return match_house_id(find_postcode_premises(postcode), house)


def find_address(postcode, house):
    """Find house ID and the other premises in its postcode with one download."""
    premises = find_postcode_premises(postcode)
    return match_house_id(premises, house), premises


def find_bin_days(house_id, updated_at, old_data, cache_csv_file, fallback=None):
    """Find next bin days."""
    csv_url = "https://opendata.leeds.gov.uk/downloads/bins/dm_jobs.csv"
    try:
        response = requests.head(
            csv_url, timeout=200
        )  # Use HEAD request to fetch only headers
    except Exception as e:
        _LOGGER.error("Failed to fetch data from web - %s", e)
        return get_next_dates_from_cache(cache_csv_file, old_data, house_id, fallback)
    if response.status_code != 200:
        _LOGGER.debug("Failed to fetch CSV from the web")
        return get_next_dates_from_cache(cache_csv_file, old_data, house_id, fallback)
    
    last_modified_str = response.headers.get("Last-Modified")
    if not last_modified_str:
        _LOGGER.debug("Last-Modified header not found")
        return get_next_dates_from_cache(cache_csv_file, old_data, house_id, fallback)
    
    last_modified = datetime.strptime(
        last_modified_str, "%a, %d %b %Y %H:%M:%S %Z")
    if updated_at is not None:
        updated_at = datetime.strptime(
            updated_at, "%a, %d %b %Y %H:%M:%S %Z")
        # Compare last modified date with updated_at
        _LOGGER.debug("Last modified - %s", last_modified)
        _LOGGER.debug("Updated at - %s", updated_at)
        if last_modified <= updated_at:
            _LOGGER.debug("CSV file not updated since last check")
            return old_data
    
    if int(response.headers.get("Content-Length", 0)) == 0:
        _LOGGER.debug("CSV file is 0 bytes")
        return get_next_dates_from_cache(cache_csv_file, old_data, house_id, fallback)

    _LOGGER.info("Refreshing waste collection data - %s", house_id)
    try:
        response = requests.get(csv_url, timeout=200)
    except Exception as e:
        _LOGGER.error("Failed to fetch data from web - %s", e)
        return get_next_dates_from_cache(cache_csv_file, old_data, house_id, fallback)
    if response.status_code != 200:
        _LOGGER.debug("Failed to fetch CSV from the web")
        return get_next_dates_from_cache(cache_csv_file, old_data, house_id, fallback)
    csv_data = response.content
    wanted_ids = wanted_premises_ids(house_id, fallback)
    matching_rows = []
    count = 0
    csv_io = StringIO(csv_data.decode("utf-8"))
    csv_reader = csv.reader(csv_io)
    try:
        for row in csv_reader:
            if not row:
                continue
            if row[0] in wanted_ids:
                matching_rows.append(row)
            else:
                count += 1
    except csv.Error as err:
        # Leeds occasionally publish this file truncated and NUL-padded out to its
        # declared Content-Length. csv then reads the padding as one enormous field
        # and raises "field larger than field limit".
        #
        # The rows read before the error are individually valid, but everything after
        # the cut is missing - a collection whose row fell in the lost tail would
        # silently disappear and the bin would be missed. So the partial download is
        # discarded in favour of the cache, which is stale but complete.
        #
        # Returning rather than letting this propagate is the important part. The
        # coordinator only records updated_at and widens its poll interval after a
        # successful update, so an exception here left it re-downloading ~180MB every
        # 30 seconds for as long as the upstream file stayed broken.
        _LOGGER.warning(
            "Truncated CSV from Leeds open data (%s) - discarding the partial "
            "download and serving cached collection dates instead",
            err,
        )
        csv_io.close()
        return get_next_dates_from_cache(cache_csv_file, old_data, house_id, fallback)

    if not matching_rows:
        _LOGGER.error(
            "No rows for house %s in the downloaded CSV - falling back to cache",
            house_id,
        )
        csv_io.close()
        return get_next_dates_from_cache(cache_csv_file, old_data, house_id, fallback)
    # Write matching rows to the cache CSV file
    try:
        if os.path.exists(cache_csv_file):
            os.remove(cache_csv_file)
            _LOGGER.info("Deleted existing cache file: %s", cache_csv_file)
        with open(cache_csv_file, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerows(matching_rows)
            _LOGGER.info("Matching rows written to cache file: %s", cache_csv_file)
    except Exception as e:
        _LOGGER.error("Failed to write to cache file - %s", e)
        return old_data
    next_dates = build_next_dates(matching_rows, house_id, fallback)
    next_dates["updated_at"] = response.headers.get("Last-Modified")
    _LOGGER.info("Next Collection Dates: %s", next_dates)
    csv_io.close()
    return next_dates


def find_nearest_date(rows, color):
    """Find nearest bin dates."""
    matching_rows = [row for row in rows if row[1] == color]
    if not matching_rows:
        return None

    current_date = datetime.now()
    nearest_date = None

    for row in matching_rows:
        row_date = datetime.strptime(row[2], "%d/%m/%y")
        if row_date < current_date.replace(hour=0, minute=0, second=0, microsecond=0):
            continue

        time_difference = abs(current_date - row_date)
        if nearest_date is None or time_difference < nearest_date[1]:
            nearest_date = (row[2], time_difference)
    
    return nearest_date[0] if nearest_date else None


def wanted_premises_ids(house_id, fallback):
    """Premises whose collection rows are needed: the address plus any fallback ones."""
    ids = {house_id}
    if fallback:
        ids.update(p["id"] for p in fallback.get("premises", []))
    return ids


def _parse_date(value):
    return datetime.strptime(value, "%d/%m/%y")


def _house_number(premise):
    """The numeric part of a premises number, or None for named houses."""
    number = premise.get("number", "")
    return int(number) if number.isdigit() else None


def _describe(premise):
    label = premise.get("number") or premise.get("name") or premise["id"]
    return f"{label} {premise.get('street', '')}".strip()


def _most_common_then_earliest(candidates):
    """Pick the most frequent date, breaking ties with the earliest.

    candidates is a list of (premise, date_string).
    """
    counts = {}
    for _, date in candidates:
        counts[date] = counts.get(date, 0) + 1
    best = min(counts, key=lambda d: (-counts[d], _parse_date(d)))
    return next(c for c in candidates if c[1] == best)


def choose_fallback(own, candidates, mode):
    """Choose which neighbouring premises' date to use.

    own is this address's premises record (or None), candidates is a list of
    (premise, date_string) for other addresses that have a usable date.
    Returns the chosen (premise, date_string).
    """
    if mode == FALLBACK_EARLIEST:
        return min(candidates, key=lambda c: _parse_date(c[1]))
    if mode in (FALLBACK_NEAREST_SIDE, FALLBACK_NEAREST_SEQUENTIAL):
        own_number = _house_number(own) if own else None
        numbered = [c for c in candidates if _house_number(c[0]) is not None]
        if own_number is not None and numbered:
            pool = numbered
            if mode == FALLBACK_NEAREST_SIDE:
                # Odd/even numbers usually sit on opposite sides of the road.
                same_side = [
                    c for c in numbered if _house_number(c[0]) % 2 == own_number % 2
                ]
                pool = same_side or numbered
            nearest = min(abs(_house_number(c[0]) - own_number) for c in pool)
            tied = [c for c in pool if abs(_house_number(c[0]) - own_number) == nearest]
            return _most_common_then_earliest(tied)
    # Most common, and also where there is no house number to measure from.
    return _most_common_then_earliest(candidates)


def build_next_dates(rows, house_id, fallback=None):
    """Work out the next date for each bin colour from the collection rows."""
    next_dates = {colour: None for colour in BIN_COLOURS}
    rows_by_id = {}
    for row in rows:
        rows_by_id.setdefault(row[0], []).append(row)

    own_rows = rows_by_id.get(house_id, [])
    for colour in BIN_COLOURS:
        next_dates[colour] = find_nearest_date(own_rows, colour)

    if not fallback:
        return next_dates

    premises = {p["id"]: p for p in fallback.get("premises", [])}
    own = premises.get(house_id)
    configured_mode = fallback.get("mode", DEFAULT_FALLBACK_MODE)
    sources = {}
    for colour in BIN_COLOURS:
        if next_dates[colour]:
            continue
        mode = configured_mode
        candidates = []
        for premise_id, premise in premises.items():
            if premise_id == house_id:
                continue
            date = find_nearest_date(rows_by_id.get(premise_id, []), colour)
            if date:
                candidates.append((premise, date))
        if not candidates:
            continue
        # House numbers only mean something along one street, so prefer our own.
        if own:
            same_street = [c for c in candidates if c[0]["street"] == own["street"]]
            if same_street:
                candidates = same_street
            else:
                mode = FALLBACK_MOST_COMMON
        premise, date = choose_fallback(own, candidates, mode)
        next_dates[colour] = date
        sources[colour] = _describe(premise)
        _LOGGER.info(
            "No %s data for house %s - using %s (%s)",
            colour, house_id, sources[colour], mode,
        )
    if sources:
        next_dates["fallback_sources"] = sources
    return next_dates


def get_next_dates_from_cache(cache_csv, old_data, house_id, fallback=None):
    if not os.path.exists(cache_csv):
        _LOGGER.debug("Cache file does not exist: %s", cache_csv)
        return old_data
    wanted_ids = wanted_premises_ids(house_id, fallback)
    matching_rows = []
    with open(cache_csv, mode='r', newline='', encoding='utf-8') as file:
        for row in csv.reader(file):
            if row and row[0] in wanted_ids:
                matching_rows.append(row)
    next_dates = build_next_dates(matching_rows, house_id, fallback)
    next_dates["updated_at"] = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S %Z")
    _LOGGER.info("Next Collection Dates from cache: %s", next_dates)
    return next_dates

"""Leeds bins module."""

import csv, os
from datetime import datetime, timezone
from io import StringIO
import logging

import requests

_LOGGER = logging.getLogger(__name__)


def find_house_id(postcode, house):
    """Find house ID."""
    csv_url = "https://opendata.leeds.gov.uk/downloads/bins/dm_premises.csv"

    try:
        response = requests.get(csv_url, timeout=200)
        if response.status_code != 200:
            _LOGGER.debug("Failed to fetch CSV from the web")
            return None
        csv_data = response.content
        postcode = postcode.upper()
        csv_io = StringIO(csv_data.decode("utf-8"))
        csv_reader = csv.reader(csv_io)
        for row in csv_reader:
            if house.isdigit():
                column = 2
            else:
                column = 1
                house = house.upper()

            if row[column] == house and row[6] == postcode:
                csv_io.close()
                return row[0]
        csv_io.close()
        return None  # noqa: TRY300
    except Exception as e:
        _LOGGER.error("Error occurred: %s", e)
        return None


def find_bin_days(house_id, updated_at, old_data, cache_csv_file):
    """Find next bin days."""
    csv_url = "https://opendata.leeds.gov.uk/downloads/bins/dm_jobs.csv"
    try:
        response = requests.head(
            csv_url, timeout=200
        )  # Use HEAD request to fetch only headers
    except Exception as e:
        _LOGGER.error("Failed to fetch data from web - %s", e)
        return get_next_dates_from_cache(cache_csv_file, old_data, house_id)
    if response.status_code != 200:
        _LOGGER.debug("Failed to fetch CSV from the web")
        return get_next_dates_from_cache(cache_csv_file, old_data, house_id)
    
    last_modified_str = response.headers.get("Last-Modified")
    if not last_modified_str:
        _LOGGER.debug("Last-Modified header not found")
        return get_next_dates_from_cache(cache_csv_file, old_data, house_id)
    
    last_modified = datetime.strptime(
        last_modified_str, "%a, %d %b %Y %H:%M:%S %Z")
    if updated_at is not None:
        updated_at = datetime.strptime(
            updated_at, "%a, %d %b %Y %H:%M:%S %Z")
        # Compare last modified date with updated_at
        _LOGGER.debug("Last modified - %s", last_modified)
        _LOGGER.debug("Updated at - %s", last_modified)
        if last_modified <= updated_at:
            _LOGGER.debug("CSV file not updated since last check")
            return old_data
    
    if int(response.headers.get("Content-Length", 0)) == 0:
        _LOGGER.debug("CSV file is 0 bytes")
        return get_next_dates_from_cache(cache_csv_file, old_data, house_id)

    _LOGGER.info("Refreshing waste collection data - %s", house_id)
    try:
        response = requests.get(csv_url, timeout=200)
    except Exception as e:
        _LOGGER.error("Failed to fetch data from web - %s", e)
        return get_next_dates_from_cache(cache_csv_file, old_data, house_id)
    if response.status_code != 200:
        _LOGGER.debug("Failed to fetch CSV from the web")
        return get_next_dates_from_cache(cache_csv_file, old_data, house_id)
    csv_data = response.content
    next_dates = {"BROWN": None, "BLACK": None, "GREEN": None}
    matching_rows = []
    count = 0
    csv_io = StringIO(csv_data.decode("utf-8"))
    csv_reader = csv.reader(csv_io)
    for row in csv_reader:
        if row[0] == house_id:
            matching_rows.append(row)
        else:
            count += 1
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
    for color in ["BROWN", "BLACK", "GREEN"]:
        nearest_date = find_nearest_date(matching_rows, color)
        if nearest_date:
            next_dates[color] = nearest_date
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


def get_next_dates_from_cache(cache_csv, old_data, house_id):
    if not os.path.exists(cache_csv):
        _LOGGER.debug("Cache file does not exist: %s", cache_csv)
        return old_data
    csv_reader = csv.reader(cache_csv)
    next_dates = {"BROWN": None, "BLACK": None, "GREEN": None}
    matching_rows = []
    with open(cache_csv, mode='r', newline='', encoding='utf-8') as file:
        csv_reader = csv.reader(file)
        for row in csv_reader:
            if row[0] == house_id:
                matching_rows.append(row)
    for color in ["BROWN", "BLACK", "GREEN"]:
        nearest_date = find_nearest_date(matching_rows, color)
        if nearest_date:
            next_dates[color] = nearest_date
    next_dates["updated_at"] = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S %Z")
    _LOGGER.info("Next Collection Dates from cache: %s", next_dates)
    return next_dates

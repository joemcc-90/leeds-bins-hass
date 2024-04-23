# Leeds waste collection Home assistant integration

Welcome to Leeds waste collection Home asistant integration! This is an integration to get data from Leeds City Council in the UK and create sensors for each bin type.

## Table of Contents

- [Welcome](#welcome)
- [Installation](#installation)
- [Configuration](#configuration)
- [Automation Examples](#automation-examples)
- [Troubleshooting](#troubleshooting)

## Welcome

This integration adds 3 sensors to Home Assistant that displays data about next waste collection dates using an address in the leeds city council area.

Platform | Name | Description
-- | -- | --
`sensor` | Recycling bin | Show remaining days until recycling bin collection day
`sensor` | General Waste bin | Show remaining days until general waste bin collection day
`sensor` | Garden Waste bin | Show remaining days until garden waste bin collection day

Each sensor has the following attributes;

Attribute | Description
-- | --
Colour | Colour of the bin (i.e. GREEN, BLACK, BROWN)
Next collection | Date of the next collection
Days | Number of days until the next collection
Info URL | URL to Leeds City Council website with information on what to put in your bin

Dataset used provided by Data Mill North [Click here for more info](https://datamillnorth.org/dataset/ep6lz/household-waste-collections)

## Installation

This integration can be installed directly via HACS. To install:

* [Add the repository](https://my.home-assistant.io/redirect/hacs_repository/?owner=joemcc-90&repository=leeds-bins-hass&category=integration) to your HACS installation (If the link doesn't work go to `HACS` > `Integrationss` > `Custom Repositories` and add `https://github.com/joemcc-90/leeds-bins-hass` with category `Integration`)
* Click `Download` (bottom right)
* Restart Home Assistant

## Configuration

This integration is configured through the Home Assistant UI. You need your house name or number and postcode.

* Follow the steps in [Installation](#installation)
* Log in to Home Assistant web interface
* Go to - `Settings` > `Devices & Services` > `Integrations` > `ADD INTEGRATION`
* Search for and select `Leeds Waste Collection`
* Enter configuration information;

Configuration | Description
-- | --
`name` | Enter a friendly name for the configuration or leave blank (will affect sensor names (i.e. "Recycling bin" becomes "Friendly name - Recycling bin")) useful if monitoring multiple addresses
`house` | Enter house name or number
`postcode` | Enter postcode

## Automation Examples

To set up notifications, use a daily trigger with a condition which uses the days attribute. If days is 1 then bin is collected the following day.

Example;
```
alias: Bins - Green Bin
description: ""
trigger:
  - platform: time
    at: "19:00:00"
condition:
  - condition: state
    entity_id: sensor.leeds_bins_1234567_green_bin
    state: Tomorrow
action:
  - service: notify.mobile_app
    data:
      message: Recycling bin due out tomorrow
      title: Bins - Green Bin
mode: single
```

Example2;
```
alias: Bins - Green Bin
description: ""
trigger:
  - platform: time
    at: "07:00:00"
condition:
  - condition: state
    entity_id: sensor.leeds_bins_1234567_green_bin
    state: Today
action:
  - service: notify.mobile_app
    data:
      message: Recycling bin due out today
      title: Bins - Green Bin
mode: single
```


## Troubleshooting

* If the sensor state is "No collection" then this means there is no scheduled collection, please check the dataset - [Dataset](https://datamillnorth.org/dataset/ep6lz/household-waste-collections)
* To hide a sensor go to - `Settings` > `Devices & Services` > `Integrations` > `Leeds Waste Collection` > `Entities` and open the sensor you wish to hide. Use the `Visible` option to hide the sensor
* To enable debug logging go to - `Settings` > `Devices & Services` > `Integrations` > `Leeds Waste Collection` and select `Enable debug logging` 


## Issues

When you experience issues/bugs with this the best way to report them is to open an issue in this repo. Click here - [Issue link](https://github.com/joemcc-90/leeds-bins-hass/issues)

## Support

[BuyMe~~Coffee~~Beer?](https://buymeacoffee.com/joemcc90)

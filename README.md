# Leeds waste collection Home assistant integration

Welcome to Leeds waste collection Home asistant integration! This is an integration to get data from Leeds City Council in the UK and create sensors for each bin type.

## Table of Contents

- [Welcome](#welcome)
- [Installation](#installation)
- [Configuration](#configuration)
- [Automation Examples](#automation)
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

Dataset used provided by Data Mill North [Click here for more info](https://datamillnorth.org/dataset/ep6lz/household-waste-collections)

## Installation

This integration can be installed directly via HACS. To install:

* [Add the repository](https://my.home-assistant.io/redirect/hacs_repository/?owner=joemcc-90&repository=leeds-bins-hass&category=integration) to your HACS installation
* Click `Download`
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

Testing

## Troubleshooting

* If the sensor state is "No collection" then this means there is no scheduled collection, please check the dataset - [Dataset](https://datamillnorth.org/dataset/ep6lz/household-waste-collections)
* To enable debug logging go to - `Settings` > `Devices & Services` > `Integrations` > `Leeds Waste Collection` and select `Enable debug logging` 
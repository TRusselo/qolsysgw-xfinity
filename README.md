# Xfinity Gateway - `xfinitygw`

Xfinity Gateway (`xfinitygw`) is an [AppDaemon][appdaemon] automation that serves as a gateway between an Xfinity Cable Box and [Home Assistant][hass]. Xfinity Gateway works by establishing a connection to your Xfinity Cable Box and uses the [MQTT integration of Home Assistant][hass-mqtt]. It takes advantage of the [MQTT discovery][hass-mqtt-discovery] feature to declare the device as a media player and keep its state up to date, while providing you with the means to control your cable box directly from Home Assistant.

## Features

- Power control (on/off/toggle)
- Channel control (change channels)
- Volume control (up/down/mute)
- Real-time state updates
- Automatic device discovery in Home Assistant


- [How It Works](#how-it-works)
- [Requirements](#requirements)
- [Installation](#installation)
   - [Installing Home Assistant](#installing-home-assistant)
   - [Installing an MQTT Broker](#installing-an-mqtt-broker)
   - [Installing AppDaemon](#installing-appdaemon)
   - [Installing HACS (optional, recommended)](#installing-hacs-optional-recommended)
   - [Installing Xfinity Gateway](#installing-Xfinity-gateway)
      - [With HACS (recommended)](#with-hacs-recommended)
      - [Manually](#manually)
- [Configuration](#configuration)
   - [Configuring the MQTT integration in Home Assistant](#configuring-the-mqtt-integration-in-home-assistant)
   - [Configuring your Xfinity IQ Panel](#configuring-your-Xfinity-iq-panel)
   - [Configuring Xfinity Gateway](#configuring-Xfinity-gateway)
      - [Required configuration](#required-configuration)
      - [Optional configuration related to the Xfinity Panel itself](#optional-configuration-related-to-the-Xfinity-panel-itself)
      - [Optional configuration related to the representation of the panel in Home Assistant](#optional-configuration-related-to-the-representation-of-the-panel-in-home-assistant)
      - [Optional configuration related to MQTT & AppDaemon](#optional-configuration-related-to-mqtt--appdaemon)
- [Other documentation](#other-documentation)
- [Acknowledgements and thanks](#acknowledgements-and-thanks)


## How It Works

Xfinity Gateway is an [async application][asyncio] and has a few parallel
workflows:

1. The communication with the Xfinity Panel

   1. Xfinity Gateway connects to your Xfinity Panel using the configured
      information (hostname, token, port), thanks to a Control4 interface

   2. As soon as the connection is established, Xfinity Gateway requests
      from the panel the information on the current state of the panel,
      its partitions and sensors

   3. Xfinity Gateway listens for messages from the panel, and calls a
      callback method everytime a message can be parsed to an executable
      action; the callback will push that message in an MQTT thread _(that
      step is not mandatory but doing that loop allows to debug the
      application from Home Assistant by sending events directly in MQTT)_

   4. Every 4 minutes, a keep-alive message is sent to the connection,
      in order to avoid the panel from disconnecting Xfinity Gateway

2. The communications with MQTT

   1. Xfinity Gateway listens to an `event` topic, when a message is received,
      we update the state of the panel according to the event (it can be
      updating the sensors, the partitions or the panel itself). Messages in
      that topic are the messages that come from the Xfinity Panel, and that
      we intepret as change to the state of the panel. In general, with the
      update, we will trigger a few MQTT messages to be sent to update the
      status of the element at the source of the event in Home Assistant.

   2. Xfinity Gateway also listens to a `control` topic, when a message is
      received, we communicate the action to perform to the Xfinity Panel.
      Messages in that topic are coming from Home Assistant as reactions
      to service calls on the `alarm_control_panel` entities, or of manually
      configured actions. They can be used to arm or disarm the system,
      or even to trigger the alarm on the device.


## Requirements

- An Xfinity Cable Box with Control4 support enabled
- The Control4 token for your cable box
- Understanding that this automation is not part of the core of Home Assistant and is thus not officially supported by Home Assistant or Xfinity.


## Installation

Installing Xfinity Gateway requires the following steps.


### Installing Home Assistant

You can get to the [Home Assistant documentation for installation][hass-install]
page in order to setup Home Assistant for your needs.


### Installing an MQTT Broker

You will require a working MQTT broker alongside your Home Assistant
installation. Home Assistant provides [documentation on how to install
and configure an MQTT broker][hass-mqtt-broker].
If you wish to use MQTT through a docker deployment, you can use the
[`eclipse-mosquitto` docker image][mqtt-docker].
If you can, setup a username and password to secure your broker even more.


### Installing AppDaemon

Xfinity Gateway is an AppDaemon automation, which means it depends on a
working and running version of AppDaemon, connected to your Home Assistant.
You can find all the resources necessary in AppDaemon's documentation about
how to [install AppDaemon][appdaemon-install] and how to
[configure it with the HASS plugin][appdaemon-hass-plugin] for communicating
with Home Assistant, and [with the MQTT plugin][appdaemon-mqtt-plugin]
for communicating with your MQTT broker.

If you wish to use AppDaemon through a docker deployment, you can use the
[`acockburn/appdaemon` docker image][appdaemon-docker].

<details><summary>See an example of <code>appdaemon.yaml</code></summary>

```yaml
appdaemon:
  time_zone: "America/New_York" # Adapt this to your actual timezone

  # All three of those might be already filled for you, or you set the
  # values here, or use the secrets.yaml file to setup the values
  latitude: !secret latitude
  longitude: !secret longitude
  elevation: !secret elevation

  plugins:
    # If using the add-on in Home Assistant, that plugin will already be
    # enabled; when using the docker container, you will have to add it here
    HASS:
      type: hass
      ha_url: "http://homeassistant:8123"
      token: !secret ha_token # The token you get from home assistant

    # And we need to add the MQTT plugin
    MQTT:
      type: mqtt
      namespace: mqtt # We will need that same value in the apps.yaml configuration
      client_host: mosquitto # The IP address or hostname of the MQTT broker
      client_port: 1883 # The port of the MQTT broker, generally 1883

      # Only if you have setup an authenticated connection, otherwise skip those:
      client_user: appdaemon # The username
      client_password: !secret mqtt_password # The password
```
</details>


### Installing HACS (optional, recommended)

HACS is the Home Assistant Community Store and allows for community integrations and
automations to be updated cleanly and easily from the Home Assistant web user interface.
If it is simple to install Xfinity Gateway without HACS, keeping up to date requires
manual steps that HACS will handle for you: you will be notified of updates, and they
can be installed by a click on a button.

If you want to use HACS, you will have to follow [their documentation on how to install HACS][hacs-install].


### Installing Xfinity Gateway

Installing Xfinity Gateway is pretty simple once all the applications above
are setup. You can either follow the path using HACS (a bit more steps initially,
easier on the longer run) or use the manual setup approach.

#### With HACS (recommended)

To install Xfinity Gateway with HACS, you will need to make sure that you enabled
AppDaemon automations in HACS, as these are not enabled by default:

1. Click on `Configuration` on the left menu bar in Home Assistant Web UI
2. Select `Devices & Services`
3. Select `Integrations`
4. Find `HACS` and click on `Configure`
5. In the window that opens, make sure that `Enable AppDaemon apps discovery & tracking`
   is checked, or check it and click `Submit`
6. If you just enabled this (or just installed HACS), you might have to wait a few minutes
   as all repositories are being fetched; you might hit a GitHub rate limit, which might
   then require you to wait a few hours for HACS to be fully configured. In this case,
   you won't be able to proceed to the next steps until HACS is ready.

Now, to install Xfinity Gateway with HACS, follow these steps:

1. Click on `HACS` on the left menu bar in Home Assistant Web UI
2. Click on `Automations` in the right panel
3. Click on `Explore & download repositories` in the bottom right corner
4. Search for `Xfinitygw`, and click on `Xfinity Gateway` in the list that appears
5. In the bottom right corner of the panel that appears, click on
   `Download this repository with HACS`
6. A confirmation panel will appear, click on `Download`, and wait for HACS to
   proceed with the download
6. Xfinity Gateway is now installed, and HACS will inform you when updates are available


#### Manually

Installing Xfinity Gateway manually can be summarized by putting the content of the
`apps/` directory of this repository (the `Xfinitygw/` directory) into the `apps/`
directory of your AppDaemon installation.

For instance, if your Home Assistant configuration directory is in `/hass/config/`,
you most likely have AppDaemon setup in `/hass/config/appdaemon/`, and you can thus
put `Xfinitygw/` into `/hass/config/appdaemon/apps/`.


## Configuration

### Configuring the MQTT integration in Home Assistant

The MQTT integration of Home Assistant needs to be configured with your
MQTT broker in order for Xfinity Gateway to work. If you haven't setup the
MQTT integration yet, you can do so with the following steps:

1. Click on `Configuration` on the left menu bar in Home Assistant Web UI
2. Select `Devices & Services`
3. Select `Integrations`
4. Click on `Add Integration` in the bottom right corner
5. Search for `MQTT`, and click on the MQTT integration
6. Fill in the information as configured for your MQTT broker (hostname,
   port, and username and password if setting things up with an
   authenticated connection)
7. Click on `Submit`, Home Assistant will try and connect to the MQTT broker,
   and the integration will be setup upon success.


### Basic Configuration

The minimum configuration in your `apps.yaml` file:

```yaml
xfinity_box:
  module: gateway
  class: XfinityGateway
  box_host: <xfinity_box_host_or_ip>
  box_token: <control4_secure_token>
```

### Optional Configuration

Additional configuration options:

```yaml
xfinity_box:
  module: gateway
  class: XfinityGateway
  
  # Required
  box_host: 192.168.1.100
  box_token: your-control4-token
  
  # Optional - Box connection
  box_port: 12345                 # Default port for Control4
  box_mac: "aa:bb:cc:dd:ee:ff"   # MAC address of your box
  
  # Optional - MQTT settings
  mqtt_namespace: mqtt            # MQTT namespace in AppDaemon
  mqtt_retain: true              # Whether to retain MQTT messages
  
  # Optional - Topics
  discovery_topic: homeassistant # Home Assistant discovery prefix
  control_topic: custom/topic    # Custom control topic
  event_topic: custom/events     # Custom event topic
  
  # Optional - Device settings
  box_unique_id: living_room_box # Unique ID for the device
  box_device_name: Living Room TV # Name in Home Assistant
  
  # Optional - Control settings
  user_control_token: custom-token # Custom control token
  box_parental_code: 1234        # Parental control code if needed


## API Documentation

[Further API documentation and technical details to be added]

## Acknowledgements

This project uses the Control4 protocol capabilities of Xfinity Cable Boxes.

<!--
List of links used in that page, sorted alphabetically by tag
-->
[appdaemon]: https://github.com/AppDaemon/appdaemon
[appdaemon-install]: https://appdaemon.readthedocs.io/en/latest/INSTALL.html
[hacs-install]: https://hacs.xyz/docs/use
[hass-install]: https://www.home-assistant.io/installation/
[hass-mqtt]: https://www.home-assistant.io/integrations/mqtt/
[hass-mqtt-broker]: https://www.home-assistant.io/docs/mqtt/broker
[hass-mqtt-discovery]: https://www.home-assistant.io/docs/mqtt/discovery/
[mqtt-docker]: https://hub.docker.com/_/eclipse-mosquitto

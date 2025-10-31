import json
import logging

from appdaemon.plugins.mqtt.mqttapi import Mqtt

from xfinity.control import XfinityControl
from xfinity.events import XfinityEvent
from xfinity.exceptions import UnknownXfinityControlException
from xfinity.exceptions import UnknownXfinityEventException
from xfinity.utils import defaultLoggerCallback


LOGGER = logging.getLogger(__name__)


class MqttListener(object):
    def __init__(self, app: Mqtt, namespace: str, topic: str,
                 callback: callable = None, logger=None):
        self._callback = callback or defaultLoggerCallback
        self._logger = logger or LOGGER

        app.mqtt_subscribe(topic, namespace=namespace)
        app.listen_event(self.event_callback, event='MQTT_MESSAGE',
                         topic=topic, namespace=namespace)


class MqttXfinityEventListener(MqttListener):
    async def event_callback(self, event_name, data, kwargs):
        self._logger.debug(f'Received {event_name} with data={data} and kwargs={kwargs}')

        event_str = data.get('payload')
        if not event_str:
            self._logger.warning('Received empty event: {data}')
            return

        try:
            # We try to parse the event to one of our event classes
            event = XfinityEvent.from_json(event_str)
        except json.decoder.JSONDecodeError:
            self._logger.debug(f'Data is not JSON: {data}')
            return
        except UnknownXfinityEventException:
            self._logger.debug(f'Unknown Xfinity event: {data}')
            return

        try:
            await self._callback(event)
        except:  # noqa: E722
            self._logger.exception(f'Error calling callback for event: {event}')


class MqttXfinityControlListener(MqttListener):
    async def event_callback(self, event_name, data, kwargs):
        self._logger.debug(f'Received {event_name} with data={data} '
                           f'and kwargs={kwargs}')

        control_str = data.get('payload')
        if not control_str:
            self._logger.warning('Received empty control: {data}')
            return

        try:
            # We try to parse the event to one of our control classes
            control = XfinityControl.from_json(control_str)
        except json.decoder.JSONDecodeError:
            self._logger.debug(f'Data is not JSON: {data}')
            return
        except UnknownXfinityControlException:
            self._logger.debug(f'Unknown Xfinity control: {data}')
            return

        try:
            await self._callback(control)
        except:  # noqa: E722
            self._logger.exception(f'Error calling callback for control: {control}')
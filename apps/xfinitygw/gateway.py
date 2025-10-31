import logging
import traceback
import uuid

from appdaemon.plugins.mqtt.mqttapi import Mqtt

from mqtt.exceptions import MqttPluginUnavailableException
from mqtt.listener import MqttXfinityControlListener
from mqtt.listener import MqttXfinityEventListener
from mqtt.updater import MqttUpdater
from mqtt.updater import MqttWrapperFactory

from xfinity.config import XfinityGatewayConfig
from xfinity.control import XfinityControl
from xfinity.events import XfinityEvent
from xfinity.events import XfinityEventStatusChange
from xfinity.events import XfinityEventChannelChange
from xfinity.events import XfinityEventError
from xfinity.events import XfinityEventInfo
from xfinity.events import XfinityEventDeviceInfo
from xfinity.exceptions import InvalidUserCodeException
from xfinity.exceptions import MissingUserCodeException
from xfinity.socket import XfinitySocket
from xfinity.state import XfinityState


LOGGER = logging.getLogger(__name__)


class AppDaemonLoggingFilter(logging.Filter):
    def __init__(self, app, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._app = app

    def filter(self, record):
        record.app_name = self._app.name
        return True


class AppDaemonLoggingHandler(logging.Handler):
    def __init__(self, app):
        super().__init__()
        self._app = app

    def check_app(self, app):
        return self._app.name == app.name

    def emit(self, record):
        if hasattr(record, 'app_name') and record.app_name != self._app.name:
            return

        message = record.getMessage()
        if record.exc_info:
            message += '\nTraceback (most recent call last):\n'
            message += '\n'.join(traceback.format_tb(record.exc_info[2]))
            message += f'{record.exc_info[0].__name__}: {record.exc_info[1]}'
        self._app.log(message, level=record.levelname)


def fqcn(o):
    cls = o if type(o) == type else o.__class__  # noqa: E721
    mod = cls.__module__
    if mod == 'builtins':
        return cls.__qualname__
    return f'{mod}.{cls.__qualname__}'


def versiontuple(v):
    """
    Converts a semgrep version into a version tuple
    """
    v = v.split('-')[0]  # Remove any pre-release flag, we're not that smart
    return tuple(map(int, (v.split('.'))))


class XfinityGateway(Mqtt):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._xfinity_socket = None
        self._factory = None
        self._state = None
        self._redirect_logging()

    def _redirect_logging(self):
        rlogger = logging.getLogger()
        rlogger.handlers = [
            h for h in rlogger.handlers
            if (fqcn(h) != fqcn(AppDaemonLoggingHandler) or
                not hasattr(h, 'check_app') or not h.check_app(self))
        ]
        rlogger.addHandler(AppDaemonLoggingHandler(self))

        self._log_filter = AppDaemonLoggingFilter(self)
        LOGGER.addFilter(self._log_filter)

        rlogger.setLevel(logging.DEBUG)

    async def initialize(self):
        LOGGER.info('Starting')
        self._is_terminated = False

        cfg = self._cfg = XfinityGatewayConfig(self.args)

        # Handle the change in the function becoming sync vs. async
        ad_version = versiontuple(self.get_ad_version())
        async_removed = (ad_version >= (0, 17, 0) and ad_version < (0, 17, 2)) or \
            (ad_version >= (4, 5, 0) and ad_version < (4, 5, 3))
        if async_removed:
            mqtt_plugin_cfg = self.get_plugin_config(namespace=cfg.mqtt_namespace)
        else:
            mqtt_plugin_cfg = await self.get_plugin_config(namespace=cfg.mqtt_namespace)

        if mqtt_plugin_cfg is None:
            raise MqttPluginUnavailableException(
                'Unable to load the MQTT Plugin from AppDaemon, have you '
                'configured the MQTT plugin properly in appdaemon.yaml?')

        self._session_token = str(uuid.uuid4())

        self._factory = MqttWrapperFactory(
            mqtt_publish=self.mqtt_publish,
            cfg=cfg,
            mqtt_plugin_cfg=mqtt_plugin_cfg,
            session_token=self._session_token,
        )

        self._state = XfinityState()
        try:
            self._factory.wrap(self._state).set_unavailable()
        except:  # noqa: E722
            LOGGER.exception('Error setting state unavailable; pursuing')

        MqttUpdater(
            state=self._state,
            factory=self._factory
        )

        MqttXfinityEventListener(
            app=self,
            namespace=cfg.mqtt_namespace,
            topic=cfg.event_topic,
            callback=self.mqtt_event_callback,
        )

        MqttXfinityControlListener(
            app=self,
            namespace=cfg.mqtt_namespace,
            topic=cfg.control_topic,
            callback=self.mqtt_control_callback,
        )

        self._xfinity_socket = XfinitySocket(
            hostname=cfg.box_host,
            port=cfg.box_port,
            token=cfg.box_token,
            callback=self.xfinity_event_callback,
            connected_callback=self.xfinity_connected_callback,
            disconnected_callback=self.xfinity_disconnected_callback,
        )
        self.create_task(self._xfinity_socket.listen())
        self.create_task(self._xfinity_socket.keep_alive())

        LOGGER.info('Started')

    async def terminate(self):
        LOGGER.info('Terminating')

        if not self._state or not self._factory:
            LOGGER.info('No state or factory, nothing to terminate.')
            return

        self._factory.wrap(self._state).set_unavailable()

        self._is_terminated = True
        LOGGER.info('Terminated')

    async def xfinity_connected_callback(self):
        LOGGER.debug('Xfinity callback for connection event')
        self._factory.wrap(self._state).configure()

    async def xfinity_disconnected_callback(self):
        if self._is_terminated:
            return

        LOGGER.debug('Xfinity callback for disconnection event')
        self._factory.wrap(self._state).set_unavailable()

    async def xfinity_event_callback(self, event: XfinityEvent):
        LOGGER.debug(f'Xfinity callback for event: {event}')
        await self.mqtt_publish(
            namespace=self._cfg.mqtt_namespace,
            topic=self._cfg.event_topic,
            payload=event.raw_str,
        )

    async def mqtt_event_callback(self, event: XfinityEvent):
        LOGGER.debug(f'MQTT callback for event: {event}')

        if isinstance(event, XfinityEventDeviceInfo):
            self._state.update(event)

        elif isinstance(event, XfinityEventStatusChange):
            LOGGER.debug(f'Status change: {event.status}')
            self._state.update_status(event.status)

        elif isinstance(event, XfinityEventChannelChange):
            LOGGER.debug(f'Channel change: {event.channel}')
            self._state.update_channel(event.channel)

        elif isinstance(event, XfinityEventError):
            LOGGER.debug(f'ERROR: {event.error_description}')
            self._state.update_error(error_type=event.error_type,
                                   error_description=event.description)

        else:
            LOGGER.info(f'UNCAUGHT event {event}; ignored')

    async def mqtt_control_callback(self, control: XfinityControl):
        if control.session_token != self._session_token and (
                self._cfg.user_control_token is None or
                control.session_token != self._cfg.user_control_token):
            LOGGER.error(f'invalid session token for {control}')
            return

        if control.requires_config:
            control.configure(self._cfg, self._state)

        try:
            control.check()
        except (MissingUserCodeException, InvalidUserCodeException) as e:
            LOGGER.error(f'{e} for control event {control}')
            return

        action = control.action
        if action is None:
            LOGGER.info(f'Action missing for control event {control}')
            return

        await self._xfinity_socket.send(action)
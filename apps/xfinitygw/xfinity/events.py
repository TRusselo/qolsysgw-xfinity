import json
import logging
from typing import Dict, Optional, Type


LOGGER = logging.getLogger(__name__)


class XfinityEvent:
    EVENT_TYPE = None

    def __init__(self, raw_str: str = None):
        self.raw_str = raw_str

    @classmethod
    def from_json(cls, json_str: str) -> 'XfinityEvent':
        data = json.loads(json_str)
        event_type = data.get('event_type')
        
        if not event_type:
            raise UnknownXfinityEventException('No event_type in data')

        event_class = EVENT_TYPES.get(event_type.upper())
        if not event_class:
            raise UnknownXfinityEventException(f'Unknown event type: {event_type}')

        event = event_class()
        event.raw_str = json_str
        event._parse_json(data)
        return event

    def _parse_json(self, data: Dict):
        pass

    def __str__(self):
        return f'{self.__class__.__name__}()'


class XfinityEventDeviceInfo(XfinityEvent):
    EVENT_TYPE = 'DEVICE_INFO'

    def __init__(self):
        super().__init__()
        self.device_id = None
        self.model = None
        self.firmware = None
        self.mac_address = None

    def _parse_json(self, data: Dict):
        self.device_id = data.get('device_id')
        self.model = data.get('model')
        self.firmware = data.get('firmware')
        self.mac_address = data.get('mac_address')


class XfinityEventStatusChange(XfinityEvent):
    EVENT_TYPE = 'STATUS_CHANGE'

    def __init__(self):
        super().__init__()
        self.status = None

    def _parse_json(self, data: Dict):
        self.status = data.get('status')


class XfinityEventChannelChange(XfinityEvent):
    EVENT_TYPE = 'CHANNEL_CHANGE'

    def __init__(self):
        super().__init__()
        self.channel = None
        self.channel_name = None

    def _parse_json(self, data: Dict):
        self.channel = data.get('channel')
        self.channel_name = data.get('channel_name')


class XfinityEventError(XfinityEvent):
    EVENT_TYPE = 'ERROR'

    def __init__(self):
        super().__init__()
        self.error_type = None
        self.description = None

    def _parse_json(self, data: Dict):
        self.error_type = data.get('error_type')
        self.description = data.get('description')


class XfinityEventInfo(XfinityEvent):
    EVENT_TYPE = 'INFO'

    def __init__(self):
        super().__init__()
        self.info_type = None
        self.message = None

    def _parse_json(self, data: Dict):
        self.info_type = data.get('info_type')
        self.message = data.get('message')


EVENT_TYPES = {
    cls.EVENT_TYPE: cls
    for cls in XfinityEvent.__subclasses__()
    if cls.EVENT_TYPE is not None
}


class UnknownXfinityEventException(Exception):
    pass
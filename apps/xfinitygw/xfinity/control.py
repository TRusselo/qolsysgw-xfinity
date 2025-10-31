import json
import logging
from typing import Dict, Optional

from .config import XfinityGatewayConfig
from .state import XfinityState


LOGGER = logging.getLogger(__name__)


class XfinityControl:
    CONTROL_TYPE = None

    def __init__(self, raw_str: str = None):
        self.raw_str = raw_str
        self.session_token = None
        self._cfg = None
        self._state = None

    @property
    def requires_config(self) -> bool:
        return False

    def configure(self, cfg: XfinityGatewayConfig, state: XfinityState):
        self._cfg = cfg
        self._state = state

    @property
    def action(self) -> Optional[Dict]:
        return None

    def check(self):
        pass

    @classmethod
    def from_json(cls, json_str: str) -> 'XfinityControl':
        data = json.loads(json_str)
        control_type = data.get('control_type')
        
        if not control_type:
            raise UnknownXfinityControlException('No control_type in data')

        control_class = CONTROL_TYPES.get(control_type.upper())
        if not control_class:
            raise UnknownXfinityControlException(f'Unknown control type: {control_type}')

        control = control_class()
        control.raw_str = json_str
        control._parse_json(data)
        return control

    def _parse_json(self, data: Dict):
        self.session_token = data.get('session_token')

    def __str__(self):
        return f'{self.__class__.__name__}()'


class ChannelChangeControl(XfinityControl):
    CONTROL_TYPE = 'CHANNEL'

    def __init__(self):
        super().__init__()
        self.channel = None

    def _parse_json(self, data: Dict):
        super()._parse_json(data)
        self.channel = data.get('channel')

    @property
    def action(self) -> Optional[Dict]:
        if not self.channel:
            return None
        return {
            'action': 'set_channel',
            'channel': self.channel
        }


class VolumeControl(XfinityControl):
    CONTROL_TYPE = 'VOLUME'

    def __init__(self):
        super().__init__()
        self.volume_action = None  # up, down, mute

    def _parse_json(self, data: Dict):
        super()._parse_json(data)
        self.volume_action = data.get('volume_action')

    @property
    def action(self) -> Optional[Dict]:
        if not self.volume_action:
            return None
        return {
            'action': 'volume_control',
            'volume_action': self.volume_action
        }


class PowerControl(XfinityControl):
    CONTROL_TYPE = 'POWER'

    def __init__(self):
        super().__init__()
        self.power_action = None  # on, off, toggle

    def _parse_json(self, data: Dict):
        super()._parse_json(data)
        self.power_action = data.get('power_action')

    @property
    def action(self) -> Optional[Dict]:
        if not self.power_action:
            return None
        return {
            'action': 'power_control',
            'power_action': self.power_action
        }


CONTROL_TYPES = {
    cls.CONTROL_TYPE: cls
    for cls in XfinityControl.__subclasses__()
    if cls.CONTROL_TYPE is not None
}


class UnknownXfinityControlException(Exception):
    pass
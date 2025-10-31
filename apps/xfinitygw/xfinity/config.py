import logging
from typing import Dict, Optional


LOGGER = logging.getLogger(__name__)


class XfinityGatewayConfig:
    def __init__(self, args: Dict):
        # Box connection configuration
        self.box_host = args.get('box_host')
        if not self.box_host:
            raise ValueError('box_host is required')

        self.box_port = args.get('box_port', 12345)
        self.box_token = args.get('box_token')
        if not self.box_token:
            raise ValueError('box_token is required')
        
        self.box_mac = args.get('box_mac')  # Optional MAC address

        # MQTT configuration
        self.mqtt_namespace = args.get('mqtt_namespace', 'mqtt')
        self.mqtt_retain = args.get('mqtt_retain', True)

        # Topics configuration
        self.discovery_topic = args.get('discovery_topic', 'homeassistant')
        self.control_topic = args.get('control_topic',
                                    f'{self.discovery_topic}/media_player/{self.box_unique_id}/set')
        self.event_topic = args.get('event_topic',
                                  f'xfinity/{self.box_unique_id}/event')

        # Device configuration
        self.box_unique_id = args.get('box_unique_id', 'xfinity_box')
        self.box_device_name = args.get('box_device_name', 'Xfinity Box')

        # Control configuration
        self.user_control_token = args.get('user_control_token')

        # Box settings
        self._box_parental_code = args.get('box_parental_code')

    @property
    def box_parental_code(self) -> Optional[str]:
        return self._box_parental_code
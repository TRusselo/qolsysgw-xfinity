import logging
from typing import Dict, Optional


LOGGER = logging.getLogger(__name__)


class XfinityState:
    def __init__(self):
        self.device_id = None
        self.model = None
        self.firmware = None
        self.mac_address = None
        self.status = 'unavailable'
        self.current_channel = None
        self.current_channel_name = None
        self.is_muted = False
        self.volume_level = None
        self.last_error = None
        self.last_exception = None

    def update(self, event):
        """Update state from device info event"""
        self.device_id = event.device_id
        self.model = event.model
        self.firmware = event.firmware
        self.mac_address = event.mac_address

    def update_status(self, status: str):
        """Update power status"""
        self.status = status

    def update_channel(self, channel: str, channel_name: Optional[str] = None):
        """Update current channel"""
        self.current_channel = channel
        if channel_name:
            self.current_channel_name = channel_name

    def update_volume(self, is_muted: Optional[bool] = None, volume_level: Optional[int] = None):
        """Update volume status"""
        if is_muted is not None:
            self.is_muted = is_muted
        if volume_level is not None:
            self.volume_level = volume_level

    def update_error(self, error_type: str, error_description: str):
        """Update last error"""
        self.last_error = {
            'type': error_type,
            'description': error_description
        }

    def set_unavailable(self):
        """Mark device as unavailable"""
        self.status = 'unavailable'
"""
Support for RFXtrx lights.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/light.rfxtrx/
"""
import logging

import homeassistant.components.rfxtrx as rfxtrx
from homeassistant.const import STATE_ON, STATE_OFF
from homeassistant.components.light import (Light, ATTR_BRIGHTNESS,
                                            ATTR_TRANSITION)
from threading import Timer

DEPENDENCIES = ['rfxtrx']

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = rfxtrx.DEFAULT_SCHEMA


def setup_platform(hass, config, add_devices_callback, discovery_info=None):
    """Setup the RFXtrx platform."""
    import RFXtrx as rfxtrxmod

    lights = rfxtrx.get_devices_from_config(config, RfxtrxLight)
    add_devices_callback(lights)

    def light_update(event):
        """Callback for light updates from the RFXtrx gateway."""
        if not isinstance(event.device, rfxtrxmod.LightingDevice) or \
                not event.device.known_to_be_dimmable:
            return

        new_device = rfxtrx.get_new_device(event, config, RfxtrxLight)
        if new_device:
            add_devices_callback([new_device])

        rfxtrx.apply_received_command(event)

    # Subscribe to main rfxtrx events
    if light_update not in rfxtrx.RECEIVED_EVT_SUBSCRIBERS:
        rfxtrx.RECEIVED_EVT_SUBSCRIBERS.append(light_update)


class RfxtrxLight(rfxtrx.RfxtrxDevice, Light):
    """Represenation of a RFXtrx light."""

    @property
    def brightness(self):
        """Return the brightness of this light between 0..255."""
        return self._brightness

    def turn_on(self, **kwargs):
        """Turn the light on."""
        if self.transition_timer:
            self.transition_timer.cancel()
        brightness = kwargs.get(ATTR_BRIGHTNESS)
        transition = kwargs.get(ATTR_TRANSITION)

        if not brightness and not transition:
            self._brightness = 255
            self._send_command("turn_on")
            print("-----------aaaa")
            return
        elif not transition:
            self._brightness = brightness
            _brightness = (brightness * 100 // 255)
            self._send_command("dim", _brightness)
            print("-----------nnnnnn")
            return

        print("-----------vvvvvvvvvvvvvvvvvvvvvvvvvvvvv")
        if not brightness:
            brightness = 255
        if brightness < self._brightness:
            return
        if transition == 0:
            self.turn_on(brightness = brightness)
            return
        brightness_step = 1
        update_interval = transition/(brightness-self._brightness)
        self._transition_update(brightness_step, brightness, update_interval)

    def turn_off(self, **kwargs):
        """Turn the light off."""
        if self.transition_timer:
             self.transition_timer.cancel()
        transition = kwargs.get(ATTR_TRANSITION)
        if not transition or transition == 0:
            rfxtrx.RfxtrxDevice.turn_off(self, **kwargs)
            return

        brightness = kwargs.get(ATTR_BRIGHTNESS, 0)
        if brightness > self._brightness:
            return

        brightness_step = -1
        update_interval = transition/(self._brightness-brightness)
        self._transition_update(brightness_step, brightness, update_interval)

    def _transition_update(self, brightness_step, target_brightness, update_interval):
        self._brightness = self._brightness + brightness_step
        if self._brightness > 0:
            self.turn_on(brightness=self._brightness)
        else:
            self.turn_off()

        if self._brightness != target_brightness:
             args = (brightness_step, target_brightness, update_interval)
             self.transition_timer = \
             Timer(update_interval, self._transition_update, args).start()

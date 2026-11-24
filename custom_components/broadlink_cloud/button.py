"""Momentary command buttons for discovered virtual BroadLink remotes."""

from __future__ import annotations

import hashlib

import httpx
from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import BroadlinkCloudAPI, BroadlinkCloudError, Command
from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add one button per single-code cloud command."""

    client: BroadlinkCloudAPI = entry.runtime_data
    async_add_entities(BroadlinkCommandButton(client, cmd) for cmd in client.commands)


class BroadlinkCommandButton(ButtonEntity):
    """One momentary cloud action. Does not claim appliance on/off status."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:remote"

    def __init__(self, client: BroadlinkCloudAPI, command: Command):
        self._client = client
        self._command = command
        raw_id = (
            f"{command.family_id}/{command.remote_id}/"
            f"{command.position}/{command.name}"
        )
        self._attr_unique_id = hashlib.sha256(
            raw_id.encode("utf-8")
        ).hexdigest()[:32]
        self._attr_name = command.name
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{command.family_id}:{command.remote_id}")},
            name=command.remote_name,
            manufacturer="BroadLink",
            model="Cloud remote",
            via_device=(
                DOMAIN,
                f"{command.family_id}:{command.hub.endpoint_id}",
            ),
        )

    async def async_press(self) -> None:
        """Send one command; never retry on timeout to avoid double toggles."""

        try:
            await self.hass.async_add_executor_job(self._client.send_code, self._command)
        except (httpx.HTTPError, BroadlinkCloudError, ValueError) as exc:
            raise HomeAssistantError(
                "BroadLink Cloud could not confirm the command"
            ) from exc

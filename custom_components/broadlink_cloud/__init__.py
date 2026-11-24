"""Unofficial BroadLink Cloud integration for Home Assistant."""

from __future__ import annotations

import logging

import httpx
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr

from .api import BroadlinkCloudAPI, BroadlinkCloudError, BroadlinkLoginError
from .const import CONF_EMAIL, CONF_PASSWORD, DOMAIN, PLATFORMS

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Sign in and discover cloud commands without blocking the event loop."""

    client = BroadlinkCloudAPI()
    try:
        await hass.async_add_executor_job(
            client.login, entry.data[CONF_EMAIL], entry.data[CONF_PASSWORD]
        )
        hubs, commands = await hass.async_add_executor_job(client.discover)
    except BroadlinkLoginError as exc:
        await hass.async_add_executor_job(client.close)
        raise ConfigEntryAuthFailed("BroadLink Cloud login failed") from exc
    except (httpx.HTTPError, BroadlinkCloudError) as exc:
        await hass.async_add_executor_job(client.close)
        raise ConfigEntryNotReady("BroadLink Cloud unavailable") from exc
    except Exception:
        await hass.async_add_executor_job(client.close)
        raise

    entry.runtime_data = client
    registry = dr.async_get(hass)
    for hub in hubs:
        registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, f"{hub.family_id}:{hub.endpoint_id}")},
            manufacturer="BroadLink",
            name=hub.name,
            model="Cloud hub",
        )
    _LOGGER.info(
        "BroadLink Cloud ready: %s hub(s), %s command button(s)",
        len(hubs),
        len(commands),
    )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload platforms and close the cloud session."""

    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        client = entry.runtime_data
        await hass.async_add_executor_job(client.close)
    return unloaded

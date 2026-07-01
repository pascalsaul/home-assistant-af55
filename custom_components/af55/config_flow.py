"""Config flow for WNC AF55."""
from typing import Any
import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, OptionsFlow
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .api import Af55Client
from .const import *
from .exceptions import Af55AuthenticationError, Af55CannotConnect

class Af55ConfigFlow(ConfigFlow,domain=DOMAIN):
    VERSION=1
    async def async_step_user(self,user_input:dict[str,Any]|None=None):
        errors={}
        if user_input:
            c = Af55Client(
                async_get_clientsession(self.hass),
                user_input[CONF_HOST],
                user_input[CONF_USERNAME],
                user_input[CONF_PASSWORD],
                user_input[CONF_VERIFY_SSL],
            )
            try:
                await c.async_login()
                await c.async_get_status()
            except Af55AuthenticationError:
                errors["base"] = "invalid_auth"
            except Af55CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(user_input[CONF_HOST].lower())
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"WNC AF55 ({user_input[CONF_HOST]})",
                    data={
                        CONF_HOST: user_input[CONF_HOST],
                        CONF_USERNAME: user_input[CONF_USERNAME],
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                    },
                    options={
                        CONF_VERIFY_SSL: user_input[CONF_VERIFY_SSL],
                        CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
                    },
                )
            finally:
                await c.async_logout()
        schema=vol.Schema({
            vol.Required(CONF_HOST,default=(user_input or {}).get(CONF_HOST,DEFAULT_HOST)):str,
            vol.Required(CONF_USERNAME,default=(user_input or {}).get(CONF_USERNAME,DEFAULT_USERNAME)):str,
            vol.Required(CONF_PASSWORD):str,
            vol.Required(CONF_VERIFY_SSL,default=(user_input or {}).get(CONF_VERIFY_SSL,DEFAULT_VERIFY_SSL)):bool})
        return self.async_show_form(step_id="user",data_schema=schema,errors=errors)
    async def async_step_reauth(self,entry_data):
        self._entry=self.hass.config_entries.async_get_entry(self.context["entry_id"])
        return await self.async_step_reauth_confirm()
    async def async_step_reauth_confirm(self,user_input=None):
        errors={}
        if user_input:
            c = Af55Client(
                async_get_clientsession(self.hass),
                self._entry.data[CONF_HOST],
                self._entry.data[CONF_USERNAME],
                user_input[CONF_PASSWORD],
                self._entry.options.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL),
            )
            try:
                await c.async_login()
            except Af55AuthenticationError:
                errors["base"] = "invalid_auth"
            except Af55CannotConnect:
                errors["base"] = "cannot_connect"
            else:
                return self.async_update_reload_and_abort(
                    self._entry,
                    data_updates={CONF_PASSWORD: user_input[CONF_PASSWORD]},
                )
            finally:
                await c.async_logout()
        return self.async_show_form(step_id="reauth_confirm",data_schema=vol.Schema({vol.Required(CONF_PASSWORD):str}),errors=errors)
    @staticmethod
    def async_get_options_flow(config_entry): return Af55OptionsFlow(config_entry)

class Af55OptionsFlow(OptionsFlow):
    def __init__(self,entry): self._entry=entry
    async def async_step_init(self,user_input=None):
        if user_input is not None: return self.async_create_entry(title="",data=user_input)
        return self.async_show_form(step_id="init",data_schema=vol.Schema({
            vol.Required(CONF_SCAN_INTERVAL,default=self._entry.options.get(CONF_SCAN_INTERVAL,DEFAULT_SCAN_INTERVAL)):
                vol.All(vol.Coerce(int),vol.Range(min=MIN_SCAN_INTERVAL,max=MAX_SCAN_INTERVAL)),
            vol.Required(CONF_VERIFY_SSL,default=self._entry.options.get(CONF_VERIFY_SSL,DEFAULT_VERIFY_SSL)):bool}))

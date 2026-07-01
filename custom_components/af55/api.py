"""Async local API client for the WNC AF55."""
from __future__ import annotations
import asyncio, random
from typing import Any
from aiohttp import ClientError, ClientResponseError, ClientSession, ClientTimeout
from yarl import URL
from .aes import encode_password
from .exceptions import Af55ApiError, Af55AuthenticationError, Af55CannotConnect

class Af55Client:
    def __init__(self, session: ClientSession, host: str, username: str, password: str, verify_ssl: bool=False):
        self._session=session; self._host=host.strip().rstrip("/")
        self._username=username; self._password=password; self._verify_ssl=verify_ssl
        self._token=None; self._cgisid=None; self._lock=asyncio.Lock()
        self._device_metadata: dict[str, Any] = {}
        self._base=self._host if self._host.startswith(("http://","https://")) else f"https://{self._host}"
    @property
    def host(self): return self._host
    async def async_login(self):
        async with self._lock: await self._login_unlocked()
    async def _login_unlocked(self):
        try:
            await self._post_login("get_web_user_login_valid", {"action":"get_web_user_login_valid","args":{}}, True)
        except Af55ApiError:
            pass
        response=await self._post_login("set_web_user_login", {
            "action":"set_web_user_login",
            "args":{"user":self._username,"password":encode_password(self._password)}
        })
        result=response.get("set_web_user_login",{})
        if int(result.get("errno",-1)) != 0:
            message = str(result.get("errmsg", "Login failed"))
            raise Af55AuthenticationError(message)
        await self._refresh_token_unlocked()
    async def _refresh_token_unlocked(self):
        response=await self._post_login("get_web_user_login_valid", {"action":"get_web_user_login_valid","args":{}})
        result=response.get("get_web_user_login_valid",{})
        if int(result.get("errno",-1)) != 0 or int(result.get("login_hint",0)) != 1:
            raise Af55AuthenticationError(str(result.get("errmsg","Session invalid")))
        token=result.get("cgitoken")
        if not token: raise Af55AuthenticationError("No CGI token returned")
        self._device_metadata = {
            key: result.get(key)
            for key in (
                "product",
                "hostname",
                "customer",
                "bridge_mode",
                "lan_ip",
                "lang",
                "group",
            )
            if result.get(key) is not None
        }
        self._token=str(token)
    async def async_logout(self) -> None:
        """Log out the current AF55 administrator session."""
        async with self._lock:
            if not self._cgisid:
                return
            try:
                await self._post_login(
                    "set_web_user_logout",
                    {
                        "action": "set_web_user_logout",
                        "args": {"user": self._username},
                    },
                    True,
                )
            except (Af55ApiError, Af55AuthenticationError, Af55CannotConnect):
                pass
            finally:
                self._token = None
                self._cgisid = None

    async def async_reset_session(self) -> None:
        """Forget the local session without sending a request to the modem."""
        async with self._lock:
            self._token = None
            self._cgisid = None

    async def async_get_status(self):
        return await self._gui("get_web_status_bar")
    async def async_get_connection_time(self):
        data = await self._gui("get_wwan_ipv4_network_connection_time")
        return data.get("connection_time")

    @property
    def device_metadata(self) -> dict[str, Any]:
        """Return metadata learned during login."""
        return dict(self._device_metadata)

    async def async_reboot(self) -> None:
        """Reboot the AF55 using the confirmed local web API action."""
        async with self._lock:
            if not self._token:
                await self._login_unlocked()

            action = "set_system_wan_power"
            payload = {
                "action": action,
                "args": {"reboot": 1},
                "token": self._token,
            }

            try:
                response = await self._post("/cgi-bin/gui.cgi", action, payload)
            except Af55CannotConnect:
                # The modem may drop the HTTP connection as soon as reboot starts.
                self._token = None
                self._cgisid = None
                return

            result = response.get(action)
            if not isinstance(result, dict):
                raise Af55ApiError(
                    "AF55 reboot response did not include set_system_wan_power"
                )

            errno = int(result.get("errno", -1))
            if errno != 0:
                raise Af55ApiError(
                    str(result.get("errmsg", "AF55 reboot command was rejected"))
                )

            self._token = None
            self._cgisid = None

    async def _gui(self, action: str) -> dict[str,Any]:
        async with self._lock:
            if not self._token: await self._login_unlocked()
            try:
                response=await self._post("/cgi-bin/gui.cgi",action,{"action":action,"token":self._token})
            except Af55AuthenticationError:
                self._token=None; await self._login_unlocked()
                response=await self._post("/cgi-bin/gui.cgi",action,{"action":action,"token":self._token})
            result=response.get(action)
            if not isinstance(result,dict):
                raise Af55ApiError(f"Missing '{action}' in response")
            errno=int(result.get("errno",0))
            if errno:
                msg=str(result.get("errmsg","AF55 API error"))
                if "login" in msg.lower() or "token" in msg.lower(): raise Af55AuthenticationError(msg)
                raise Af55ApiError(msg)
            return result
    async def _post_login(self, action, payload, allow_auth_error=False):
        response=await self._post("/cgi-bin/login.cgi",action,payload)
        result=response.get(action)
        if isinstance(result,dict) and int(result.get("errno",0)) != 0:
            msg=str(result.get("errmsg","Login API error"))
            if allow_auth_error: raise Af55ApiError(msg)
            raise Af55AuthenticationError(msg)
        return response
    async def _post(self,path,action,payload):
        url=URL(f"{self._base}{path}").with_query({"_":f"{action}_{random.random()}"})
        headers={"Accept":"application/json, text/javascript, */*; q=0.01","Content-Type":"json",
                 "X-Requested-With":"XMLHttpRequest","Origin":self._base,"Referer":f"{self._base}/"}
        try:
            cookies={"CGISID": self._cgisid} if self._cgisid else None
            async with self._session.post(url,json=payload,headers=headers,cookies=cookies,
                                          ssl=self._verify_ssl,timeout=ClientTimeout(total=15)) as response:
                response.raise_for_status()
                if "CGISID" in response.cookies:
                    self._cgisid=response.cookies["CGISID"].value
                data=await response.json(content_type=None)
        except (ClientError, asyncio.TimeoutError, ValueError) as err:
            if isinstance(err,ClientResponseError) and err.status in (401,403):
                raise Af55AuthenticationError("Session rejected") from err
            raise Af55CannotConnect(f"Unable to reach AF55 at {self._host}") from err
        if not isinstance(data,dict): raise Af55ApiError("Non-object response")
        if int(data.get("errno",0)) != 0:
            msg=str(data.get("errmsg","AF55 API error"))
            if "login" in msg.lower() or "token" in msg.lower(): raise Af55AuthenticationError(msg)
            raise Af55ApiError(msg)
        return data

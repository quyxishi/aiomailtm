from typing import Any, Callable, Dict, List, Self, TypeVar, Optional
from asyncio import AbstractEventLoop
from importlib.abc import Traversable
from aiohttp import ClientResponse
from dataclasses import dataclass
from importlib import resources
from inspect import FrameInfo
from datetime import datetime
from pathlib import Path
import aiofiles
import aiohttp
import asyncio
import inspect
import random
import orjson
import string
import time

from .__version__ import __title__, __version__
from .recli import recli
from . import wordlists


_T = TypeVar('_T')


@dataclass
class Subject:
    address: str
    name: str

    @staticmethod
    def from_dict(__dict: Dict[str, Any]) -> Self:
        return Subject(
            address=__dict.get('address') or '', name=__dict.get('name') or ''
        )


@dataclass
class Message:
    _id: str
    message_id: str
    message_from: Subject
    message_to: Subject
    message_cc: List[Subject]
    message_bcc: List[Subject]
    subject: str
    intro: str
    seen: bool
    flagged: bool
    is_deleted: bool
    retention: bool
    retention_date: datetime
    text: str
    html: List[str]
    has_attachments: bool
    size: int
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def from_dict(__dict: Dict[str, Any]) -> Self:
        # fmt: off
        try:
            retention_date: datetime = datetime.fromisoformat(
                __dict.get('retentionDate') or ''
            )
        except ValueError:
            retention_date = datetime.fromtimestamp(0)

        try:
            created_at: datetime = datetime.fromisoformat(
                __dict.get('createdAt') or ''
            )
        except ValueError:
            created_at = datetime.fromtimestamp(0)

        try:
            updated_at: datetime = datetime.fromisoformat(
                __dict.get('updatedAt') or ''
            )
        except ValueError:
            updated_at = datetime.fromtimestamp(0)
        # fmt: on

        return Message(
            _id=str(object=__dict.get('id') or ''),
            message_id=str(object=__dict.get('msgid') or ''),
            message_from=Subject.from_dict(__dict.get('from') or {}),
            message_to=list(
                [Subject.from_dict(__d or {}) for __d in (__dict.get('to') or [])]
            ),
            message_cc=list(
                [Subject.from_dict(__d or {}) for __d in (__dict.get('cc') or [])]
            ),
            message_bcc=list(
                [Subject.from_dict(__d or {}) for __d in (__dict.get('bcc') or [])]
            ),
            subject=str(object=__dict.get('subject') or ''),
            intro=str(object=__dict.get('intro') or ''),
            seen=bool(__dict.get('seen') or False),
            flagged=bool(__dict.get('flagged') or False),
            is_deleted=bool(__dict.get('isDeleted') or False),
            retention=bool(__dict.get('retention') or False),
            retention_date=retention_date,
            text=str(object=__dict.get('text') or ''),
            html=str(object=__dict.get('html') or []),
            has_attachments=bool(__dict.get('hasAttachments') or False),
            size=int(__dict.get('size') or 0),
            created_at=created_at,
            updated_at=updated_at,
        )


@dataclass
class Account:
    address: str
    password: str

    def __str__(self) -> str:
        return ':'.join([self.address, self.password])


class AioMailtmClient:
    """
    Base client of Mail.tm API

    Usage
    -----

    ```
    >>> def simple_callback(message: Message) -> str:
    >>>     return message.subject

    >>> client = AioMailtmClient()

    >>> account: Optional[Account] = await client.create_account()
    >>> assert account
    >>> print(account.address)

    >>> mail_subject: Optional[str] = await client.listen_messages(callback=simple_callback)
    >>> print(mail_subject)
    ```
    """

    _recli_debug: bool = False

    _api_endpoint: str = 'https://api.mail.tm'

    _http_headers: Dict[str, str] = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'User-Agent': f'{__title__}/{__version__}',
    }

    _api_minor_delay: float = 0.25
    _api_major_delay: float = 15.0
    _api_retry: int = 0

    _mail_address: Optional[str] = None
    _mail_password: Optional[str] = None
    _mail_token: Optional[str] = None

    def __init__(self, recli_debug: bool = False) -> None:
        """Mail.tm API Client constructor"""

        self._recli_debug = recli_debug
        self._aiohttp_session = aiohttp.ClientSession(
            base_url=self._api_endpoint, headers=self._http_headers, json_serialize=None
        )

    def __del__(self) -> None:
        try:
            event_loop: AbstractEventLoop = asyncio.get_event_loop()
        except RuntimeError:
            event_loop: AbstractEventLoop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop=event_loop)
        finally:
            if event_loop.is_running():
                event_loop.create_task(coro=self._aiohttp_session.close())
            else:
                event_loop.run_until_complete(future=self._aiohttp_session.close())

    def _recli_proxy(self, __method: str, __msg: str, *__args, **__kwargs) -> None:
        if not self._recli_debug:
            return None

        recli.__getattribute__(recli, __method)(f'~<{__title__}>~: ' + __msg, *__args, **__kwargs)

    def _rassert(self, __expr: Any) -> bool:
        """Perform reverse assertion on `__expr`"""

        frame: FrameInfo = inspect.stack()[1]
        return (
            False
            if __expr
            else self._recli_proxy(
                'warn',
                f'~<{Path(frame.filename).name}:{frame.lineno}>~ *has failed the assertion*',
            )
            or True
        )

    @staticmethod
    async def _fixed_sleep(__delay: float) -> None:
        entry_time: float = time.time()
        exit_time: float = entry_time + __delay

        while entry_time <= exit_time:
            await asyncio.sleep(delay=0.01)
            entry_time = time.time()

    @staticmethod
    def _process_url(__url: str) -> str:
        return '/' + '/'.join(__url.split('/')[3:])

    async def _request(self, __method: str, __url: str, **__kwargs) -> ClientResponse:
        await self._fixed_sleep(self._api_minor_delay)

        response: ClientResponse = await self._aiohttp_session.__getattribute__(
            __method.lower()
        )(url=__url, **__kwargs)

        if response.status == 429:
            self._api_retry += 1
            delay: float = self._api_major_delay * self._api_retry

            self._recli_proxy(
                'info',
                f'too many requests · #{self._api_retry} for {delay:.1f}s',
            )

            await self._fixed_sleep(delay)
            return await self._request(__method, __url, **__kwargs)
        elif not 200 <= response.status <= 204:
            self._recli_proxy(
                'warn',
                f'<{self._process_url(response.url.__str__())}> *returned unexpected response* ~<{response.status}>~',
            )

        self._api_retry = 1
        return response

    @staticmethod
    async def _generate_login() -> str:
        digits_count: int = random.randint(a=2, b=6)
        digits_side: bool = bool(random.randint(a=0, b=1))

        digits: str = ''.join(
            [random.choice(string.digits) for _ in range(digits_count)]
        )
        login: str = digits if not digits_side else ''

        delimiter: str = random.choice(seq=['', '.', '_'])

        adjectives_file: Traversable = resources.files(wordlists) / 'adjectives.txt'
        nouns_file: Traversable = resources.files(wordlists) / 'nouns.txt'

        async with aiofiles.open(file=adjectives_file, mode='r', encoding='utf-8') as f:
            login += random.choice(seq=await f.readlines()).strip()

        login += delimiter

        async with aiofiles.open(file=nouns_file, mode='r', encoding='utf-8') as f:
            login += random.choice(seq=await f.readlines()).strip()

        if digits_side:
            login += digits

        return login

    def _handle_api_error(self, __error_response: Any) -> bool:
        if not isinstance(__error_response, Dict):
            return False

        __error_response: Dict[str, str] = dict(__error_response)
        response_keys: List[str] = list(__error_response.keys())

        if not ('violations' in response_keys or 'detail' in response_keys):
            return False

        return (
            self._recli_proxy(
                'error', f'<api>: {__error_response["detail"]}'
            )
            or True
        )

    def _bearer_header(self) -> Dict[str, str]:
        return {'Authorization': 'Bearer ' + (self._mail_token or '?')}

    async def _retrieve_domains(self) -> Optional[List[str]]:
        domains_response: ClientResponse = await self._request('GET', '/domains')
        domains_bytes: bytes = await domains_response.read()

        if self._rassert(domains_bytes):
            return None

        try:
            domains_serialize: Optional[List[Dict[str, str]]] = orjson.loads(
                domains_bytes
            )
        except orjson.JSONDecodeError:
            self._recli_proxy(
                'warn', '</domains> *does not contains valid json*'
            )
            return None

        # fmt: off
        if self._handle_api_error(domains_serialize) \
        or self._rassert(isinstance(domains_serialize, List)):
            return None
        # fmt: on

        return [domain['domain'] for domain in domains_serialize if domain['isActive']]

    async def create_account(
        self, login: Optional[str] = None, password: Optional[str] = None
    ) -> Optional[Account]:
        login: str = login or await self._generate_login()
        password: str = password or ''.join(
            [random.choice(string.ascii_letters + string.digits) for _ in range(18)]
        )

        domains: Optional[List[str]] = await self._retrieve_domains()

        if self._rassert(domains):
            return None

        accounts_data: Dict[str, str] = {
            'address': login + '@' + random.choice(seq=domains),
            'password': password,
        }

        accounts_response: ClientResponse = await self._request(
            'POST', '/accounts', data=orjson.dumps(accounts_data)
        )
        accounts_bytes: bytes = await accounts_response.read()

        if self._rassert(accounts_bytes):
            return None

        try:
            accounts_serialize: Optional[Dict[str, str]] = orjson.loads(accounts_bytes)
        except orjson.JSONDecodeError:
            self._recli_proxy(
                'warn', '</accounts> *does not contains valid json*'
            )
            return None

        # fmt: off
        if self._handle_api_error(accounts_serialize) \
        or self._rassert(isinstance(accounts_serialize, Dict)):
            return None
        # fmt: on

        self._mail_address = accounts_serialize['address']
        self._mail_password = password

        return Account(address=self._mail_address, password=self._mail_password)

    async def _retrieve_token(self) -> None:
        if self._rassert(self._mail_address) or self._rassert(self._mail_password):
            return None

        token_data: Dict[str, str] = {
            'address': self._mail_address,
            'password': self._mail_password,
        }

        token_response: ClientResponse = await self._request(
            'POST', '/token', data=orjson.dumps(token_data)
        )
        token_bytes: bytes = await token_response.read()

        if self._rassert(token_bytes):
            return None

        try:
            token_serialize: Optional[Dict[str, str]] = orjson.loads(token_bytes)
        except orjson.JSONDecodeError:
            self._recli_proxy(
                'warn', '</token> *does not contains valid json*'
            )
            return None

        # fmt: off
        if self._handle_api_error(token_serialize) \
        or self._rassert(isinstance(token_serialize, Dict)):
            return None
        # fmt: on

        self._mail_token = token_serialize['token']

    async def _retrieve_messages(self) -> Optional[List[Dict[str, Any]]]:
        if not self._mail_token:
            await self._retrieve_token()

            if self._rassert(self._mail_token):
                return None

        messages_response: ClientResponse = await self._request(
            'GET', '/messages', headers=self._bearer_header()
        )
        messages_bytes: bytes = await messages_response.read()

        if self._rassert(messages_bytes):
            return None

        try:
            messages_serialize: Optional[List[Dict[str, Any]]] = orjson.loads(
                messages_bytes
            )
        except orjson.JSONDecodeError:
            self._recli_proxy(
                'warn', '</messages> *does not contains valid json*'
            )
            return None

        # fmt: off
        if self._handle_api_error(messages_serialize) \
        or self._rassert(isinstance(messages_serialize, List)):
            return None
        # fmt: on

        return messages_serialize

    async def _retrieve_message(self, __id: str) -> Optional[Dict[str, Any]]:
        if not self._mail_token:
            await self._retrieve_token()

            if self._rassert(self._mail_token):
                return None

        message_response: ClientResponse = await self._request(
            'GET', f'/messages/{__id}', headers=self._bearer_header()
        )
        message_bytes: bytes = await message_response.read()

        if self._rassert(message_bytes):
            return None

        try:
            message_serialize: Optional[Dict[str, Any]] = orjson.loads(message_bytes)
        except orjson.JSONDecodeError:
            self._recli_proxy(
                'warn',
                f'</messages/{__id}> *does not contains valid json*',
            )
            return None

        # fmt: off
        if self._handle_api_error(message_serialize) \
        or self._rassert(isinstance(message_serialize, Dict)):
            return None
        # fmt: on

        return message_serialize

    async def listen_messages(
        self,
        callback: Callable[[Message], Optional[_T]],
        polling_timeout: float = 60.0,
        polling_delay: float = 5.0,
    ) -> Optional[_T]:
        """
        Listens for new messages and executes a callback on each,
        passing the :class:`Message` as a parameter.

        Continues, if callback return is not `None`

        Returns `None` on a timeout
        """

        if self._rassert(callback):
            return None

        entry_time: float = time.time()
        exit_time: float = entry_time + polling_timeout

        processed_ids: List[str] = []

        while entry_time <= exit_time:
            messages: Optional[List[Dict[str, Any]]] = await self._retrieve_messages()

            if self._rassert(isinstance(messages, List)):
                return None

            for message in messages:
                if message['id'] in processed_ids:
                    continue

                message: Optional[Dict[str, Any]] = await self._retrieve_message(
                    message['id']
                )

                if self._rassert(message):
                    continue

                callback_return: Optional[_T] = callback(Message.from_dict(message))

                if callback_return is not None:
                    return callback_return

                processed_ids.append(message['id'])

            await self._fixed_sleep(polling_delay)
            entry_time = time.time()

        return None

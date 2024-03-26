# aiomailtm
> Asynchronous & exception-less implementation of [Mail.tm API](https://docs.mail.tm/)

## Installation
```shell
pip install --upgrade git+https://github.com/quyxishi/aiomailtm@main
```

## Usage
```python
from aiomailtm import AioMailtmClient, Message, Account
from typing import Optional
import asyncio


def simple_callback(message: Message) -> str:
    return message.subject


async def main() -> None:
    client = AioMailtmClient()

    account: Optional[Account] = await client.create_account()
    assert account
    print(account)

    mail_subject: str = await client.listen_messages(callback=simple_callback)
    print(mail_subject)


if __name__ == '__main__':
    asyncio.run(main=main())
```

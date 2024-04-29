from typing import Any, Dict, List, Self
from dataclasses import dataclass
from datetime import datetime


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

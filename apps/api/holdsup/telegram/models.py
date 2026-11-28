"""The few fields of a Telegram update the bot reads (Bot API `Update`); the rest is ignored."""

from pydantic import BaseModel, ConfigDict, Field


class User(BaseModel):
    id: int
    is_bot: bool = False


class Chat(BaseModel):
    id: int
    type: str  # "private", "group", "supergroup" or "channel"


class Message(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    message_id: int
    chat: Chat
    sender: User | None = Field(default=None, alias="from")
    text: str | None = None
    caption: str | None = None  # the text under a photo or a file


class Update(BaseModel):
    update_id: int
    message: Message | None = None  # None for every other kind (edits, channel posts…)

from datetime import datetime

from pydantic import BaseModel, Field


class AuthSendCodeRequest(BaseModel):
    phone: str | None = None


class AuthVerifyCodeRequest(BaseModel):
    phone: str | None = None
    code: str
    password: str | None = None


class PasswordRequest(BaseModel):
    password: str


class UserInfo(BaseModel):
    id: int
    username: str | None = None
    phone: str | None = None
    first_name: str | None = None
    last_name: str | None = None


class AuthStatusResponse(BaseModel):
    configured: bool
    authorized: bool
    phone_hint: str | None = None
    user: UserInfo | None = None
    selected_channels: list[str]


class AuthMethodsResponse(BaseModel):
    code: bool
    qr: bool


class AppConfigResponse(BaseModel):
    api_title: str
    api_version: str
    public_api_url: str
    selected_channels: list[str]
    auth_methods: AuthMethodsResponse
    docs_url: str
    health_url: str


class ReactionInfo(BaseModel):
    key: str
    count: int
    type: str


class MessageSource(BaseModel):
    channel_id: int
    title: str
    username: str | None = None
    requested_as: str


class ParsedMessage(BaseModel):
    id: int
    text: str
    date: datetime
    views: int | None = None
    forwards: int | None = None
    post_author: str | None = None
    url: str | None = None
    like_count: int | None = None
    dislike_count: int | None = None
    reactions: list[ReactionInfo] = Field(default_factory=list)
    source: MessageSource


class ChannelParseResult(BaseModel):
    requested_as: str
    title: str | None = None
    username: str | None = None
    status: str
    error: str | None = None
    messages: list[ParsedMessage] = Field(default_factory=list)


class ParseResponse(BaseModel):
    authorized: bool
    count: int
    channels: list[str]
    items: list[ParsedMessage]
    results: list[ChannelParseResult]

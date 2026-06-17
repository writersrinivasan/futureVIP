from contextvars import ContextVar

# Set per HTTP request by middleware; agents read this to prefer the user's key
user_openai_key: ContextVar[str | None] = ContextVar("user_openai_key", default=None)

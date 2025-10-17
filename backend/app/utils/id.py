import shortuuid


def new_id(prefix: str | None = None) -> str:
    s = shortuuid.uuid()
    return f"{prefix}_{s}" if prefix else s


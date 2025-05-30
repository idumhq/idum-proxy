def check_path(obj, path: str) -> bool:
    """Check if nested attribute path exists"""
    current = obj
    for attr in path.split("."):
        if not hasattr(current, attr):
            return False
        current = getattr(current, attr)
    return True

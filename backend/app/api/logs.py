from fastapi import APIRouter

router = APIRouter()


@router.get("")
def get_logs(limit: int = 100) -> list[dict[str, str]]:
    """Placeholder — structured log persistence ships in a later phase."""
    return [{"message": "Log API not yet implemented", "limit": str(limit)}]

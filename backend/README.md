# DJ Library Pipeline — Backend

Python 3.11+ FastAPI service. See the [root README](../README.md) for full project documentation.

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
uvicorn app.main:app --reload
```

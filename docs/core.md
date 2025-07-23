# `core` Package Documentation

> Cross‑cutting utilities that **every other package may import**, but which **never import from outside**.  This guarantees acyclic dependencies (CUPID‑*Predictable*) and keeps shared concerns in one place.

```
core/
├── __init__.py
├── logging.py     # Structured logging & tracing
├── exceptions.py  # HTTP‑friendly error wrappers
└── security.py    # Crypto helpers (JWT & OAuth)
```

---

## 1. `core.logging`

| Responsibility                          | Details                                                                                                                                                                                                                                                            |
| --------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **What**                                | Provide a single `get_logger()` factory that returns a **structlog** logger pre‑configured with:<br>• JSON renderer in production (Log Analytics friendly)<br>• Colourised console renderer in dev<br>• OpenTelemetry span context injection (trace\_id, span\_id) |
| **Why**                                 | Centralised config eliminates copy‑paste `basicConfig` blocks and ensures trace correlation across FastAPI & Celery.                                                                                                                                               |
| **How**                                 |                                                                                                                                                                                                                                                                    |
| API                                     | \`\`\`python                                                                                                                                                                                                                                                       |
| from core.logging import get\_logger    |                                                                                                                                                                                                                                                                    |
| logger = get\_logger(**name**)          |                                                                                                                                                                                                                                                                    |
| logger.info("user.login", user\_id=123) |                                                                                                                                                                                                                                                                    |

````|
| ENV | `LOG_LEVEL` (`INFO` default), `LOG_FMT` (`json`/`pretty`), `OTEL_EXPORTER_OTLP_ENDPOINT`. |
| Extensibility | Add processors in `build_processor_chain()` – e.g. redact PII, enrich with request‑id. |

### Key Functions
```python
get_logger(name: str) -> structlog.BoundLogger
setup_logging(debug: bool = False) -> None
````

Call `setup_logging()` **once at startup** inside `gateway.main` and `worker.celery_app`.

---

## 2. `core.exceptions`

| Responsibility | Map internal errors to **RFC‑7807 Problem Details** JSON so clients get consistent error bodies and Swagger reflects possible responses.                                                                                                                     |         |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------- |
| Primary Class  | \`AppException(code: str, status\_code: int, message: str, extra: dict                                                                                                                                                                                       | None)\` |
| FastAPI Hook   | `add_exception_handlers(app: FastAPI) -> None` registers handlers for:<br>• `AppException` → `JSONResponse(status_code, {type, title, detail, ...})`<br>• `ValidationError` (Pydantic) → 422 problem<br>• Generic `Exception` → 500 problem (with trace\_id) |         |
| Example        |                                                                                                                                                                                                                                                              |         |

```python
raise AppException(
    code="auth.invalid_credentials",
    status_code=401,
    message="Username or password incorrect",
)
```

**Mapping Table** (extend per domain):

| Code                       | HTTP | Meaning        |
| -------------------------- | ---- | -------------- |
| `auth.invalid_credentials` | 401  | Bad login      |
| `auth.token_expired`       | 401  | JWT expired    |
| `resource.not_found`       | 404  | Missing entity |

---

## 3. `core.security`

| Responsibility  | Stateless crypto helpers kept free of framework code (CUPID‑*Independent*).                                                         |
| --------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| JWT             | `create_access_token(data: dict, exp_seconds: int) -> str`<br>`verify_token(token: str) -> dict` (raises `AppException` on failure) |
| Passwords       | `hash_password(plain: str) -> str` and `verify_password(plain, hashed) -> bool` using **argon2‑cffi**                               |
| OAuth           | `parse_jwt_from_provider(token: str, jwks_url: str) -> dict` (caches JWKS for 15 m)                                                 |
| ENV             | `JWT_SECRET_KEY`, `JWT_ALG` (`HS256` default), `OAUTH_JWKS_CACHE_TTL`                                                               |
| No Side Effects | Pure functions; no DB or HTTP – external calls injected via caller (e.g., pass a `requests.get` fn).                                |
| Usage           |                                                                                                                                     |

```python
from core.security import create_access_token, verify_token

token = create_access_token({"sub": user.id})
claims = verify_token(token)
```

---

## Usage in Services

```python
# gateway/main.py (excerpt)
from core.logging import setup_logging, get_logger
setup_logging(debug=settings.DEBUG)
logger = get_logger(__name__)

from core.exceptions import add_exception_handlers
add_exception_handlers(app)
```

*This yields uniform structured logs, auto‑traced exceptions, and zero duplication across the codebase.*

---

## Future Enhancements

* **Rate‑limit logger** processor to avoid log flooding.
* **Custom Problem Detail types** per RFC‑9457 once adopted.
* **Key rotation helper** in `core.security` for seamless JWT secret rollover.

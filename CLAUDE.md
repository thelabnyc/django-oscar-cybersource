# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

django-oscar-cybersource integrates django-oscar e-commerce sites with CyberSource Secure Acceptance Checkout API and SOAP API. It supports two payment flows:
1. **Secure Acceptance**: Browser-based form POST to CyberSource (PCI SAQ A-EP compliant)
2. **Bluefin**: Direct SOAP API integration for encrypted payment data

## Development Commands

**IMPORTANT**: All commands (tests, mypy, linting, etc.) MUST be run in Docker via `docker compose` due to the PostgreSQL dependency. The test database requires PostgreSQL's HStoreField support.

### Setup
```bash
# Start PostgreSQL service
docker compose up -d postgres

# Install dependencies locally (optional, for IDE support)
uv sync --all-extras
```

### Testing
```bash
# Run all tests (MUST use docker compose)
docker compose run --rm test uv run python manage.py test cybersource -v 2 --buffer --noinput

# Run tests in tox - tests multiple Django/Oscar version combinations
docker compose run --rm test uv run tox

# Run specific test file
docker compose run --rm test uv run python manage.py test cybersource.tests.test_checkout -v 2

# Run with coverage
docker compose run --rm test bash -c "uv run coverage erase && uv run coverage run manage.py test cybersource -v 2 --buffer --noinput && uv run coverage report"
```

### Type Checking & Linting
```bash
# Type checking (MUST use docker compose)
docker compose run --rm test uv run mypy cybersource sandbox

# Linting and formatting
docker compose run --rm test uv run ruff check .
docker compose run --rm test uv run ruff format .
```

### Translations
```bash
docker compose run --rm test make translations
```

### Building Documentation
```bash
# Documentation is built using Sphinx
docker compose run --rm test bash -c "cd docs && sphinx-build -b html . _build"
```

## Architecture

### Core Components

**Payment Flow Models:**
- `cybersource/models.py`: Contains three key models:
  - `SecureAcceptanceProfile`: Stores CyberSource credentials per hostname (supports multi-tenant)
  - `CyberSourceReply`: Logs all responses from CyberSource (both Secure Acceptance and SOAP)
  - `PaymentToken`: Stores tokenized payment methods for repeat purchases
  - `TransactionMixin`: Extends Oscar's AbstractTransaction with CyberSource-specific fields

**Payment Methods:**
- `cybersource/methods.py`: Defines two PaymentMethod classes:
  - `Cybersource`: Secure Acceptance flow (returns `FormPostRequired` status)
  - `Bluefin`: SOAP-based flow for encrypted payment data

**Actions:**
- `cybersource/actions.py`: Orchestrates payment operations:
  - `CreatePaymentToken`: Builds Secure Acceptance form fields
  - `RecordPaymentToken`: Saves token after successful creation
  - `GetPaymentToken`: Creates token via SOAP API (Bluefin flow)
  - `AuthorizePayment`: Authorizes payment using token via SOAP
  - `CapturePayment`: Captures previously authorized payment

**API Clients:**
- `cybersource/cybersoap.py`: SOAP API wrapper using Zeep
  - Handles PKCS12 certificate authentication
  - Supports authorization, capture, and token creation operations

**Views:**
- `cybersource/views.py`:
  - `CyberSourceReplyView`: Handles POST callbacks from Secure Acceptance
  - `DecisionManagerNotificationView`: Processes Decision Manager webhook updates
  - `FingerprintRedirectView`: Device fingerprinting for fraud detection

**Configuration:**
- `cybersource/conf.py`: Pydantic-based settings validation
  - Supports both legacy (separate settings) and modern (CYBERSOURCE dict) config
  - Required settings: ORG_ID, MERCHANT_ID, WSDL, PKCS12_DATA, PKCS12_PASSWORD

### Key Architectural Patterns

**Multi-Tenant Support:**
The package supports multiple CyberSource profiles via `SecureAcceptanceProfile.get_profile(hostname)`. Falls back to default profile or Django settings if hostname-specific profile not found.

**Transaction Lifecycle:**
1. Authorization creates a Transaction with `txn_type=AUTHORISE`
2. Capture creates a Transaction with `txn_type=DEBIT` and links to authorization via `authorization` FK
3. `TransactionMixin.get_remaining_amount_to_capture()` tracks partial captures

**Session Resumption:**
To work around SameSite=Lax cookie restrictions, the encrypted session ID is sent to CyberSource as merchant-defined data and returned in the reply, allowing session resumption after form POST.

**Decision Manager Integration:**
Webhook receives XML updates from CyberSource Decision Manager, allowing fraud review status changes to update order status and add notes.

### Testing Infrastructure

- **Sandbox app**: Minimal Django Oscar installation in `sandbox/` for testing
- **Test factories**: `cybersource/tests/factories.py` for creating test data
- **Mock responses**: `cybersource/test/responses.py` contains sample CyberSource responses
- Tests use Django TestCase with PostgreSQL (required for HStoreField)

### Important Implementation Details

**Signature Verification:**
All Secure Acceptance callbacks are verified using HMAC-SHA256 signatures via `cybersource/signature.py`. Invalid signatures raise `SuspiciousOperation`.

**Encrypted Fields:**
`SecureAcceptanceProfile.secret_key` uses `thelabdb.fields.EncryptedTextField` with Fernet encryption. Requires `FERNET_KEYS` in Django settings.

**Type Safety:**
Project uses strict mypy configuration with django-stubs. All code should be properly typed. Migrations and tests have `ignore_errors = true` in mypy config.

**SOAP Responses:**
SOAP API responses are zeep CompoundValue objects. Use `cybersource/utils.py:zeepobj_to_dict()` to convert for storage in HStoreField.

## Configuration

The package expects environment variables or Django settings for CyberSource credentials:
- `CYBERSOURCE_ORG_ID`
- `CYBERSOURCE_MERCHANT_ID`
- `CYBERSOURCE_PKCS12_DATA` (base64 encoded)
- `CYBERSOURCE_PKCS12_PASSWORD` (base64 encoded)
- `CYBERSOURCE_REDIRECT_PENDING`
- `CYBERSOURCE_REDIRECT_SUCCESS`
- `CYBERSOURCE_REDIRECT_FAIL`

Optional Secure Acceptance credentials (can also be stored in database):
- `CYBERSOURCE_PROFILE`
- `CYBERSOURCE_ACCESS`
- `CYBERSOURCE_SECRET`

## Common Patterns

**Adding New Transaction Types:**
Extend `SecureAcceptanceOrderAction` in actions.py and add handler to `CyberSourceReplyView.get_handler_fn()`.

**Custom SOAP Operations:**
Use `CyberSourceSoap.call()` with appropriate factory method from `self.factory`. See existing operations for examples.

**Extending Models:**
All models use `abstract = True` mixins where possible. Override in your Oscar fork if needed.

**Testing Payment Flows:**
Use `requests_mock` to mock SOAP API calls. See `test_checkout.py` for examples.

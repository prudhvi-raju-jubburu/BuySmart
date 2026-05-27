# PostgreSQL Configuration & Setup Guide

This guide details how to configure PostgreSQL for local development and testing, and connects Neon PostgreSQL as the single source of truth for the BuySmart application.

---

## 1. Environment Configurations

BuySmart requires two database connection strings inside the backend configuration file (`backend/.env`):

1. **`DATABASE_URL`**: Used by the main Flask application for development and production.
2. **`TEST_DATABASE_URL`**: Used strictly by the `pytest` test suite to isolate test database setups and teardowns from real user data.

### Configuration Template (`backend/.env`)

Add the following to your `backend/.env` file:

```ini
# =====================================================
# Database Configuration (PostgreSQL ONLY)
# =====================================================

# 1. Neon PostgreSQL URL (Staging / Production)
DATABASE_URL=postgresql://neondb_owner:npg_u8BNYfAVoU1I@ep-cool-union-aouxe72y.c-2.ap-southeast-1.aws.neon.tech/neondb?sslmode=require

# 2. Local PostgreSQL URLs (Alternative for local development)
# DATABASE_URL=postgresql://postgres:postgres@localhost:5432/buysmart_dev
# TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/buysmart_test

# 3. Test Database Connection (Required for running unit/persistence tests)
TEST_DATABASE_URL=postgresql://neondb_owner:npg_u8BNYfAVoU1I@ep-cool-union-aouxe72y.c-2.ap-southeast-1.aws.neon.tech/buysmart_test?sslmode=require
```

---

## 2. Setting Up a Local PostgreSQL Instance

If you choose to run local databases instead of connecting to remote Neon databases for development/tests:

### Installing PostgreSQL (Windows)
1. Download and run the installer from the [Official PostgreSQL Site](https://www.postgresql.org/download/windows/).
2. During installation, configure the default port to `5432` and set the password for the default `postgres` user (e.g. `postgres`).
3. Add the PostgreSQL `bin` directory (typically `C:\Program Files\PostgreSQL\<version>\bin`) to your Windows User `PATH` environment variable.

### Creating Databases
Create the target databases for development and testing using `psql` or pgAdmin:
```sql
CREATE DATABASE buysmart_dev;
CREATE DATABASE buysmart_test;
```

---

## 3. Database Initialization & Seeding

When the Flask application starts up, it automatically performs startup checks and creates any missing tables.

To seed initial development products and a default admin user, run:
```bash
python seed.py
```

---

## 4. Startup Verification Checks

On boot, BuySmart performs three startup validation checks:
1. **Environment Validation:** Verifies that `DATABASE_URL`, `SECRET_KEY`, and `JWT_SECRET_KEY` are all present.
2. **PostgreSQL Connectivity:** Executes a raw connection handshake (`SELECT 1`).
3. **Database Capabilities:** Performs temporary transactional reads/writes (`INSERT`/`DELETE`) to confirm read/write rights.

If all checks pass, the console prints:
```text
Environment Validation Passed
Connected to PostgreSQL
Database Health Check Passed
```
If any check fails, the application prints a critical error traceback and terminates immediately to prevent running in a broken state.

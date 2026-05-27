# Backup & Recovery Guide

This guide details how to export and import database states using the provided Python scripts. These utilities are essential for safeguarding production database states before running migrations or refactoring database schemas.

---

## 1. Exporting the Database

The `export_database.py` script queries all records from each table, serializes dates and times to JSON-safe ISO strings, and saves them to a structured JSON file.

### CLI Usage

Ensure your Python virtual environment is activated, then run:

```bash
# Run from the project root directory
python scripts/export_database.py [output_path.json]
```

### Examples

**Export to a default timestamped file:**
```bash
python scripts/export_database.py
```
*Creates a file like:* `buysmart_backup_20260525_141022.json`

**Export to a specific file path:**
```bash
python scripts/export_database.py backups/pre_migration_backup.json
```

---

## 2. Restoring the Database

The `import_database.py` script reads an exported JSON backup, drops and resets existing tables, inserts records in logical dependency order (to prevent foreign key constraint issues), and updates PostgreSQL serial ID sequences.

> [!CAUTION]
> Running the import database utility **completely drops and resets** existing tables in the target database before restoring! Verify that you have exported your current database state first!

### CLI Usage

```bash
python scripts/import_database.py <path_to_backup.json>
```

### Example
```bash
python scripts/import_database.py buysmart_backup_20260525_141022.json
```

---

## 3. Supported Tables

The backup and restore scripts handle the following data in logical dependency order:

1. **`products`**: Scraped products and attributes.
2. **`users`**: User profiles, password hashes, and admin roles.
3. **`wishlist`**: Saved product relations per user.
4. **`search_events`**: Keyword search history.
5. **`click_events`**: Analytics of comparison clicks.
6. **`purchase_events`**: Record of outbound purchases.
7. **`scraping_logs`**: Platform scrape durations and results.
8. **`analytics_counters`**: General platform metrics.
9. **`ai_search_events`**: AI-powered natural language queries.
10. **`ai_search_cache`**: Scraper results caching.
11. **`price_alerts`**: Price target alerts per user.
12. **`user_preferences`**: User platform/category weights.
13. **`recommendation_feedback`**: User feedback ratings on recommendations.

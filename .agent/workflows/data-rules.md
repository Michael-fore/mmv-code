---
description: data rules
---

try and use websites with history over APIs when possible.

Free API keys (USDA NASS, FRED, EIA, NOAA, etc.) are acceptable — register and use them. Only paid or proprietary data sources require explicit approval.

tables should map 1:1 with the sources, always flattening nested data.

When exploring websites, if it is an old site check the network calls to see if that is a simpler interface.

always fetch the raw data first to determine what the tables should look like

when creating the DDL for the tables, make sure our primary-key/deuplication strategy keeps in mind the nature of the data

## Normalization Rules

**All ingest scripts must normalize to canonical vocabulary before writing to the DB.** The DB tables are the source of truth for what values are allowed. Never write raw source-specific codes (e.g., SPTB codes, FEMA zone labels, numeric condition grades) into the DB without mapping them to canonical terms first.

**Import `canonical_vocab.py` for all mappings.** Never hardcode source-specific → canonical mappings inside an ingest script. Add the alias to `signals/canonical_vocab.py` and call `normalize_property_type()` / `normalize_entity_name()` from there.

**Unknown terms must be logged, never silently dropped.** If a value isn't in the canonical vocab, call `log_unknown_term(source, field, value)` — do not default to `"other"` or skip the record. The vocab resolution job picks these up nightly.

**Entity names:** Always store the raw `owner_name` as received. The `entity_aliases` table holds the resolved canonical name. Never attempt fuzzy matching at query time.
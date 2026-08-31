# Learning Material: Hashing, Security & JSON in MySQL

---

## 1. Cryptographic Hashing for Passwords

### 1.1 Theory: Hashing vs. Encryption

| Property | **Hashing (One-Way)** | **Encryption (Two-Way)** |
|---|---|---|
| **Reversibility** | Impossible to reverse | Reversible with key |
| **Purpose** | Verify integrity, store passwords | Confidentiality |
| **Output** | Fixed-length digest | Variable-length ciphertext |
| **Same Input** | Same output (deterministic) | Different output (IV/salt) |

> **Never store passwords in plaintext or encrypted form. Always hash.**

---

### 1.2 Password Hashing Best Practices

| Requirement | Why | Implementation |
|---|---|---|
| **Salt** | Prevent rainbow tables, ensure unique hashes | Random per-user, stored with hash |
| **Slow/Iterated** | Increase attacker cost (GPU/ASIC resistance) | PBKDF2, bcrypt, Argon2, scrypt |
| **Memory-Hard** | Resist parallel hardware attacks | Argon2id, scrypt |
| **Constant-Time Compare** | Prevent timing attacks | `secrets.compare_digest()` |

---

### 1.3 Project Implementation: PBKDF2-SHA256

**File:** `src/bismillah_mbd/routes/auth.py` (lines 36–52)

```python
PBKDF2_ITERATIONS = 120_000  # 120k iterations

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)           # 16 bytes = 32 hex chars
    digest = hashlib.pbkdf2_hmac(
        "sha256",                          # Algorithm
        password.encode(),                 # Input bytes
        salt.encode(),                     # Salt bytes
        PBKDF2_ITERATIONS                  # Iteration count
    ).hex()                                # Hex-encode binary digest
    return f"{salt}${digest}"              # Format: salt$hash

def verify_password(password: str, stored: str) -> bool:
    try:
        salt, digest = stored.split("$", 1)  # Split once on first $
    except ValueError:
        return False
    candidate = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), PBKDF2_ITERATIONS
    ).hex()
    return secrets.compare_digest(candidate, digest)  # Constant-time
```

**Storage Format in `users.password_hash`:**
```
a1b2c3d4e5f6...$f7e8d9c0b1a2...  (salt$hash)
```

**Why PBKDF2-SHA256?**
- ✅ Widely available in Python stdlib (`hashlib`)
- ✅ Configurable iterations (120k = ~100ms on modern CPU)
- ✅ Salt prevents precomputation
- ⚠️ Not memory-hard (consider Argon2id for new projects)

---

### 1.4 Database-Side Hashing (Not Used Here)

MySQL 8.0+ has built-in hashing functions:
```sql
-- Not recommended for passwords (too fast, no salt management)
SELECT SHA2('password', 256);           -- SHA-256
SELECT SHA2(CONCAT('salt', 'password'), 256);  -- Manual salt
```

**Why Application-Side is Preferred:**
1. **Separation of concerns** — DB stores, app computes
2. **Algorithm agility** — Change hashing without DB migration
3. **Resource isolation** — CPU-intensive hashing on app servers, not DB
4. **Standard libraries** — Battle-tested implementations

---

## 2. JSON Data Type in MySQL

### 2.1 Theory: JSON in Relational Databases

| Aspect | **Traditional Columns** | **JSON Column** |
|---|---|---|
| **Schema** | Fixed at DDL time | Flexible, schema-less |
| **Querying** | Standard SQL | JSON path expressions |
| **Indexing** | B+Tree on column | Virtual column + index |
| **Validation** | Type constraints | `JSON_VALID()`, `CHECK (JSON_VALID(col))` |
| **Storage** | Optimized per type | Binary format (OPTIMIZED) |

> **Use JSON for:** sparse attributes, user preferences, semi-structured data, rapid prototyping.

---

### 2.2 Project Implementation: `users.preferences`

**Schema:** `src/bismillah_mbd/sql/01-schema.sql` (line 30)
```sql
preferences JSON NULL
```

**Example Data (from seeder):**
```json
{"theme": "dark", "notifications": true}
{"theme": "light", "notifications": false}
{"theme": "system", "notifications": true}
```

---

### 2.3 JSON Functions Reference

| Function | Purpose | Example |
|---|---|---|
| `JSON_EXTRACT(col, '$.path')` | Extract value (returns JSON) | `JSON_EXTRACT(prefs, '$.theme')` → `"dark"` |
| `col->'$.path'` | Shorthand for extract | `prefs->'$.theme'` |
| `col->>'$.path'` | Extract as text (unquoted) | `prefs->>'$.theme'` → `dark` |
| `JSON_SET(col, '$.path', val)` | Insert/update value | `JSON_SET(prefs, '$.theme', 'light')` |
| `JSON_REMOVE(col, '$.path')` | Delete key | `JSON_REMOVE(prefs, '$.notifications')` |
| `JSON_KEYS(col)` | Array of top-level keys | `JSON_KEYS(prefs)` → `["theme", "notifications"]` |
| `JSON_CONTAINS(col, val, path)` | Check if value exists | `JSON_CONTAINS(prefs, 'true', '$.notifications')` |
| `JSON_VALID(col)` | Validate JSON syntax | `WHERE JSON_VALID(prefs)` |

---

### 2.4 Python Integration: JSON Preferences

**File:** `src/bismillah_mbd/routes/auth.py` (lines 132–146)

```python
@router.put("/users/{user_id}/preferences", response_model=UserResponse)
def set_preferences(user_id: int, preferences: dict, conn: MySQLConnection = Depends(get_db)):
    fetch_user(conn, user_id)  # Verify user exists
    try:
        with conn.cursor() as cur:
            cur.callproc("sp_update_user_preferences", (user_id, json.dumps(preferences)))
        conn.commit()
    except MySQLError as e:
        # ... error handling ...
    return fetch_user(conn, user_id)
```

**Procedure:** `src/bismillah_mbd/sql/03-procedures.sql`
```sql
CREATE PROCEDURE sp_update_user_preferences(IN p_user_id INT, IN p_preferences JSON)
BEGIN
    UPDATE users SET preferences = p_preferences WHERE id = p_user_id;
END;
```

**Key Points:**
- Python `dict` → `json.dumps()` → MySQL `JSON` type
- MySQL validates JSON on insert (invalid JSON → error)
- Whole-blob write (not partial update via API)

---

### 2.5 Querying JSON in SQL

```sql
-- Get users with dark theme
SELECT username, preferences->>'$.theme' AS theme
FROM users
WHERE preferences->>'$.theme' = 'dark';

-- Count users by notification preference
SELECT
    preferences->>'$.notifications' AS notifications,
    COUNT(*)
FROM users
WHERE JSON_VALID(preferences)
GROUP BY preferences->>'$.notifications';

-- Update single key (partial update)
UPDATE users
SET preferences = JSON_SET(preferences, '$.theme', 'light')
WHERE id = 1;

-- Add new key
UPDATE users
SET preferences = JSON_SET(preferences, '$.language', 'en')
WHERE id = 1;
```

---

### 2.6 Indexing JSON: Virtual Columns

MySQL cannot index JSON directly. Create **virtual generated column** + index:

```sql
-- Add virtual column extracting theme
ALTER TABLE users
ADD COLUMN theme_pref VARCHAR(20)
GENERATED ALWAYS AS (preferences->>'$.theme') VIRTUAL;

-- Index it
CREATE INDEX idx_users_theme ON users (theme_pref);
```

**How it works:**
- `VIRTUAL` = computed on read, not stored
- `STORED` = computed on write, takes space
- Index on virtual column enables fast `WHERE theme_pref = 'dark'`

---

## 3. Security Considerations

### 3.1 Password Hashing Checklist

- [ ] Use established algorithm (PBKDF2, bcrypt, Argon2id)
- [ ] Unique salt per user (16+ bytes, cryptographically random)
- [ ] Sufficient iterations (PBKDF2: 100k–600k; bcrypt: cost 10–12)
- [ ] Constant-time comparison (`secrets.compare_digest`)
- [ ] Store salt + hash together (single column)
- [ ] Never log passwords or hashes
- [ ] Rate-limit login attempts

### 3.2 JSON Security

- [ ] Validate JSON input in application (`json.loads()` catches malformed)
- [ ] `JSON_VALID()` in SQL for defense in depth
- [ ] Avoid storing sensitive data in JSON (tokens, PII)
- [ ] Sanitize before `JSON_SET` if user controls path

---

## 4. Hands-On Exercises

### Exercise 1: Password Hash Verification
```python
# In Python REPL
import hashlib, secrets

hash_val = hash_password("mySecret123")
print(hash_val)  # salt$hash

verify_password("mySecret123", hash_val)  # True
verify_password("wrong", hash_val)        # False
```

### Exercise 2: JSON Path Queries
```sql
-- Given preferences = '{"theme":"dark","notifications":true,"ui":{"density":"compact"}}'

-- Extract nested value
SELECT preferences->>'$.ui.density';  -- "compact"

-- Check nested key exists
SELECT JSON_CONTAINS_PATH(preferences, 'one', '$.ui.density');  -- 1

-- Update nested
SELECT JSON_SET(preferences, '$.ui.density', 'comfortable');
```

### Exercise 3: Virtual Column Index
```sql
-- Add virtual column for nested preference
ALTER TABLE users
ADD COLUMN ui_density VARCHAR(20)
GENERATED ALWAYS AS (preferences->>'$.ui.density') VIRTUAL;

CREATE INDEX idx_users_ui_density ON users (ui_density);

-- Query uses index
EXPLAIN SELECT * FROM users WHERE ui_density = 'compact';
```

### Exercise 4: Timing Attack Demo
```python
import time, secrets

# Vulnerable: string comparison (short-circuits on first mismatch)
def vulnerable_compare(a, b):
    return a == b

# Secure: constant-time
def secure_compare(a, b):
    return secrets.compare_digest(a, b)

# Timing difference exists in vulnerable version
```

### Exercise 5: Iteration Count Tuning
```python
import time, hashlib

def benchmark(iterations):
    start = time.time()
    hashlib.pbkdf2_hmac("sha256", b"pass", b"salt", iterations)
    return time.time() - start

for i in [50000, 100000, 200000, 400000]:
    print(f"{i:,} iterations: {benchmark(i)*1000:.1f}ms")
# Target: 100-300ms for interactive login
```

---

## 5. Architecture.md Reference: JSON Section

From `docs/database-documentation/architecture.md`:

```markdown
## JSON (`users.preferences`, Sub-CPMK-6)

- Column: `users.preferences JSON NULL` (already in `schema.sql`).
- Wired endpoints:
  - `PUT /users/{user_id}/preferences` stores an arbitrary JSON object (whole-blob write).
  - `GET /users/{id}` returns it.
- Student work: demonstrate extraction/modification against this column using
  MySQL JSON functions during evaluation (e.g., reading a single preference
  key). Suggested demo data shape: `{"theme": "dark", "notifications": true}`.
```

---

## 6. Summary Checklist

- [ ] **Hashing** = one-way; store `salt$hash`; verify with constant-time compare
- [ ] **PBKDF2-SHA256** with 120k iterations (application-side)
- [ ] **JSON** column for flexible, sparse attributes
- [ ] **JSON functions**: `->`, `->>`, `JSON_SET`, `JSON_REMOVE`, `JSON_EXTRACT`
- [ ] **Virtual columns** + index for JSON query performance
- [ ] **Whole-blob write** via procedure; partial updates via SQL if needed
- [ ] Security: no sensitive data in JSON; validate input; rate-limit auth
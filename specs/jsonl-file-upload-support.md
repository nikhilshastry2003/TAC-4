# Feature: JSONL File Upload Support

## Feature Description
Add support for uploading JSONL (JSON Lines) files to the application. JSONL files contain one JSON object per line, making them ideal for streaming data and large datasets. This feature will analyze the entire JSONL file to extract all possible fields across all records, handle nested objects and lists with proper concatenation and delimiter-based indexing, and create a new SQLite table just like the existing CSV and JSON upload functionality.

## User Story
As a data analyst
I want to upload JSONL files to the application
So that I can query line-delimited JSON data using natural language without having to convert it to CSV or JSON array format first

## Problem Statement
Currently, the application only supports CSV and JSON array file uploads. Many data sources and APIs export data in JSONL format, which is a standard format for log files, streaming data, and large datasets. Users must manually convert JSONL files to supported formats before uploading, which is time-consuming and error-prone. Additionally, JSONL files often contain nested structures and varying fields across records that need to be properly flattened and consolidated.

## Solution Statement
Extend the file processing system to handle JSONL files by parsing each line as a separate JSON object, scanning the entire file to identify all possible fields (including those that may only appear in some records), and flattening nested structures using delimiter-based concatenation. Nested lists will be concatenated with a configurable delimiter stored in a constants file, and individual list items can be accessed using indexed notation (_0, _1, etc.). The implementation will use Python's standard library (no new external dependencies) and integrate seamlessly with the existing upload workflow.

## Relevant Files
Use these files to implement the feature:

**Server-side files:**
- `app/server/server.py` - Update upload endpoint to accept .jsonl files and route to new processor function
- `app/server/core/file_processor.py` - Add new `convert_jsonl_to_sqlite` function for JSONL processing
- `app/server/core/sql_security.py` - Reuse existing validation for table and column names (no changes needed)

**Client-side files:**
- `app/client/index.html` - Update file upload UI text to mention .jsonl support
- `app/client/src/main.ts` - Update file input accept attribute to include .jsonl extension

**Test files:**
- `app/server/tests/core/test_file_processor.py` - Add comprehensive tests for JSONL processing
- `app/server/tests/assets/test_events.jsonl` - Sample JSONL file with nested structures
- `app/server/tests/assets/test_logs.jsonl` - Sample JSONL file with varying fields

**Documentation:**
- `README.md` - Update feature list and usage section to mention JSONL support

### New Files
- `app/server/core/constants.py` - New file for storing configurable constants like delimiters
- `app/server/tests/assets/test_events.jsonl` - Test file with nested objects and lists
- `app/server/tests/assets/test_logs.jsonl` - Test file with varying fields across records
- `app/server/tests/assets/test_simple.jsonl` - Simple test file for basic JSONL parsing

## Implementation Plan

### Phase 1: Foundation
Create the constants configuration file and implement the core JSONL parsing logic that can handle line-by-line JSON parsing, field consolidation across all records, and nested structure flattening with proper delimiter management.

### Phase 2: Core Implementation
Implement the `convert_jsonl_to_sqlite` function with full support for nested object and list handling, integrate it into the upload endpoint, and ensure proper security validation using existing patterns.

### Phase 3: Integration
Update the client-side UI to indicate JSONL support, create comprehensive test files representing real-world JSONL scenarios, implement thorough unit tests, and validate the feature works end-to-end with zero regressions.

## Step by Step Tasks
IMPORTANT: Execute every step in order, top to bottom.

### Create Constants Configuration File
- Create `app/server/core/constants.py` with the following constants:
  - `NESTED_OBJECT_DELIMITER = "__"` - Delimiter for flattening nested objects (e.g., "user__name")
  - `NESTED_LIST_DELIMITER = "||"` - Delimiter for concatenating list items into a string
  - `LIST_INDEX_PREFIX = "_"` - Prefix for indexed list access (e.g., "tags_0", "tags_1")
- Add docstrings explaining the purpose and usage of each constant
- Ensure the file follows existing code style and security patterns

### Implement Core JSONL Parsing Function
- Add `convert_jsonl_to_sqlite` function to `app/server/core/file_processor.py`
- Implement line-by-line JSON parsing to handle large files efficiently
- Create a field discovery phase that reads through entire file to identify all possible field names
- Handle malformed JSON lines gracefully (skip and log, don't fail entire upload)
- Implement nested object flattening using `NESTED_OBJECT_DELIMITER`
  - Example: `{"user": {"name": "John"}}` becomes `{"user__name": "John"}`
  - Support arbitrary nesting depth
- Implement nested list handling with dual approach:
  - Concatenated string column: `tags` → "python||javascript||ruby"
  - Indexed columns: `tags_0` → "python", `tags_1` → "javascript", `tags_2` → "ruby"
  - Determine max list length across all records during field discovery
- Use the same table name sanitization as CSV/JSON processors
- Use the same security validation patterns via `sql_security` module
- Return the same response structure as other processors (table_name, schema, row_count, sample_data)

### Add Security Validation
- Reuse existing `sanitize_table_name` function for JSONL table names
- Validate flattened column names using existing `validate_identifier` function
- Ensure no SQL injection vulnerabilities in dynamically created column names
- Add input validation to reject files that are too large or malformed

### Update Upload Endpoint
- Modify `app/server/server.py` upload endpoint to accept `.jsonl` file extension
- Update file type validation: `if not file.filename.endswith(('.csv', '.json', '.jsonl'))`
- Add routing logic: `elif file.filename.endswith('.jsonl'): result = convert_jsonl_to_sqlite(content, table_name)`
- Ensure error handling covers JSONL-specific errors
- Add logging for JSONL uploads with file size and record count

### Create Test JSONL Files
- Create `app/server/tests/assets/test_simple.jsonl` with 3 simple records (no nesting)
  - Example: `{"id": 1, "name": "Alice", "age": 30}`
- Create `app/server/tests/assets/test_events.jsonl` with nested objects and lists
  - Include records with: nested objects, arrays of primitives, varying field presence
  - Example: `{"event": "purchase", "user": {"id": 1, "name": "Alice"}, "items": ["book", "pen"], "total": 25.50}`
- Create `app/server/tests/assets/test_logs.jsonl` with varying fields
  - Different records have different field sets to test field consolidation
  - Example line 1: `{"timestamp": "2024-01-01", "level": "INFO", "message": "Start"}`
  - Example line 2: `{"timestamp": "2024-01-01", "level": "ERROR", "message": "Failed", "stack_trace": "..."}`

### Write Comprehensive Unit Tests
- Add test class `TestJSONLProcessor` to `app/server/tests/core/test_file_processor.py`
- Test `test_convert_jsonl_to_sqlite_success`: Basic JSONL parsing with simple records
- Test `test_convert_jsonl_to_sqlite_nested_objects`: Nested object flattening validation
- Test `test_convert_jsonl_to_sqlite_nested_lists`: List concatenation and indexing validation
- Test `test_convert_jsonl_to_sqlite_varying_fields`: Field consolidation across records
- Test `test_convert_jsonl_to_sqlite_empty_file`: Error handling for empty files
- Test `test_convert_jsonl_to_sqlite_invalid_json`: Error handling for malformed JSON lines
- Test `test_convert_jsonl_to_sqlite_table_name_sanitization`: Table name cleaning validation
- Test `test_convert_jsonl_to_sqlite_column_name_cleaning`: Column name normalization validation
- Verify all tests pass and provide proper error messages

### Update Client-Side File Upload UI
- Update `app/client/index.html` line 80: Change text from "Drag and drop .csv or .json files here" to "Drag and drop .csv, .json, or .jsonl files here"
- Update `app/client/index.html` line 81: Change accept attribute from `accept=".csv,.json"` to `accept=".csv,.json,.jsonl"`
- Update `app/client/src/main.ts` file upload handler to accept `.jsonl` extension (no code change needed, backend validation handles this)

### Update Documentation
- Update `README.md` line 8: Change "📁 Drag-and-drop file upload (.csv and .json)" to "📁 Drag-and-drop file upload (.csv, .json, and .jsonl)"
- Update `README.md` line 86: Change "Or drag and drop your own .csv or .json files" to "Or drag and drop your own .csv, .json, or .jsonl files"
- Update `README.md` line 138: Change "POST /api/upload" description from "Upload CSV/JSON file" to "Upload CSV/JSON/JSONL file"
- Add section to README explaining JSONL-specific features:
  - Nested object flattening with `__` delimiter
  - List concatenation with `||` delimiter
  - Indexed list access with `_0`, `_1`, etc.

### Run Validation Commands
- Run all unit tests to ensure no regressions
- Manually test JSONL upload with the created test files
- Verify table schema and data integrity in SQLite database
- Test natural language queries against uploaded JSONL data
- Verify error handling for invalid JSONL files

## Testing Strategy

### Unit Tests
- **JSONL Parser Tests**: Validate line-by-line JSON parsing handles valid and invalid JSON
- **Field Discovery Tests**: Ensure all fields across all records are discovered
- **Nested Object Tests**: Verify proper flattening with correct delimiter usage
- **Nested List Tests**: Validate both concatenation and indexing approaches work correctly
- **Table Creation Tests**: Ensure SQLite tables are created with correct schema
- **Security Tests**: Validate table and column name sanitization prevents SQL injection

### Integration Tests
- **End-to-End Upload**: Upload JSONL file via API and verify table creation
- **Query Integration**: Run natural language queries on JSONL-derived tables
- **Schema Validation**: Verify schema endpoint returns correct information for JSONL tables
- **Multiple File Types**: Upload CSV, JSON, and JSONL files in sequence without conflicts

### Edge Cases
- **Empty JSONL file**: Should return appropriate error message
- **Single record JSONL**: Should create table with single row
- **Malformed JSON lines**: Should skip bad lines and log warnings, process valid lines
- **Very long field names**: Should be truncated or sanitized appropriately
- **Deeply nested objects (5+ levels)**: Should flatten correctly without breaking
- **Large arrays (100+ items)**: Should handle indexed columns efficiently
- **Mixed data types in same field**: Should handle SQLite's flexible typing
- **Unicode and special characters**: Should be properly encoded and stored
- **Large files (10MB+)**: Should process without memory issues
- **Identical field names after flattening**: Should append suffix to avoid collisions

## Acceptance Criteria
- [ ] JSONL files can be uploaded via the UI drag-and-drop interface
- [ ] JSONL files can be uploaded via the file browser
- [ ] Each JSONL file creates a new SQLite table with sanitized name
- [ ] All fields across all JSONL records are discovered and included in schema
- [ ] Nested objects are flattened using `__` delimiter (e.g., `user__name`)
- [ ] Nested lists are concatenated using `||` delimiter in one column
- [ ] Nested lists create indexed columns (`_0`, `_1`, etc.) for individual access
- [ ] Constants are defined in `constants.py` and can be updated without code changes
- [ ] No new external libraries are added (only Python stdlib)
- [ ] Security validation prevents SQL injection in table/column names
- [ ] Malformed JSON lines are skipped with appropriate logging
- [ ] UI indicates JSONL support in file upload section
- [ ] Documentation is updated to explain JSONL features
- [ ] All existing tests continue to pass (zero regressions)
- [ ] New comprehensive tests cover JSONL functionality
- [ ] Natural language queries work correctly on JSONL-derived tables
- [ ] Error messages are clear and user-friendly for JSONL-specific errors

## Validation Commands
Execute every command to validate the feature works correctly with zero regressions.

- `cd app/server && uv run pytest tests/core/test_file_processor.py::TestJSONLProcessor -v` - Run JSONL-specific tests
- `cd app/server && uv run pytest tests/core/test_file_processor.py -v` - Run all file processor tests
- `cd app/server && uv run pytest` - Run server tests to validate the feature works with zero regressions
- `cd app/server && uv run python -c "from core.constants import NESTED_OBJECT_DELIMITER, NESTED_LIST_DELIMITER, LIST_INDEX_PREFIX; print(f'Delimiters configured: {NESTED_OBJECT_DELIMITER}, {NESTED_LIST_DELIMITER}, {LIST_INDEX_PREFIX}')"` - Verify constants are properly defined
- Manual validation: Start the application with `./scripts/start.sh` and upload each test JSONL file via UI, verify tables are created correctly
- Manual validation: Run natural language query "Show me all records" on each JSONL table and verify results display correctly

## Notes

### Implementation Considerations
- **No External Dependencies**: Use only Python standard library (`json` module) for JSONL parsing
- **Memory Efficiency**: Process JSONL line-by-line to handle large files without loading entire file into memory
- **Two-Pass Approach**: First pass discovers all fields, second pass populates data (acceptable tradeoff for schema completeness)
- **NULL Handling**: Fields not present in some records will be NULL in SQLite for those rows
- **Type Inference**: Let pandas/SQLite handle type inference automatically based on values
- **List Length Variation**: Indexed columns (_0, _1, etc.) are created based on max list length found across all records

### Delimiter Configuration Rationale
- `__` for nested objects: Common convention in many data processing systems (e.g., Django ORM)
- `||` for list concatenation: Distinct separator that's unlikely to appear in actual data
- `_` prefix for indexing: Clear, concise, and maintains SQLite column name validity

### Future Enhancements (Out of Scope)
- Streaming upload for very large JSONL files (>1GB)
- Configurable delimiter settings via UI
- Smart type detection for nested fields
- Automatic schema evolution when uploading updated JSONL files
- Export query results as JSONL format

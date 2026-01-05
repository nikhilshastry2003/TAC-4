import json
import os
import pandas as pd
import sqlite3
import io
import re
import logging
from typing import Dict, Any, List, Optional
from .sql_security import (
    execute_query_safely,
    validate_identifier,
    SQLSecurityError
)
from .constants import (
    NESTED_OBJECT_DELIMITER,
    NESTED_LIST_DELIMITER,
    LIST_INDEX_PREFIX
)

# Configure logging
logger = logging.getLogger(__name__)

def sanitize_table_name(table_name: str) -> str:
    """
    Sanitize table name for SQLite by removing/replacing bad characters
    and validating against SQL injection
    """
    # Remove file extension if present
    if '.' in table_name:
        table_name = table_name.rsplit('.', 1)[0]
    
    # Replace bad characters with underscores
    sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', table_name)
    
    # Ensure it starts with a letter or underscore
    if sanitized and not sanitized[0].isalpha() and sanitized[0] != '_':
        sanitized = '_' + sanitized
    
    # Ensure it's not empty
    if not sanitized:
        sanitized = 'table'
    
    # Validate the sanitized name
    try:
        validate_identifier(sanitized, "table")
    except SQLSecurityError:
        # If validation fails, use a safe default
        sanitized = f"table_{hash(table_name) % 100000}"
    
    return sanitized

def convert_csv_to_sqlite(csv_content: bytes, table_name: str) -> Dict[str, Any]:
    """
    Convert CSV file content to SQLite table
    """
    try:
        # Sanitize table name
        table_name = sanitize_table_name(table_name)
        
        # Read CSV into pandas DataFrame
        df = pd.read_csv(io.BytesIO(csv_content))
        
        # Clean column names
        df.columns = [col.lower().replace(' ', '_').replace('-', '_') for col in df.columns]
        
        # Connect to SQLite database
        conn = sqlite3.connect(os.path.join("db", "database.db"))
        
        # Write DataFrame to SQLite
        df.to_sql(table_name, conn, if_exists='replace', index=False)
        
        # Get schema information using safe query execution
        cursor_info = execute_query_safely(
            conn,
            "PRAGMA table_info({table})",
            identifier_params={'table': table_name}
        )
        columns_info = cursor_info.fetchall()
        
        schema = {}
        for col in columns_info:
            schema[col[1]] = col[2]  # column_name: data_type
        
        # Get sample data using safe query execution
        cursor_sample = execute_query_safely(
            conn,
            "SELECT * FROM {table} LIMIT 5",
            identifier_params={'table': table_name}
        )
        sample_rows = cursor_sample.fetchall()
        column_names = [col[1] for col in columns_info]
        sample_data = [dict(zip(column_names, row)) for row in sample_rows]
        
        # Get row count using safe query execution
        cursor_count = execute_query_safely(
            conn,
            "SELECT COUNT(*) FROM {table}",
            identifier_params={'table': table_name}
        )
        row_count = cursor_count.fetchone()[0]
        
        conn.close()
        
        return {
            'table_name': table_name,
            'schema': schema,
            'row_count': row_count,
            'sample_data': sample_data
        }
        
    except Exception as e:
        raise Exception(f"Error converting CSV to SQLite: {str(e)}")

def convert_json_to_sqlite(json_content: bytes, table_name: str) -> Dict[str, Any]:
    """
    Convert JSON file content to SQLite table
    """
    try:
        # Sanitize table name
        table_name = sanitize_table_name(table_name)
        
        # Parse JSON
        data = json.loads(json_content.decode('utf-8'))
        
        # Ensure it's a list of objects
        if not isinstance(data, list):
            raise ValueError("JSON must be an array of objects")
        
        if not data:
            raise ValueError("JSON array is empty")
        
        # Convert to pandas DataFrame
        df = pd.DataFrame(data)
        
        # Clean column names
        df.columns = [col.lower().replace(' ', '_').replace('-', '_') for col in df.columns]
        
        # Connect to SQLite database
        conn = sqlite3.connect(os.path.join("db", "database.db"))
        
        # Write DataFrame to SQLite
        df.to_sql(table_name, conn, if_exists='replace', index=False)
        
        # Get schema information using safe query execution
        cursor_info = execute_query_safely(
            conn,
            "PRAGMA table_info({table})",
            identifier_params={'table': table_name}
        )
        columns_info = cursor_info.fetchall()
        
        schema = {}
        for col in columns_info:
            schema[col[1]] = col[2]  # column_name: data_type
        
        # Get sample data using safe query execution
        cursor_sample = execute_query_safely(
            conn,
            "SELECT * FROM {table} LIMIT 5",
            identifier_params={'table': table_name}
        )
        sample_rows = cursor_sample.fetchall()
        column_names = [col[1] for col in columns_info]
        sample_data = [dict(zip(column_names, row)) for row in sample_rows]
        
        # Get row count using safe query execution
        cursor_count = execute_query_safely(
            conn,
            "SELECT COUNT(*) FROM {table}",
            identifier_params={'table': table_name}
        )
        row_count = cursor_count.fetchone()[0]
        
        conn.close()
        
        return {
            'table_name': table_name,
            'schema': schema,
            'row_count': row_count,
            'sample_data': sample_data
        }
        
    except Exception as e:
        raise Exception(f"Error converting JSON to SQLite: {str(e)}")

def flatten_nested_structure(obj: Any, parent_key: str = '', max_list_indices: Dict[str, int] = None) -> Dict[str, Any]:
    """
    Flatten nested objects and lists into a single-level dictionary.

    Args:
        obj: The object to flatten (dict, list, or primitive)
        parent_key: The parent key for nested structures
        max_list_indices: Dict tracking maximum list indices found (for indexed columns)

    Returns:
        Flattened dictionary with nested structures expanded
    """
    if max_list_indices is None:
        max_list_indices = {}

    flattened = {}

    if isinstance(obj, dict):
        for key, value in obj.items():
            new_key = f"{parent_key}{NESTED_OBJECT_DELIMITER}{key}" if parent_key else key
            # Recursively flatten nested structures
            nested_flattened = flatten_nested_structure(value, new_key, max_list_indices)
            flattened.update(nested_flattened)

    elif isinstance(obj, list):
        # Create concatenated string column
        if parent_key:
            # Convert list items to strings and concatenate
            list_str = NESTED_LIST_DELIMITER.join(str(item) for item in obj)
            flattened[parent_key] = list_str

            # Create indexed columns for individual access
            for idx, item in enumerate(obj):
                indexed_key = f"{parent_key}{LIST_INDEX_PREFIX}{idx}"
                flattened[indexed_key] = item

            # Track maximum list index for this key
            if parent_key not in max_list_indices or len(obj) > max_list_indices[parent_key]:
                max_list_indices[parent_key] = len(obj)

    else:
        # Primitive value (string, number, boolean, null)
        if parent_key:
            flattened[parent_key] = obj

    return flattened

def discover_all_fields(records: List[Dict[str, Any]]) -> tuple[set, Dict[str, int]]:
    """
    Discover all possible fields across all records, including nested structures.

    Args:
        records: List of parsed JSONL records

    Returns:
        Tuple of (set of all field names, dict of max list indices per field)
    """
    all_fields = set()
    max_list_indices = {}

    for record in records:
        flattened = flatten_nested_structure(record, max_list_indices=max_list_indices)
        all_fields.update(flattened.keys())

    return all_fields, max_list_indices

def clean_column_name(col_name: str) -> str:
    """
    Clean and normalize column names for SQLite.

    Args:
        col_name: Original column name

    Returns:
        Cleaned column name safe for SQLite
    """
    # Convert to lowercase and replace spaces/hyphens with underscores
    cleaned = col_name.lower().replace(' ', '_').replace('-', '_')

    # Replace any remaining invalid characters
    cleaned = re.sub(r'[^a-z0-9_]', '_', cleaned)

    # Ensure it starts with a letter or underscore
    if cleaned and not cleaned[0].isalpha() and cleaned[0] != '_':
        cleaned = '_' + cleaned

    # Ensure it's not empty
    if not cleaned:
        cleaned = 'column'

    return cleaned

def convert_jsonl_to_sqlite(jsonl_content: bytes, table_name: str) -> Dict[str, Any]:
    """
    Convert JSONL file content to SQLite table.

    Parses JSON Lines format (one JSON object per line), handles nested objects
    and lists, discovers all fields across all records, and creates a SQLite table.

    Args:
        jsonl_content: Raw bytes content of JSONL file
        table_name: Desired name for the SQLite table

    Returns:
        Dictionary with table_name, schema, row_count, and sample_data

    Raises:
        Exception: If file is empty, malformed, or processing fails
    """
    try:
        # Sanitize table name
        table_name = sanitize_table_name(table_name)

        # Parse JSONL content line by line
        content_str = jsonl_content.decode('utf-8')
        lines = content_str.strip().split('\n')

        if not lines or (len(lines) == 1 and not lines[0].strip()):
            raise ValueError("JSONL file is empty")

        # Parse JSON records and collect valid ones
        records = []
        skipped_lines = 0

        for line_num, line in enumerate(lines, start=1):
            line = line.strip()
            if not line:
                continue

            try:
                record = json.loads(line)
                if not isinstance(record, dict):
                    logger.warning(f"Line {line_num} is not a JSON object, skipping")
                    skipped_lines += 1
                    continue
                records.append(record)
            except json.JSONDecodeError as e:
                logger.warning(f"Line {line_num} contains invalid JSON, skipping: {str(e)}")
                skipped_lines += 1
                continue

        if not records:
            raise ValueError("No valid JSON objects found in JSONL file")

        if skipped_lines > 0:
            logger.info(f"Skipped {skipped_lines} invalid lines in JSONL file")

        # Discover all fields across all records
        all_fields, max_list_indices = discover_all_fields(records)

        # Flatten all records
        flattened_records = []
        for record in records:
            flattened = flatten_nested_structure(record, max_list_indices=max_list_indices)

            # Ensure all discovered fields are present (fill with None if missing)
            complete_record = {field: flattened.get(field, None) for field in all_fields}
            flattened_records.append(complete_record)

        # Convert to pandas DataFrame
        df = pd.DataFrame(flattened_records)

        # Clean column names
        df.columns = [clean_column_name(col) for col in df.columns]

        # Handle duplicate column names after cleaning
        seen_columns = {}
        final_columns = []
        for col in df.columns:
            if col in seen_columns:
                seen_columns[col] += 1
                final_columns.append(f"{col}_{seen_columns[col]}")
            else:
                seen_columns[col] = 0
                final_columns.append(col)
        df.columns = final_columns

        # Connect to SQLite database
        conn = sqlite3.connect(os.path.join("db", "database.db"))

        # Write DataFrame to SQLite
        df.to_sql(table_name, conn, if_exists='replace', index=False)

        # Get schema information using safe query execution
        cursor_info = execute_query_safely(
            conn,
            "PRAGMA table_info({table})",
            identifier_params={'table': table_name}
        )
        columns_info = cursor_info.fetchall()

        schema = {}
        for col in columns_info:
            schema[col[1]] = col[2]  # column_name: data_type

        # Get sample data using safe query execution
        cursor_sample = execute_query_safely(
            conn,
            "SELECT * FROM {table} LIMIT 5",
            identifier_params={'table': table_name}
        )
        sample_rows = cursor_sample.fetchall()
        column_names = [col[1] for col in columns_info]
        sample_data = [dict(zip(column_names, row)) for row in sample_rows]

        # Get row count using safe query execution
        cursor_count = execute_query_safely(
            conn,
            "SELECT COUNT(*) FROM {table}",
            identifier_params={'table': table_name}
        )
        row_count = cursor_count.fetchone()[0]

        conn.close()

        logger.info(f"Successfully converted JSONL to SQLite table '{table_name}' with {row_count} rows")

        return {
            'table_name': table_name,
            'schema': schema,
            'row_count': row_count,
            'sample_data': sample_data
        }

    except Exception as e:
        raise Exception(f"Error converting JSONL to SQLite: {str(e)}")
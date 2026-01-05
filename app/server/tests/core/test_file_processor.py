import pytest
import json
import pandas as pd
import sqlite3
import os
import io
from pathlib import Path
from unittest.mock import patch
from core.file_processor import (
    convert_csv_to_sqlite,
    convert_json_to_sqlite,
    convert_jsonl_to_sqlite,
    flatten_nested_structure,
    clean_column_name
)


@pytest.fixture
def test_db():
    """Create an in-memory test database"""
    # Create in-memory database
    conn = sqlite3.connect(':memory:')
    
    # Patch the database connection to use our in-memory database
    with patch('core.file_processor.sqlite3.connect') as mock_connect:
        mock_connect.return_value = conn
        yield conn
    
    conn.close()


@pytest.fixture
def test_assets_dir():
    """Get the path to test assets directory"""
    return Path(__file__).parent.parent / "assets"


class TestFileProcessor:
    
    def test_convert_csv_to_sqlite_success(self, test_db, test_assets_dir):
        # Load real CSV file
        csv_file = test_assets_dir / "test_users.csv"
        with open(csv_file, 'rb') as f:
            csv_data = f.read()
        
        table_name = "users"
        result = convert_csv_to_sqlite(csv_data, table_name)
        
        # Verify return structure
        assert result['table_name'] == table_name
        assert 'schema' in result
        assert 'row_count' in result
        assert 'sample_data' in result
        
        # Test the returned data
        assert result['row_count'] == 4  # 4 users in test file
        assert len(result['sample_data']) <= 5  # Should return up to 5 samples
        
        # Verify schema has expected columns (cleaned names)
        assert 'name' in result['schema']
        assert 'age' in result['schema'] 
        assert 'city' in result['schema']
        assert 'email' in result['schema']
        
        # Verify sample data structure and content
        john_data = next((item for item in result['sample_data'] if item['name'] == 'John Doe'), None)
        assert john_data is not None
        assert john_data['age'] == 25
        assert john_data['city'] == 'New York'
        assert john_data['email'] == 'john@example.com'
    
    def test_convert_csv_to_sqlite_column_cleaning(self, test_db, test_assets_dir):
        # Test column name cleaning with real file
        csv_file = test_assets_dir / "column_names.csv"
        with open(csv_file, 'rb') as f:
            csv_data = f.read()
        
        table_name = "test_users"
        result = convert_csv_to_sqlite(csv_data, table_name)
        
        # Verify columns were cleaned in the schema
        assert 'full_name' in result['schema']
        assert 'birth_date' in result['schema']
        assert 'email_address' in result['schema']
        assert 'phone_number' in result['schema']
        
        # Verify sample data has cleaned column names and actual content
        sample = result['sample_data'][0]
        assert 'full_name' in sample
        assert 'birth_date' in sample
        assert 'email_address' in sample
        assert sample['full_name'] == 'John Doe'
        assert sample['birth_date'] == '1990-01-15'
    
    def test_convert_csv_to_sqlite_with_inconsistent_data(self, test_db, test_assets_dir):
        # Test with CSV that has inconsistent row lengths - should raise error
        csv_file = test_assets_dir / "invalid.csv"
        with open(csv_file, 'rb') as f:
            csv_data = f.read()
        
        table_name = "inconsistent_table"
        
        # Pandas will fail on inconsistent CSV data
        with pytest.raises(Exception) as exc_info:
            convert_csv_to_sqlite(csv_data, table_name)
        
        assert "Error converting CSV to SQLite" in str(exc_info.value)
    
    def test_convert_json_to_sqlite_success(self, test_db, test_assets_dir):
        # Load real JSON file
        json_file = test_assets_dir / "test_products.json"
        with open(json_file, 'rb') as f:
            json_data = f.read()
        
        table_name = "products"
        result = convert_json_to_sqlite(json_data, table_name)
        
        # Verify return structure
        assert result['table_name'] == table_name
        assert 'schema' in result
        assert 'row_count' in result
        assert 'sample_data' in result
        
        # Test the returned data
        assert result['row_count'] == 3  # 3 products in test file
        assert len(result['sample_data']) == 3
        
        # Verify schema has expected columns
        assert 'id' in result['schema']
        assert 'name' in result['schema']
        assert 'price' in result['schema']
        assert 'category' in result['schema']
        assert 'in_stock' in result['schema']
        
        # Verify sample data structure and content
        laptop_data = next((item for item in result['sample_data'] if item['name'] == 'Laptop'), None)
        assert laptop_data is not None
        assert laptop_data['price'] == 999.99
        assert laptop_data['category'] == 'Electronics'
        assert laptop_data['in_stock'] == True
    
    def test_convert_json_to_sqlite_invalid_json(self):
        # Test with invalid JSON
        json_data = b'invalid json'
        table_name = "test_table"
        
        with pytest.raises(Exception) as exc_info:
            convert_json_to_sqlite(json_data, table_name)
        
        assert "Error converting JSON to SQLite" in str(exc_info.value)
    
    def test_convert_json_to_sqlite_not_array(self):
        # Test with JSON that's not an array
        json_data = b'{"name": "John", "age": 25}'
        table_name = "test_table"
        
        with pytest.raises(Exception) as exc_info:
            convert_json_to_sqlite(json_data, table_name)
        
        assert "JSON must be an array of objects" in str(exc_info.value)
    
    def test_convert_json_to_sqlite_empty_array(self):
        # Test with empty JSON array
        json_data = b'[]'
        table_name = "test_table"

        with pytest.raises(Exception) as exc_info:
            convert_json_to_sqlite(json_data, table_name)

        assert "JSON array is empty" in str(exc_info.value)


class TestJSONLProcessor:
    """Test suite for JSONL file processing"""

    def test_convert_jsonl_to_sqlite_success(self, test_db, test_assets_dir):
        """Test basic JSONL parsing with simple records"""
        jsonl_file = test_assets_dir / "test_simple.jsonl"
        with open(jsonl_file, 'rb') as f:
            jsonl_data = f.read()

        table_name = "simple_test"
        result = convert_jsonl_to_sqlite(jsonl_data, table_name)

        # Verify return structure
        assert result['table_name'] == table_name
        assert 'schema' in result
        assert 'row_count' in result
        assert 'sample_data' in result

        # Test the returned data
        assert result['row_count'] == 3
        assert len(result['sample_data']) == 3

        # Verify schema has expected columns
        assert 'id' in result['schema']
        assert 'name' in result['schema']
        assert 'age' in result['schema']

        # Verify sample data content
        alice_data = next((item for item in result['sample_data'] if item['name'] == 'Alice'), None)
        assert alice_data is not None
        assert alice_data['id'] == 1
        assert alice_data['age'] == 30

    def test_convert_jsonl_to_sqlite_nested_objects(self, test_db, test_assets_dir):
        """Test nested object flattening validation"""
        jsonl_file = test_assets_dir / "test_events.jsonl"
        with open(jsonl_file, 'rb') as f:
            jsonl_data = f.read()

        table_name = "events_test"
        result = convert_jsonl_to_sqlite(jsonl_data, table_name)

        # Verify return structure
        assert result['table_name'] == table_name
        assert result['row_count'] == 4

        # Verify nested object flattening (user__id, user__name, user__email)
        assert 'user__id' in result['schema']
        assert 'user__name' in result['schema']

        # Verify sample data has flattened fields
        purchase_event = next((item for item in result['sample_data'] if item['event'] == 'purchase'), None)
        assert purchase_event is not None
        assert purchase_event['user__id'] == 1
        assert purchase_event['user__name'] == 'Alice'

    def test_convert_jsonl_to_sqlite_nested_lists(self, test_db, test_assets_dir):
        """Test list concatenation and indexing validation"""
        jsonl_file = test_assets_dir / "test_events.jsonl"
        with open(jsonl_file, 'rb') as f:
            jsonl_data = f.read()

        table_name = "events_lists_test"
        result = convert_jsonl_to_sqlite(jsonl_data, table_name)

        # Verify concatenated list column exists
        assert 'items' in result['schema']

        # Verify indexed list columns exist (items_0, items_1, etc.)
        assert 'items_0' in result['schema']
        assert 'items_1' in result['schema']

        # Verify sample data has both formats
        purchase_event = next((item for item in result['sample_data'] if item['event'] == 'purchase'), None)
        assert purchase_event is not None

        # Check concatenated format
        assert 'book||pen' in str(purchase_event['items']) or purchase_event['items'] == 'book||pen'

        # Check indexed access
        assert purchase_event['items_0'] == 'book'
        assert purchase_event['items_1'] == 'pen'

    def test_convert_jsonl_to_sqlite_varying_fields(self, test_db, test_assets_dir):
        """Test field consolidation across records"""
        jsonl_file = test_assets_dir / "test_logs.jsonl"
        with open(jsonl_file, 'rb') as f:
            jsonl_data = f.read()

        table_name = "logs_test"
        result = convert_jsonl_to_sqlite(jsonl_data, table_name)

        # Verify all fields from all records are included
        assert 'timestamp' in result['schema']
        assert 'level' in result['schema']
        assert 'message' in result['schema']
        assert 'stack_trace' in result['schema']  # Only in some records
        assert 'error_code' in result['schema']  # Only in some records
        assert 'retry_count' in result['schema']  # Only in some records
        assert 'memory_mb' in result['schema']  # Only in some records

        # Verify records with missing fields have NULL/None values
        assert result['row_count'] == 5

    def test_convert_jsonl_to_sqlite_empty_file(self, test_db):
        """Test error handling for empty files"""
        jsonl_data = b''
        table_name = "empty_test"

        with pytest.raises(Exception) as exc_info:
            convert_jsonl_to_sqlite(jsonl_data, table_name)

        assert "JSONL file is empty" in str(exc_info.value)

    def test_convert_jsonl_to_sqlite_invalid_json(self, test_db):
        """Test error handling for malformed JSON lines"""
        jsonl_data = b'{"valid": "json"}\n{invalid json}\n{"another": "valid"}'
        table_name = "invalid_test"

        # Should skip invalid lines and process valid ones
        result = convert_jsonl_to_sqlite(jsonl_data, table_name)

        # Should have processed 2 valid records
        assert result['row_count'] == 2

    def test_convert_jsonl_to_sqlite_table_name_sanitization(self, test_db):
        """Test table name cleaning validation"""
        jsonl_data = b'{"id": 1, "name": "test"}'
        table_name = "My Table-Name!"

        result = convert_jsonl_to_sqlite(jsonl_data, table_name)

        # Table name should be sanitized (special chars replaced with underscores)
        assert result['table_name'] == "My_Table_Name_"

    def test_convert_jsonl_to_sqlite_column_name_cleaning(self, test_db):
        """Test column name normalization validation"""
        jsonl_data = b'{"User ID": 1, "Full-Name": "Alice", "Email Address": "alice@example.com"}'
        table_name = "column_test"

        result = convert_jsonl_to_sqlite(jsonl_data, table_name)

        # Column names should be cleaned
        assert 'user_id' in result['schema']
        assert 'full_name' in result['schema']
        assert 'email_address' in result['schema']

    def test_flatten_nested_structure_simple(self):
        """Test flattening simple nested objects"""
        obj = {"user": {"name": "John", "age": 30}}
        flattened = flatten_nested_structure(obj)

        assert flattened['user__name'] == 'John'
        assert flattened['user__age'] == 30

    def test_flatten_nested_structure_deep_nesting(self):
        """Test flattening deeply nested objects"""
        obj = {
            "level1": {
                "level2": {
                    "level3": {
                        "value": "deep"
                    }
                }
            }
        }
        flattened = flatten_nested_structure(obj)

        assert flattened['level1__level2__level3__value'] == 'deep'

    def test_flatten_nested_structure_with_lists(self):
        """Test flattening objects with lists"""
        max_indices = {}
        obj = {"tags": ["python", "javascript", "ruby"]}
        flattened = flatten_nested_structure(obj, max_list_indices=max_indices)

        # Check concatenated format
        assert flattened['tags'] == 'python||javascript||ruby'

        # Check indexed format
        assert flattened['tags_0'] == 'python'
        assert flattened['tags_1'] == 'javascript'
        assert flattened['tags_2'] == 'ruby'

        # Check max indices tracking
        assert max_indices['tags'] == 3

    def test_clean_column_name(self):
        """Test column name cleaning function"""
        assert clean_column_name("User ID") == "user_id"
        assert clean_column_name("Full-Name") == "full_name"
        assert clean_column_name("Email Address") == "email_address"
        assert clean_column_name("123invalid") == "_123invalid"
        assert clean_column_name("") == "column"
        assert clean_column_name("valid_name") == "valid_name"
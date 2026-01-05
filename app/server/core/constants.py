"""
Constants configuration for file processing.

This module contains configurable constants used throughout the file processing
system, particularly for handling nested structures in JSONL files.
"""

# Delimiter for flattening nested objects
# Example: {"user": {"name": "John"}} becomes {"user__name": "John"}
NESTED_OBJECT_DELIMITER = "__"

# Delimiter for concatenating list items into a single string column
# Example: ["python", "javascript", "ruby"] becomes "python||javascript||ruby"
NESTED_LIST_DELIMITER = "||"

# Prefix for indexed list access columns
# Example: ["python", "javascript"] creates columns "tags_0", "tags_1"
LIST_INDEX_PREFIX = "_"

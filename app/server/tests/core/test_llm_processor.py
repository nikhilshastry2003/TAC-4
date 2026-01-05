import pytest
import os
from unittest.mock import patch, MagicMock
from core.llm_processor import (
    generate_sql_with_gemini,
    generate_sql_with_anthropic,
    format_schema_for_prompt,
    generate_sql
)
from core.data_models import QueryRequest


class TestLLMProcessor:

    @patch('core.llm_processor.genai')
    def test_generate_sql_with_gemini_success(self, mock_genai):
        # Mock Gemini model and response
        mock_model = MagicMock()
        mock_genai.GenerativeModel.return_value = mock_model

        mock_response = MagicMock()
        mock_response.text = "SELECT * FROM users WHERE age > 25"
        mock_model.generate_content.return_value = mock_response

        # Mock environment variable
        with patch.dict(os.environ, {'GEMINI_API_KEY': 'test-key'}):
            query_text = "Show me users older than 25"
            schema_info = {
                'tables': {
                    'users': {
                        'columns': {'id': 'INTEGER', 'name': 'TEXT', 'age': 'INTEGER'},
                        'row_count': 100
                    }
                }
            }

            result = generate_sql_with_gemini(query_text, schema_info)

            assert result == "SELECT * FROM users WHERE age > 25"
            mock_genai.configure.assert_called_once_with(api_key='test-key')
            mock_model.generate_content.assert_called_once()

    @patch('core.llm_processor.genai')
    def test_generate_sql_with_gemini_clean_markdown(self, mock_genai):
        # Test SQL cleanup from markdown
        mock_model = MagicMock()
        mock_genai.GenerativeModel.return_value = mock_model

        mock_response = MagicMock()
        mock_response.text = "```sql\nSELECT * FROM users\n```"
        mock_model.generate_content.return_value = mock_response

        with patch.dict(os.environ, {'GEMINI_API_KEY': 'test-key'}):
            query_text = "Show all users"
            schema_info = {'tables': {}}

            result = generate_sql_with_gemini(query_text, schema_info)

            assert result == "SELECT * FROM users"

    def test_generate_sql_with_gemini_no_api_key(self):
        # Test error when API key is not set
        with patch.dict(os.environ, {}, clear=True):
            query_text = "Show all users"
            schema_info = {'tables': {}}

            with pytest.raises(Exception) as exc_info:
                generate_sql_with_gemini(query_text, schema_info)

            assert "GEMINI_API_KEY environment variable not set" in str(exc_info.value)

    @patch('core.llm_processor.genai')
    def test_generate_sql_with_gemini_api_error(self, mock_genai):
        # Test API error handling
        mock_model = MagicMock()
        mock_genai.GenerativeModel.return_value = mock_model
        mock_model.generate_content.side_effect = Exception("API Error")

        with patch.dict(os.environ, {'GEMINI_API_KEY': 'test-key'}):
            query_text = "Show all users"
            schema_info = {'tables': {}}

            with pytest.raises(Exception) as exc_info:
                generate_sql_with_gemini(query_text, schema_info)

            assert "Error generating SQL with Gemini" in str(exc_info.value)

    @patch('core.llm_processor.Anthropic')
    def test_generate_sql_with_anthropic_success(self, mock_anthropic_class):
        # Mock Anthropic client and response
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.content[0].text = "SELECT * FROM products WHERE price < 100"
        mock_client.messages.create.return_value = mock_response

        # Mock environment variable
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'}):
            query_text = "Show me products under $100"
            schema_info = {
                'tables': {
                    'products': {
                        'columns': {'id': 'INTEGER', 'name': 'TEXT', 'price': 'REAL'},
                        'row_count': 50
                    }
                }
            }

            result = generate_sql_with_anthropic(query_text, schema_info)

            assert result == "SELECT * FROM products WHERE price < 100"
            mock_client.messages.create.assert_called_once()

            # Verify the API call parameters
            call_args = mock_client.messages.create.call_args
            assert call_args[1]['model'] == 'claude-3-haiku-20240307'
            assert call_args[1]['temperature'] == 0.1
            assert call_args[1]['max_tokens'] == 500

    @patch('core.llm_processor.Anthropic')
    def test_generate_sql_with_anthropic_clean_markdown(self, mock_anthropic_class):
        # Test SQL cleanup from markdown
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.content[0].text = "```\nSELECT * FROM orders\n```"
        mock_client.messages.create.return_value = mock_response

        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'}):
            query_text = "Show all orders"
            schema_info = {'tables': {}}

            result = generate_sql_with_anthropic(query_text, schema_info)

            assert result == "SELECT * FROM orders"

    def test_generate_sql_with_anthropic_no_api_key(self):
        # Test error when API key is not set
        with patch.dict(os.environ, {}, clear=True):
            query_text = "Show all orders"
            schema_info = {'tables': {}}

            with pytest.raises(Exception) as exc_info:
                generate_sql_with_anthropic(query_text, schema_info)

            assert "ANTHROPIC_API_KEY environment variable not set" in str(exc_info.value)

    @patch('core.llm_processor.Anthropic')
    def test_generate_sql_with_anthropic_api_error(self, mock_anthropic_class):
        # Test API error handling
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client
        mock_client.messages.create.side_effect = Exception("API Error")

        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'}):
            query_text = "Show all orders"
            schema_info = {'tables': {}}

            with pytest.raises(Exception) as exc_info:
                generate_sql_with_anthropic(query_text, schema_info)

            assert "Error generating SQL with Anthropic" in str(exc_info.value)

    def test_format_schema_for_prompt(self):
        # Test schema formatting for LLM prompt
        schema_info = {
            'tables': {
                'users': {
                    'columns': {'id': 'INTEGER', 'name': 'TEXT', 'age': 'INTEGER'},
                    'row_count': 100
                },
                'products': {
                    'columns': {'id': 'INTEGER', 'name': 'TEXT', 'price': 'REAL'},
                    'row_count': 50
                }
            }
        }

        result = format_schema_for_prompt(schema_info)

        assert "Table: users" in result
        assert "Table: products" in result
        assert "- id (INTEGER)" in result
        assert "- name (TEXT)" in result
        assert "- age (INTEGER)" in result
        assert "- price (REAL)" in result
        assert "Row count: 100" in result
        assert "Row count: 50" in result

    def test_format_schema_for_prompt_empty(self):
        # Test with empty schema
        schema_info = {'tables': {}}

        result = format_schema_for_prompt(schema_info)

        assert result == ""

    @patch('core.llm_processor.generate_sql_with_gemini')
    def test_generate_sql_gemini_key_priority(self, mock_gemini_func):
        # Test that Gemini is used when Gemini key exists (regardless of request preference)
        mock_gemini_func.return_value = "SELECT * FROM users"

        with patch.dict(os.environ, {'GEMINI_API_KEY': 'gemini-key', 'ANTHROPIC_API_KEY': 'anthropic-key'}):
            request = QueryRequest(query="Show all users", llm_provider="anthropic")
            schema_info = {'tables': {}}

            result = generate_sql(request, schema_info)

            assert result == "SELECT * FROM users"
            mock_gemini_func.assert_called_once_with("Show all users", schema_info)

    @patch('core.llm_processor.generate_sql_with_anthropic')
    def test_generate_sql_anthropic_fallback(self, mock_anthropic_func):
        # Test that Anthropic is used when only Anthropic key exists
        mock_anthropic_func.return_value = "SELECT * FROM products"

        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'anthropic-key'}, clear=True):
            request = QueryRequest(query="Show all products", llm_provider="gemini")
            schema_info = {'tables': {}}

            result = generate_sql(request, schema_info)

            assert result == "SELECT * FROM products"
            mock_anthropic_func.assert_called_once_with("Show all products", schema_info)

    @patch('core.llm_processor.generate_sql_with_gemini')
    def test_generate_sql_request_preference_gemini(self, mock_gemini_func):
        # Test request preference when no keys available
        mock_gemini_func.return_value = "SELECT * FROM orders"

        with patch.dict(os.environ, {}, clear=True):
            request = QueryRequest(query="Show all orders", llm_provider="gemini")
            schema_info = {'tables': {}}

            result = generate_sql(request, schema_info)

            assert result == "SELECT * FROM orders"
            mock_gemini_func.assert_called_once_with("Show all orders", schema_info)

    @patch('core.llm_processor.generate_sql_with_anthropic')
    def test_generate_sql_request_preference_anthropic(self, mock_anthropic_func):
        # Test request preference when no keys available
        mock_anthropic_func.return_value = "SELECT * FROM customers"

        with patch.dict(os.environ, {}, clear=True):
            request = QueryRequest(query="Show all customers", llm_provider="anthropic")
            schema_info = {'tables': {}}

            result = generate_sql(request, schema_info)

            assert result == "SELECT * FROM customers"
            mock_anthropic_func.assert_called_once_with("Show all customers", schema_info)

    @patch('core.llm_processor.generate_sql_with_gemini')
    def test_generate_sql_both_keys_gemini_priority(self, mock_gemini_func):
        # Test that Gemini has priority when both keys exist
        mock_gemini_func.return_value = "SELECT * FROM inventory"

        with patch.dict(os.environ, {'GEMINI_API_KEY': 'gemini-key', 'ANTHROPIC_API_KEY': 'anthropic-key'}):
            request = QueryRequest(query="Show inventory", llm_provider="anthropic")
            schema_info = {'tables': {}}

            result = generate_sql(request, schema_info)

            assert result == "SELECT * FROM inventory"
            mock_gemini_func.assert_called_once_with("Show inventory", schema_info)

    @patch('core.llm_processor.generate_sql_with_gemini')
    def test_generate_sql_only_gemini_key(self, mock_gemini_func):
        # Test when only Gemini key exists
        mock_gemini_func.return_value = "SELECT * FROM sales"

        with patch.dict(os.environ, {'GEMINI_API_KEY': 'gemini-key'}, clear=True):
            request = QueryRequest(query="Show sales data", llm_provider="anthropic")
            schema_info = {'tables': {}}

            result = generate_sql(request, schema_info)

            assert result == "SELECT * FROM sales"
            mock_gemini_func.assert_called_once_with("Show sales data", schema_info)

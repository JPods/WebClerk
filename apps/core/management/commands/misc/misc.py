"""
Miscellaneous utility functions for WebClerk3.

This module serves as a "junk drawer" for utility functions that don't fit
neatly into other specialized modules. It includes adaptations from WebClerk2
functions and general-purpose helpers.

Functions are organized by category and include docstrings with WebClerk2
origins where applicable.
"""

# Standard library imports
import os
import re
from typing import Any, Dict, List, Optional, Union

# Third-party imports
# Add imports as needed for specific utilities

# Django imports
from django.conf import settings
from django.core.files.base import ContentFile


class WebClerk2Utils:
    """
    Collection of utility functions adapted from WebClerk2.

    This class groups related functions and provides a namespace
    to avoid polluting the module level.
    """

    @staticmethod
    def validate_filename_length(filename: str, max_length: int = 255) -> bool:
        """
        Validate filename length (adapted from UTFileNameLength.4dm).

        Args:
            filename: The filename to validate
            max_length: Maximum allowed length (default: 255 for most filesystems)

        Returns:
            bool: True if filename is within length limits
        """
        return len(filename) <= max_length

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Sanitize filename for safe storage.

        Removes or replaces unsafe characters, truncates if too long.

        Args:
            filename: Original filename

        Returns:
            str: Sanitized filename
        """
        # Remove or replace unsafe characters
        safe_name = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # Remove leading/trailing whitespace and dots
        safe_name = safe_name.strip(' .')
        # Truncate if too long
        if len(safe_name) > 255:
            name, ext = os.path.splitext(safe_name)
            safe_name = name[:255-len(ext)] + ext
        return safe_name or 'unnamed_file'

    @staticmethod
    def generate_barcode_data(product_id: str, format_type: str = 'CODE128') -> str:
        """
        Generate barcode data string (adapted from BarCodeBuild.4dm).

        Args:
            product_id: Product identifier
            format_type: Barcode format (CODE128, EAN13, etc.)

        Returns:
            str: Formatted barcode data
        """
        # Basic implementation - extend based on specific barcode requirements
        if format_type == 'CODE128':
            return f"({product_id})"
        elif format_type == 'EAN13':
            # Pad to 12 digits, calculate check digit
            padded = product_id.zfill(12)
            # Simple check digit calculation (real implementation would be more complex)
            check_digit = sum(int(d) for d in padded) % 10
            return padded + str(check_digit)
        else:
            return product_id

    @staticmethod
    def extract_keywords_from_text(text: str) -> List[str]:
        """
        Extract keywords from text content (adapted from Key_Search.4dm).

        Basic implementation - can be enhanced with NLP libraries.

        Args:
            text: Text content to analyze

        Returns:
            List[str]: Extracted keywords
        """
        # Simple word frequency analysis
        words = re.findall(r'\b\w+\b', text.lower())
        # Filter out common stop words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        keywords = [word for word in words if word not in stop_words and len(word) > 2]
        # Return unique keywords sorted by frequency
        from collections import Counter
        return [word for word, _ in Counter(keywords).most_common(10)]

    @staticmethod
    def format_currency_amount(amount: Union[float, int], currency_code: str = 'USD') -> str:
        """
        Format currency amount for display.

        Args:
            amount: Numeric amount
            currency_code: ISO currency code

        Returns:
            str: Formatted currency string
        """
        # Basic formatting - can be enhanced with babel or similar
        return f"{currency_code} {amount:,.2f}"

    @staticmethod
    def calculate_percentage_change(old_value: float, new_value: float) -> float:
        """
        Calculate percentage change between two values.

        Args:
            old_value: Original value
            new_value: New value

        Returns:
            float: Percentage change (positive for increase, negative for decrease)
        """
        if old_value == 0:
            return 0.0 if new_value == 0 else (100.0 if new_value > 0 else -100.0)
        return ((new_value - old_value) / abs(old_value)) * 100.0

    @staticmethod
    def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
        """
        Safely divide two numbers, returning default if denominator is zero.

        Args:
            numerator: Number to divide
            denominator: Number to divide by
            default: Value to return if denominator is zero

        Returns:
            float: Division result or default
        """
        try:
            return numerator / denominator if denominator != 0 else default
        except (ZeroDivisionError, TypeError):
            return default

    @staticmethod
    def truncate_text(text: str, max_length: int, suffix: str = '...') -> str:
        """
        Truncate text to maximum length with optional suffix.

        Args:
            text: Text to truncate
            max_length: Maximum length including suffix
            suffix: Suffix to append if truncated

        Returns:
            str: Truncated text
        """
        if len(text) <= max_length:
            return text
        return text[:max_length - len(suffix)] + suffix

    @staticmethod
    def merge_dicts(*dicts: Dict[str, Any], deep: bool = False) -> Dict[str, Any]:
        """
        Merge multiple dictionaries.

        Args:
            *dicts: Dictionaries to merge
            deep: If True, perform deep merge for nested dicts

        Returns:
            Dict[str, Any]: Merged dictionary
        """
        if not deep:
            result = {}
            for d in dicts:
                result.update(d)
            return result
        else:
            # Deep merge implementation
            from collections import defaultdict
            result = defaultdict(dict)
            for d in dicts:
                for key, value in d.items():
                    if isinstance(value, dict) and isinstance(result[key], dict):
                        result[key] = WebClerk2Utils.merge_dicts(result[key], value, deep=True)
                    else:
                        result[key] = value
            return dict(result)


# Convenience functions for direct import
def validate_filename_length(filename: str, max_length: int = 255) -> bool:
    """Convenience wrapper for WebClerk2Utils.validate_filename_length"""
    return WebClerk2Utils.validate_filename_length(filename, max_length)


def sanitize_filename(filename: str) -> str:
    """Convenience wrapper for WebClerk2Utils.sanitize_filename"""
    return WebClerk2Utils.sanitize_filename(filename)


def generate_barcode_data(product_id: str, format_type: str = 'CODE128') -> str:
    """Convenience wrapper for WebClerk2Utils.generate_barcode_data"""
    return WebClerk2Utils.generate_barcode_data(product_id, format_type)


def extract_keywords_from_text(text: str) -> List[str]:
    """Convenience wrapper for WebClerk2Utils.extract_keywords_from_text"""
    return WebClerk2Utils.extract_keywords_from_text(text)


def format_currency_amount(amount: Union[float, int], currency_code: str = 'USD') -> str:
    """Convenience wrapper for WebClerk2Utils.format_currency_amount"""
    return WebClerk2Utils.format_currency_amount(amount, currency_code)


def calculate_percentage_change(old_value: float, new_value: float) -> float:
    """Convenience wrapper for WebClerk2Utils.calculate_percentage_change"""
    return WebClerk2Utils.calculate_percentage_change(old_value, new_value)


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Convenience wrapper for WebClerk2Utils.safe_divide"""
    return WebClerk2Utils.safe_divide(numerator, denominator, default)


def truncate_text(text: str, max_length: int, suffix: str = '...') -> str:
    """Convenience wrapper for WebClerk2Utils.truncate_text"""
    return WebClerk2Utils.truncate_text(text, max_length, suffix)


def merge_dicts(*dicts: Dict[str, Any], deep: bool = False) -> Dict[str, Any]:
    """Convenience wrapper for WebClerk2Utils.merge_dicts"""
    return WebClerk2Utils.merge_dicts(*dicts, deep=deep)
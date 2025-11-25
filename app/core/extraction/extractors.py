"""Data extraction utilities for parsing user input"""

import re
from typing import Optional


class DataExtractor:
    """Extract structured data from user messages"""
    
    @staticmethod
    def extract_name(text: str) -> Optional[str]:
        """
        Extract name from text.
        
        Args:
            text: User input text
            
        Returns:
            Extracted name or None
        """
        text = text.strip()
        
        # Remove common filler words and phrases
        patterns_to_remove = [
            r'\b(um|uh|like|so|well|okay|ok|my|name|is|i\'m|i\s+am|call\s+me|it\'s|this\s+is|the\s+name\s+is)\b',
        ]
        
        for pattern in patterns_to_remove:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Clean up extra spaces
        text = re.sub(r'\s+', ' ', text).strip()
        
        # If empty after cleaning, return None
        if not text:
            return None
        
        # Check if it looks like a name (letters, spaces, hyphens, apostrophes)
        if re.match(r'^[A-Za-z\s\-\'\.]+$', text):
            words = text.split()
            if 1 <= len(words) <= 5:
                # Capitalize properly
                return ' '.join(word.capitalize() for word in words)
        
        return None
    
    @staticmethod
    def extract_phone(text: str) -> Optional[str]:
        """
        Extract phone number from text.
        
        Args:
            text: User input text
            
        Returns:
            Extracted phone number or None
        """
        # Remove common filler words
        text = re.sub(
            r'\b(my|number|is|phone|cell|mobile|it\'s|its)\b', 
            '', 
            text, 
            flags=re.IGNORECASE
        )
        
        # Various phone patterns
        patterns = [
            r'(\+?237[-.\s]?\d{2}[-.\s]?\d{3}[-.\s]?\d{3})',  # Cameroon format
            r'(\+?27[-.\s]?\d{2}[-.\s]?\d{3}[-.\s]?\d{4})',   # South Africa
            r'(\+?1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})',  # US/Canada
            r'(0\d{2}[-.\s]?\d{3}[-.\s]?\d{4})',              # Local format
            r'(\d{9,12})',                                      # Just digits
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                phone = match.group(1)
                # Normalize: keep only digits and +
                digits = re.sub(r'[^\d+]', '', phone)
                if len(digits) >= 9:
                    return digits
        
        return None
    
    @staticmethod
    def extract_amount(text: str) -> Optional[float]:
        """
        Extract monetary amount from text.
        
        Args:
            text: User input text
            
        Returns:
            Extracted amount or None
        """
        text = text.lower().strip()
        
        # Patterns for amount extraction (XAF, FCFA, or just numbers)
        patterns = [
            r'(\d+(?:[.,]\d+)?)\s*(?:xaf|fcfa|francs?|cfa)',  # 1000 XAF
            r'(?:xaf|fcfa|cfa)\s*(\d+(?:[.,]\d+)?)',          # XAF 1000
            r'[R$€£]\s*(\d+(?:[.,]\d+)?)',                     # R100, $100
            r'(\d+(?:[.,]\d+)?)\s*(?:dollars?|rand|usd)?',    # 100 dollars
            r'(\d+(?:[.,]\d+)?)',                              # Just numbers
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                amount_str = match.group(1).replace(',', '.')
                try:
                    amount = float(amount_str)
                    if amount > 0:
                        return amount
                except ValueError:
                    continue
        
        return None
    
    @staticmethod
    def is_confirmation(text: str) -> Optional[bool]:
        """
        Check if text is a confirmation or denial.
        
        Args:
            text: User input text
            
        Returns:
            True for confirmation, False for denial, None if unclear
        """
        text_lower = text.lower().strip()
        
        confirmations = [
            'yes', 'yeah', 'yep', 'yup', 'correct', 'confirm', 'sure',
            'ok', 'okay', 'proceed', 'oui', 'right', 'affirmative',
            'absolutely', 'definitely', 'of course', 'go ahead'
        ]
        
        denials = [
            'no', 'nope', 'nah', 'cancel', 'stop', 'wrong', 'incorrect',
            'nevermind', 'never mind', 'non', 'negative', 'forget it',
            'not right', 'that\'s wrong'
        ]
        
        for word in confirmations:
            if word in text_lower:
                return True
        
        for word in denials:
            if word in text_lower:
                return False
        
        return None
    
    @staticmethod
    def extract_email(text: str) -> Optional[str]:
        """
        Extract email address from text.
        
        Args:
            text: User input text
            
        Returns:
            Extracted email or None
        """
        # Email pattern
        pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        match = re.search(pattern, text)
        
        if match:
            return match.group(0).lower()
        
        return None
    
    @staticmethod
    def normalize_text(text: str) -> str:
        """
        Normalize text for better matching.
        
        Args:
            text: Input text
            
        Returns:
            Normalized text
        """
        text = text.lower().strip()
        # Replace hyphens with spaces
        text = text.replace('-', ' ')
        # Remove extra spaces
        
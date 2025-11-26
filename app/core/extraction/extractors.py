"""Data extraction utilities for parsing user input"""

import re
from typing import Optional


class DataExtractor:
    """Extract structured data from user messages"""
    
    @staticmethod
    def extract_name(text: str) -> Optional[str]:
        """Extract name from text."""
        text = text.strip()
        
        # Remove common filler words
        patterns_to_remove = [
            r'\b(um|uh|like|so|well|okay|ok|my|name|is|i\'m|i\s+am|call\s+me|it\'s|this\s+is|the\s+name\s+is)\b',
        ]
        
        for pattern in patterns_to_remove:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        text = re.sub(r'\s+', ' ', text).strip()
        
        if not text:
            return None
        
        if re.match(r'^[A-Za-z\s\-\'\.]+$', text):
            words = text.split()
            if 1 <= len(words) <= 5:
                return ' '.join(word.capitalize() for word in words)
        
        return None
    
    @staticmethod
    def extract_age(text: str) -> Optional[int]:
        """
        Extract age from text.
        
        Args:
            text: User input text
            
        Returns:
            Extracted age or None
        """
        # Remove common filler words
        text = re.sub(
            r'\b(my|age|is|i\'m|i\s+am|years?|old)\b',
            '',
            text,
            flags=re.IGNORECASE
        )
        
        # Patterns for age extraction
        patterns = [
            r'\b(\d{1,3})\s*(?:years?\s*old)?',  # "25 years old" or "25"
            r'(?:age|aged?)\s*(\d{1,3})',  # "age 25" or "aged 25"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    age = int(match.group(1))
                    # Validate age range (reasonable human age)
                    if 1 <= age <= 150:
                        return age
                except ValueError:
                    continue
        
        # Try to extract just a number if text is simple
        text_stripped = text.strip()
        if text_stripped.isdigit():
            age = int(text_stripped)
            if 1 <= age <= 150:
                return age
        
        return None
    
    @staticmethod
    def extract_sex(text: str) -> Optional[str]:
        """
        Extract sex/gender from text.
        
        Args:
            text: User input text
            
        Returns:
            'M' for male, 'F' for female, or None
        """
        text_lower = text.lower().strip()
        
        # Male indicators
        male_keywords = [
            'male', 'man', 'boy', 'homme', 'masculin',
            'garcon', 'garçon', 'm', 'h'
        ]
        
        # Female indicators
        female_keywords = [
            'female', 'woman', 'girl', 'femme', 'féminin',
            'fille', 'f'
        ]
        
        for keyword in male_keywords:
            if keyword in text_lower or text_lower == keyword:
                return 'M'
        
        for keyword in female_keywords:
            if keyword in text_lower or text_lower == keyword:
                return 'F'
        
        return None
    
    @staticmethod
    def extract_groupement(text: str, groupements: list) -> Optional[int]:
        """
        Extract groupement selection from text.
        
        Args:
            text: User input text
            groupements: List of available groupements
            
        Returns:
            Groupement ID or None
        """
        text_lower = text.lower().strip()
        
        # Try to match by ID
        for groupement in groupements:
            if str(groupement['id']) in text_lower:
                return groupement['id']
        
        # Try to match by name
        for groupement in groupements:
            if groupement['name'].lower() in text_lower:
                return groupement['id']
        
        # Try to match by token
        for groupement in groupements:
            if groupement['token'].lower() in text_lower:
                return groupement['id']
        
        # Try to extract just a number
        if text_lower.isdigit():
            id_num = int(text_lower)
            if any(g['id'] == id_num for g in groupements):
                return id_num
        
        return None
    
    @staticmethod
    def extract_phone(text: str) -> Optional[str]:
        """Extract phone number from text."""
        text = re.sub(r'\b(my|number|is|phone|cell|mobile|it\'s|its)\b', '', text, flags=re.IGNORECASE)
        
        patterns = [
            r'(\+?237[-.\s]?\d{2}[-.\s]?\d{3}[-.\s]?\d{3})',
            r'(\+?27[-.\s]?\d{2}[-.\s]?\d{3}[-.\s]?\d{4})',
            r'(\+?1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})',
            r'(0\d{2}[-.\s]?\d{3}[-.\s]?\d{4})',
            r'(\d{9,12})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                phone = match.group(1)
                digits = re.sub(r'[^\d+]', '', phone)
                if len(digits) >= 9:
                    return digits
        
        return None
    
    @staticmethod
    def extract_amount(text: str) -> Optional[float]:
        """Extract monetary amount from text."""
        text = text.lower().strip()
        
        patterns = [
            r'(\d+(?:[.,]\d+)?)\s*(?:xaf|fcfa|francs?|cfa)',
            r'(?:xaf|fcfa|cfa)\s*(\d+(?:[.,]\d+)?)',
            r'[R$€£]\s*(\d+(?:[.,]\d+)?)',
            r'(\d+(?:[.,]\d+)?)\s*(?:dollars?|rand|usd)?',
            r'(\d+(?:[.,]\d+)?)',
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
        """Check if text is a confirmation or denial."""
        text_lower = text.lower().strip()
        
        confirmations = [
            'yes', 'yeah', 'yep', 'yup', 'correct', 'confirm', 'sure',
            'ok', 'okay', 'proceed', 'oui', 'right', 'affirmative',
        ]
        
        denials = [
            'no', 'nope', 'nah', 'cancel', 'stop', 'wrong', 'incorrect',
            'nevermind', 'never mind', 'non', 'negative',
        ]
        
        for word in confirmations:
            if word in text_lower:
                return True
        
        for word in denials:
            if word in text_lower:
                return False
        
        return None
    
    @staticmethod
    def normalize_text(text: str) -> str:
        """Normalize text for better matching."""
        text = text.lower().strip()
        text = text.replace('-', ' ')
        text = re.sub(r'\s+', ' ', text)
        return text
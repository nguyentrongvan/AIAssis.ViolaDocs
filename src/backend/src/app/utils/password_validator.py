"""
Password validation utility with strict requirements
"""
import re
from typing import Dict, List, Tuple


class PasswordValidator:
    """Password validator with strict security requirements"""
    
    MIN_LENGTH = 12
    REQUIRES_UPPERCASE = True
    REQUIRES_LOWERCASE = True
    REQUIRES_DIGIT = True
    REQUIRES_SPECIAL = True
    SPECIAL_CHARS = r'!@#$%^&*()_+\-=\[\]{}|;:,.<>?'
    
    @classmethod
    def validate(cls, password: str) -> Tuple[bool, List[str]]:
        """
        Validate password against strict requirements.
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Check minimum length
        if len(password) < cls.MIN_LENGTH:
            errors.append(f"Password must be at least {cls.MIN_LENGTH} characters long")
        
        # Check uppercase
        if cls.REQUIRES_UPPERCASE and not re.search(r'[A-Z]', password):
            errors.append("Password must contain at least one uppercase letter (A-Z)")
        
        # Check lowercase
        if cls.REQUIRES_LOWERCASE and not re.search(r'[a-z]', password):
            errors.append("Password must contain at least one lowercase letter (a-z)")
        
        # Check digit
        if cls.REQUIRES_DIGIT and not re.search(r'\d', password):
            errors.append("Password must contain at least one digit (0-9)")
        
        # Check special character
        if cls.REQUIRES_SPECIAL:
            special_pattern = f'[{re.escape(cls.SPECIAL_CHARS)}]'
            if not re.search(special_pattern, password):
                errors.append(f"Password must contain at least one special character ({cls.SPECIAL_CHARS})")
        
        return len(errors) == 0, errors
    
    @classmethod
    def get_requirements(cls) -> List[str]:
        """Get list of password requirements for display"""
        requirements = [
            f"At least {cls.MIN_LENGTH} characters",
            "At least one uppercase letter (A-Z)",
            "At least one lowercase letter (a-z)",
            "At least one digit (0-9)",
            f"At least one special character ({cls.SPECIAL_CHARS})"
        ]
        return requirements
    
    @classmethod
    def check_strength(cls, password: str) -> str:
        """
        Check password strength (weak/medium/strong).
        
        Returns:
            'weak', 'medium', or 'strong'
        """
        if len(password) < cls.MIN_LENGTH:
            return 'weak'
        
        score = 0
        
        # Length bonus
        if len(password) >= 16:
            score += 2
        elif len(password) >= cls.MIN_LENGTH:
            score += 1
        
        # Character variety
        if re.search(r'[A-Z]', password):
            score += 1
        if re.search(r'[a-z]', password):
            score += 1
        if re.search(r'\d', password):
            score += 1
        special_pattern = f'[{re.escape(cls.SPECIAL_CHARS)}]'
        if re.search(special_pattern, password):
            score += 1
        
        # Determine strength
        if score >= 5:
            return 'strong'
        elif score >= 3:
            return 'medium'
        else:
            return 'weak'


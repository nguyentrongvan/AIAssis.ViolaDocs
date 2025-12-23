"""
User Preferences Service for managing user-specific theme and UI preferences
"""
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..models.user_preferences import UserPreferences
from ..models.users import User


class UserPreferencesService:
    """Service for managing user preferences"""
    
    @staticmethod
    async def get_preferences(
        user_id: int,
        session: AsyncSession
    ) -> Optional[UserPreferences]:
        """Get user preferences by user_id"""
        result = await session.execute(
            select(UserPreferences).where(UserPreferences.user_id == user_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_or_create_preferences(
        user_id: int,
        session: AsyncSession
    ) -> UserPreferences:
        """Get user preferences or create default if not exists"""
        preferences = await UserPreferencesService.get_preferences(user_id, session)
        
        if not preferences:
            preferences = UserPreferences(
                user_id=user_id,
                primary_color=None,  # Use default from theme.css
                font_size="medium",
                border_radius="medium",
                animation_speed="normal",
                compact_mode=False
            )
            session.add(preferences)
            await session.flush()
        
        return preferences
    
    @staticmethod
    async def update_preferences(
        user_id: int,
        session: AsyncSession,
        primary_color: Optional[str] = None,
        font_size: Optional[str] = None,
        border_radius: Optional[str] = None,
        animation_speed: Optional[str] = None,
        compact_mode: Optional[bool] = None
    ) -> UserPreferences:
        """Update user preferences"""
        preferences = await UserPreferencesService.get_or_create_preferences(user_id, session)
        
        if primary_color is not None:
            preferences.primary_color = primary_color
        if font_size is not None:
            preferences.font_size = font_size
        if border_radius is not None:
            preferences.border_radius = border_radius
        if animation_speed is not None:
            preferences.animation_speed = animation_speed
        if compact_mode is not None:
            preferences.compact_mode = compact_mode
        
        await session.commit()
        await session.refresh(preferences)
        
        return preferences
    
    @staticmethod
    def calculate_theme_colors(primary_color: str) -> Dict[str, str]:
        """
        Calculate derived theme colors from primary color.
        Returns a dictionary of CSS variable values.
        """
        if not primary_color or not primary_color.startswith('#'):
            return {}
        
        # Parse hex color
        hex_color = primary_color.lstrip('#')
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        
        # Calculate dark variant (darken by 20%)
        dark_r = max(0, int(r * 0.8))
        dark_g = max(0, int(g * 0.8))
        dark_b = max(0, int(b * 0.8))
        primary_dark = f"#{dark_r:02x}{dark_g:02x}{dark_b:02x}"
        
        # Calculate light variant (lighten by 30%)
        light_r = min(255, int(r + (255 - r) * 0.3))
        light_g = min(255, int(g + (255 - g) * 0.3))
        light_b = min(255, int(b + (255 - b) * 0.3))
        primary_light = f"#{light_r:02x}{light_g:02x}{light_b:02x}"
        
        # Generate gradient end (slightly different hue)
        # Shift hue slightly for gradient
        gradient_end_r = min(255, int(r * 1.1))
        gradient_end_g = min(255, int(g * 0.95))
        gradient_end_b = min(255, int(b * 1.15))
        gradient_end = f"#{min(255, gradient_end_r):02x}{min(255, gradient_end_g):02x}{min(255, gradient_end_b):02x}"
        
        return {
            "primary": primary_color,
            "primary-dark": primary_dark,
            "primary-light": primary_light,
            "gradient-start": primary_color,
            "gradient-end": gradient_end,
            "gradient-primary": f"linear-gradient(135deg, {primary_color} 0%, {gradient_end} 100%)",
            "gradient-cyan-purple": f"linear-gradient(135deg, #00D9FF 0%, {primary_color} 100%)",
            "gradient-purple-pink": f"linear-gradient(135deg, {primary_color} 0%, #EC4899 100%)",
        }


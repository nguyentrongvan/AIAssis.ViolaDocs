"""
Settings Service for managing system settings in database
"""
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..models.settings import SystemSettings
from ..db import AsyncSessionLocal


class SettingsService:
    """Service for managing system settings"""
    
    _cache: Dict[str, Any] = {}
    _cache_loaded: bool = False
    
    @classmethod
    async def get_setting(
        cls, 
        key: str, 
        default: Any = None,
        session: Optional[AsyncSession] = None
    ) -> Any:
        """Get a single setting by key"""
        # Check cache first
        if cls._cache_loaded and key in cls._cache:
            return cls._cache[key]
        
        # Query database
        if session is None:
            async with AsyncSessionLocal() as sess:
                return await cls._get_setting_from_db(key, default, sess)
        else:
            return await cls._get_setting_from_db(key, default, session)
    
    @classmethod
    async def _get_setting_from_db(
        cls,
        key: str,
        default: Any,
        session: AsyncSession
    ) -> Any:
        """Get setting from database"""
        result = await session.execute(
            select(SystemSettings).where(SystemSettings.key == key)
        )
        setting = result.scalar_one_or_none()
        
        if setting:
            value = setting.value
            # Update cache
            cls._cache[key] = value
            return value
        return default
    
    @classmethod
    async def set_setting(
        cls,
        key: str,
        value: Any,
        category: str,
        description: Optional[str] = None,
        sensitive: bool = False,
        user_id: Optional[int] = None,
        session: Optional[AsyncSession] = None
    ) -> SystemSettings:
        """Set or update a setting"""
        if session is None:
            async with AsyncSessionLocal() as sess:
                return await cls._set_setting_in_db(
                    key, value, category, description, sensitive, user_id, sess
                )
        else:
            return await cls._set_setting_in_db(
                key, value, category, description, sensitive, user_id, session
            )
    
    @classmethod
    async def _set_setting_in_db(
        cls,
        key: str,
        value: Any,
        category: str,
        description: Optional[str],
        sensitive: bool,
        user_id: Optional[int],
        session: AsyncSession
    ) -> SystemSettings:
        """Set setting in database"""
        result = await session.execute(
            select(SystemSettings).where(SystemSettings.key == key)
        )
        setting = result.scalar_one_or_none()
        
        if setting:
            # Update existing
            setting.value = value
            setting.category = category
            if description is not None:
                setting.description = description
            setting.sensitive = sensitive
            if user_id is not None:
                setting.updated_by = user_id
        else:
            # Create new
            setting = SystemSettings(
                key=key,
                value=value,
                category=category,
                description=description,
                sensitive=sensitive,
                updated_by=user_id
            )
            session.add(setting)
        
        await session.commit()
        await session.refresh(setting)
        
        # Update cache
        cls._cache[key] = value
        cls._cache_loaded = True
        
        return setting
    
    @classmethod
    async def get_settings_by_category(
        cls,
        category: str,
        session: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """Get all settings in a category"""
        if session is None:
            async with AsyncSessionLocal() as sess:
                return await cls._get_settings_by_category_from_db(category, sess)
        else:
            return await cls._get_settings_by_category_from_db(category, session)
    
    @classmethod
    async def _get_settings_by_category_from_db(
        cls,
        category: str,
        session: AsyncSession
    ) -> Dict[str, Any]:
        """Get settings by category from database"""
        result = await session.execute(
            select(SystemSettings).where(SystemSettings.category == category)
        )
        settings = result.scalars().all()
        
        return {setting.key: setting.value for setting in settings}
    
    @classmethod
    async def get_all_settings(
        cls,
        session: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """Get all settings"""
        if session is None:
            async with AsyncSessionLocal() as sess:
                return await cls._get_all_settings_from_db(sess)
        else:
            return await cls._get_all_settings_from_db(session)
    
    @classmethod
    async def _get_all_settings_from_db(
        cls,
        session: AsyncSession
    ) -> Dict[str, Any]:
        """Get all settings from database"""
        result = await session.execute(select(SystemSettings))
        settings = result.scalars().all()
        
        return {setting.key: setting.value for setting in settings}
    
    @classmethod
    async def delete_setting(
        cls,
        key: str,
        session: Optional[AsyncSession] = None
    ) -> bool:
        """Delete a setting"""
        if session is None:
            async with AsyncSessionLocal() as sess:
                return await cls._delete_setting_from_db(key, sess)
        else:
            return await cls._delete_setting_from_db(key, session)
    
    @classmethod
    async def _delete_setting_from_db(
        cls,
        key: str,
        session: AsyncSession
    ) -> bool:
        """Delete setting from database"""
        result = await session.execute(
            select(SystemSettings).where(SystemSettings.key == key)
        )
        setting = result.scalar_one_or_none()
        
        if setting:
            await session.delete(setting)
            await session.commit()
            # Remove from cache
            if key in cls._cache:
                del cls._cache[key]
            return True
        return False
    
    @classmethod
    async def load_cache(cls, session: Optional[AsyncSession] = None):
        """Load all settings into cache"""
        all_settings = await cls.get_all_settings(session)
        cls._cache.update(all_settings)
        cls._cache_loaded = True
    
    @classmethod
    def clear_cache(cls):
        """Clear the settings cache"""
        cls._cache.clear()
        cls._cache_loaded = False


# Convenience functions
async def get_setting(key: str, default: Any = None) -> Any:
    """Get a setting"""
    return await SettingsService.get_setting(key, default)


async def set_setting(
    key: str,
    value: Any,
    category: str,
    description: Optional[str] = None,
    sensitive: bool = False,
    user_id: Optional[int] = None
) -> SystemSettings:
    """Set a setting"""
    return await SettingsService.set_setting(
        key, value, category, description, sensitive, user_id
    )



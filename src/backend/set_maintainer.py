"""
Script to set is_maintainer flag for a user
Usage: python set_maintainer.py <user_email> [--remove]
"""
import asyncio
import sys
import warnings
from pathlib import Path

# Suppress asyncio warnings on Windows (ProactorEventLoop cleanup)
warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*Event loop is closed.*")

# Add src to path
backend_dir = Path(__file__).parent
src_dir = backend_dir / "src"
sys.path.insert(0, str(src_dir))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.models.users import User

async def set_maintainer(email: str, is_maintainer: bool = True):
    """Set is_maintainer flag for a user"""
    engine = create_async_engine(settings.postgres_async_dsn)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    try:
        async with async_session() as session:
            result = await session.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()
            
            if not user:
                print(f"Error: User with email '{email}' not found")
                return False
            
            user.is_maintainer = is_maintainer
            await session.commit()
            
            status = "granted" if is_maintainer else "revoked"
            print(f"Successfully {status} maintainer access for user: {user.name} ({user.email})")
            return True
    finally:
        # Properly close the engine to avoid event loop warnings
        await engine.dispose()

async def main():
    if len(sys.argv) < 2:
        print("Usage: python set_maintainer.py <user_email> [--remove]")
        sys.exit(1)
    
    email = sys.argv[1]
    is_maintainer = "--remove" not in sys.argv
    
    await set_maintainer(email, is_maintainer)

if __name__ == "__main__":
    # Use asyncio.run() which properly handles event loop cleanup
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


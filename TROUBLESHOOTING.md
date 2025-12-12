# Troubleshooting Guide

## Không thể login vào hệ thống

### 1. Kiểm tra Backend có đang chạy không

```bash
# Kiểm tra backend có đang chạy
curl http://localhost:8000/api/v1/health

# Hoặc mở browser
http://localhost:8000/docs
```

Nếu không có response, backend chưa chạy. Hãy start backend:

```bash
cd src/backend
python run.py
# hoặc
uvicorn src.app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Kiểm tra Frontend có đang chạy không

```bash
cd src/frontend
npm run dev
```

Frontend sẽ chạy tại: http://localhost:5173 (hoặc port khác nếu 5173 đã được dùng)

### 3. Kiểm tra Admin User có tồn tại không

```bash
cd src/backend
.\venv\Scripts\activate
python create_admin.py
```

Nếu admin user chưa tồn tại, script sẽ tạo user với:
- **Email**: admin@example.com
- **Password**: admin123

### 4. Test Login API trực tiếp

```bash
# Sử dụng curl
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "admin123"}'

# Hoặc sử dụng PowerShell
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/auth/login" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"email": "admin@example.com", "password": "admin123"}'
```

Response mong đợi:
```json
{
  "is_success": true,
  "message": "Success",
  "status_code": 200,
  "data": {
    "access_token": "...",
    "refresh_token": "...",
    "token_type": "bearer"
  }
}
```

### 5. Kiểm tra CORS Configuration

Đảm bảo trong `src/backend/src/app/main.py` có CORS config cho frontend port:

```python
allow_origins=[
    "http://localhost:3000",
    "http://localhost:5173",  # Vite default port
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
]
```

### 6. Kiểm tra API Base URL trong Frontend

Đảm bảo trong `src/frontend/src/services/api.js`:

```javascript
const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000/api/v1'
```

Hoặc tạo file `.env` trong `src/frontend/`:

```env
VITE_API_BASE=http://localhost:8000/api/v1
```

### 7. Kiểm tra Browser Console

Mở Browser DevTools (F12) và kiểm tra:
- **Console tab**: Xem có lỗi JavaScript không
- **Network tab**: Xem request đến `/auth/login` có thành công không
  - Status code phải là 200
  - Response phải có `is_success: true`

### 8. Reset Password cho Admin User

Nếu quên password, có thể reset bằng script:

```python
# Tạo file reset_password.py trong src/backend/
import asyncio
from sqlalchemy import select
from app.db import AsyncSessionLocal
from app.models.users import User
from app.services.auth import get_password_hash

async def reset_admin_password():
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.email == "admin@example.com")
        )
        user = result.scalar_one_or_none()
        
        if not user:
            print("Admin user not found!")
            return
        
        # Reset password to admin123
        user.password_hash = get_password_hash("admin123")
        await session.commit()
        print("✅ Password reset successfully!")
        print("   Email: admin@example.com")
        print("   Password: admin123")

if __name__ == "__main__":
    asyncio.run(reset_admin_password())
```

### 9. Kiểm tra Database Connection

Đảm bảo database đang chạy:

```bash
# Nếu dùng PostgreSQL trong Docker
docker-compose ps

# Kiểm tra connection string trong .env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/vandms
```

### 10. Common Issues

#### Issue: "Cannot connect to server"
- **Nguyên nhân**: Backend không chạy hoặc sai port
- **Giải pháp**: Start backend server

#### Issue: "Invalid email or password"
- **Nguyên nhân**: Sai email/password hoặc user không tồn tại
- **Giải pháp**: Chạy `create_admin.py` để tạo admin user

#### Issue: CORS Error
- **Nguyên nhân**: Frontend và Backend không cùng origin
- **Giải pháp**: Kiểm tra CORS config trong `main.py`

#### Issue: 401 Unauthorized
- **Nguyên nhân**: Token không hợp lệ hoặc đã hết hạn
- **Giải pháp**: Clear localStorage và login lại

## Default Credentials

Sau khi chạy `create_admin.py`:
- **Email**: admin@example.com
- **Password**: admin123

⚠️ **Lưu ý**: Đổi password sau lần đăng nhập đầu tiên!


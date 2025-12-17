"""
Permission service for checking document access rights.

This service provides centralized logic for checking document permissions,
including owner access, admin/staff access, shares, and role-based permissions.
"""
from typing import Optional, Tuple, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload

from ..models.users import User
from ..models.documents import Document, Share, FolderShare, Folder
from ..models.roles import Role


async def check_folder_access(
    session: AsyncSession,
    user: User,
    folder_id: int
) -> Tuple[bool, Optional[str]]:
    """
    Check if user has access to a folder.
    
    Returns:
        Tuple of (has_access: bool, reason: Optional[str])
        - has_access: True if user has access to folder
        - reason: Reason for access denial if has_access is False, None otherwise
    
    Permission hierarchy:
    1. Folder owner always has access
    2. Admin/staff always have access
    3. Check FolderShare with target_type="user" and target_id=user.id
    4. Check FolderShare with target_type="role" - match with User.roles
    """
    # Get folder
    folder_result = await session.execute(
        select(Folder).where(Folder.id == folder_id)
    )
    folder = folder_result.scalar_one_or_none()
    
    if not folder:
        return False, "Folder not found"
    
    # 1. Folder owner always has access
    if folder.owner_id == user.id:
        return True, None
    
    # 2. Admin/staff always have access
    if user.role in ["admin", "staff"]:
        return True, None
    
    # 3. Check folder shares
    now = datetime.utcnow()
    folder_shares_result = await session.execute(
        select(FolderShare).where(
            and_(
                FolderShare.folder_id == folder_id,
                or_(
                    FolderShare.expires_at.is_(None),
                    FolderShare.expires_at > now
                )
            )
        )
    )
    folder_shares = folder_shares_result.scalars().all()
    
    # Check user-specific folder shares
    for folder_share in folder_shares:
        if folder_share.target_type == "user" and folder_share.target_id == user.id:
            return True, None
    
    # 4. Check role-based folder shares
    user_role_names = await get_user_role_names(session, user)
    
    for folder_share in folder_shares:
        if folder_share.target_type == "role":
            # For role shares, target_id is the role_id
            # We need to get the role name from the role_id
            role_result = await session.execute(
                select(Role).where(Role.id == folder_share.target_id)
            )
            role = role_result.scalar_one_or_none()
            
            if role and role.name in user_role_names:
                return True, None
    
    return False, "Access denied: insufficient folder permissions"


async def check_document_access(
    session: AsyncSession,
    user: User,
    document: Document,
    required_permission: str = "view"  # view, search, chat
) -> Tuple[bool, Optional[Share], Optional[str]]:
    """
    Check if user has required permission to access a document.
    
    Document-level permissions:
    - view: Xem tài liệu (get_document, list_versions, get_rendition, comments)
    - search: Tài liệu khả dụng trong search (nếu không có thì không search ra được)
    - chat: Tài liệu và vectorDB khả dụng cho chatbot (nếu không có thì bot không trả về thông tin từ tài liệu này)
    
    Returns:
        Tuple of (has_access: bool, share: Optional[Share], reason: Optional[str])
        - has_access: True if user has the required permission
        - share: The Share object if access is granted via share, None otherwise
        - reason: Reason for access denial if has_access is False, None otherwise
    
    Permission hierarchy:
    1. Owner always has full access (view, search, chat)
    2. Admin/staff always have full access
    3. **CRITICAL**: Check folder share FIRST (if document has folder_id)
    4. Check Share with target_type="user" and target_id=user.id
    5. Check Share with target_type="role" - match with User.roles
    6. Check permissions in Share (view/search/chat)
    """
    # 1. Owner always has full access (view, search, chat)
    if document.owner_id == user.id:
        return True, None, None
    
    # 2. Admin/staff always have full access (view, search, chat)
    if user.role in ["admin", "staff"]:
        return True, None, None
    
    # 3. **CRITICAL**: Check folder share FIRST (before document shares)
    # If document is in a folder and user has folder access, grant full access
    if document.folder_id:
        has_folder_access, _ = await check_folder_access(session, user, document.folder_id)
        if has_folder_access:
            # User has folder access, grant full access to document
            # Return immediately without checking document-level shares
            return True, None, None
    
    # 4. Check document-level shares (only if no folder access)
    now = datetime.utcnow()
    shares_result = await session.execute(
        select(Share).where(
            and_(
                Share.document_id == document.id,
                or_(
                    Share.expires_at.is_(None),
                    Share.expires_at > now
                )
            )
        )
    )
    shares = shares_result.scalars().all()
    
    # Check user-specific document shares
    for share in shares:
        if share.target_type == "user" and share.target_id == user.id:
            # Check if share has required permission
            share_permissions = share.permissions or []
            
            # Handle both old format (read/write/delete) and new format (view/search/chat)
            # For backward compatibility, map old permissions to new ones
            if isinstance(share_permissions, str):
                share_permissions = [share_permissions]
            elif isinstance(share_permissions, dict):
                # If it's a dict (for role shares), extract permissions
                share_permissions = share_permissions.get("permissions", [])
                if isinstance(share_permissions, str):
                    share_permissions = [share_permissions]
            
            # Map old permissions to new ones for backward compatibility
            normalized_permissions = []
            for perm in share_permissions:
                if perm == "read":
                    normalized_permissions.append("view")
                elif perm == "write":
                    normalized_permissions.extend(["view", "search"])
                elif perm == "delete":
                    normalized_permissions.extend(["view", "search", "chat"])
                else:
                    normalized_permissions.append(perm)
            
            # Check if share has required permission
            if required_permission in normalized_permissions:
                return True, share, None
    
    # 5. Check role-based document shares
    # Always query roles from database to avoid lazy loading issues in async context
    user_role_names = await get_user_role_names(session, user)
    
    for share in shares:
        if share.target_type == "role":
            # For role shares, we need to check if the role name is stored in metadata
            # Since permissions is JSON, we can use it to store role_name
            # Check if share has role_name in permissions or metadata
            share_permissions = share.permissions or []
            
            # Try to get role name from permissions (if it's a dict with role_name)
            role_name = None
            if isinstance(share_permissions, dict):
                role_name = share_permissions.get("role_name")
                # Extract actual permissions
                actual_permissions = share_permissions.get("permissions", [])
                if isinstance(actual_permissions, str):
                    actual_permissions = [actual_permissions]
            elif isinstance(share_permissions, list):
                # If permissions is a list, check if first element is role name (legacy)
                # This is a workaround for existing data
                actual_permissions = share_permissions
            else:
                actual_permissions = []
            
            # Check if user has this role
            if role_name and role_name in user_role_names:
                # Check if share has required permission
                if isinstance(actual_permissions, str):
                    actual_permissions = [actual_permissions]
                
                # Map old permissions to new ones for backward compatibility
                normalized_permissions = []
                for perm in actual_permissions:
                    if perm == "read":
                        normalized_permissions.append("view")
                    elif perm == "write":
                        normalized_permissions.extend(["view", "search"])
                    elif perm == "delete":
                        normalized_permissions.extend(["view", "search", "chat"])
                    else:
                        normalized_permissions.append(perm)
                
                # Check if share has required permission
                if required_permission in normalized_permissions:
                    return True, share, None
    
    # 6. Check Role permissions (if document is in a group with role-based access)
    # This would require checking DocumentGroup.allowed_roles
    # For now, we'll skip this as it's handled at the group level in chat
    
    return False, None, "Access denied: insufficient permissions"


async def get_user_accessible_documents_query(
    session: AsyncSession,
    user: User,
    base_query=None
):
    """
    Create a query that returns all documents accessible by the user.
    
    This includes:
    - Documents owned by the user
    - Documents shared with the user (via user shares)
    - Documents shared with user's roles (via role shares)
    - Documents in folders shared with the user (via folder shares)
    
    Note: This function needs to be async because it loads user roles.
    For role-based shares, we need to check shares separately as the role
    information is stored in JSON metadata.
    
    Important: This query is used for LISTING documents, not for checking individual document access.
    Individual document access is still checked via check_document_access() with proper hierarchy.
    
    Args:
        session: Database session
        user: User object
        base_query: Optional base query to extend (defaults to select(Document))
    
    Returns:
        SQLAlchemy query object
    """
    from sqlalchemy import select as sql_select
    
    if base_query is None:
        base_query = sql_select(Document)
    
    now = datetime.utcnow()
    
    # Base condition: documents not deleted
    conditions = [Document.deleted_at.is_(None)]
    
    # Owner condition
    owner_condition = Document.owner_id == user.id
    
    # Admin/staff condition
    if user.role in ["admin", "staff"]:
        # Admin/staff can see all non-deleted documents
        return base_query.where(and_(*conditions))
    
    # Get user's role names
    user_role_names = await get_user_role_names(session, user)
    
    # Get document IDs from user shares
    user_share_condition = and_(
        Share.target_type == "user",
        Share.target_id == user.id,
        or_(
            Share.expires_at.is_(None),
            Share.expires_at > now
        )
    )
    user_shared_doc_ids_query = sql_select(Share.document_id).where(user_share_condition)
    
    # Get document IDs from role shares
    # We need to check all role shares and see if any match user's roles
    role_shares_result = await session.execute(
        select(Share).where(
            and_(
                Share.target_type == "role",
                or_(
                    Share.expires_at.is_(None),
                    Share.expires_at > now
                )
            )
        )
    )
    role_shares = role_shares_result.scalars().all()
    
    role_shared_doc_ids = []
    for share in role_shares:
        share_permissions = share.permissions or {}
        if isinstance(share_permissions, dict):
            role_name = share_permissions.get("role_name")
        else:
            # Legacy: try to get role name from permissions if it's stored differently
            role_name = None
        
        # If we can't determine role name from share, skip it
        # In practice, role shares should have role_name in metadata
        if role_name and role_name in user_role_names:
            role_shared_doc_ids.append(share.document_id)
    
    # Get folder IDs from folder shares (user-specific)
    user_folder_share_condition = and_(
        FolderShare.target_type == "user",
        FolderShare.target_id == user.id,
        or_(
            FolderShare.expires_at.is_(None),
            FolderShare.expires_at > now
        )
    )
    user_shared_folder_ids_query = sql_select(FolderShare.folder_id).where(user_folder_share_condition)
    
    # Get folder IDs from folder shares (role-based)
    role_folder_shares_result = await session.execute(
        select(FolderShare).where(
            and_(
                FolderShare.target_type == "role",
                or_(
                    FolderShare.expires_at.is_(None),
                    FolderShare.expires_at > now
                )
            )
        )
    )
    role_folder_shares = role_folder_shares_result.scalars().all()
    
    role_shared_folder_ids = []
    for folder_share in role_folder_shares:
        # For role shares, target_id is the role_id
        role_result = await session.execute(
            select(Role).where(Role.id == folder_share.target_id)
        )
        role = role_result.scalar_one_or_none()
        
        if role and role.name in user_role_names:
            role_shared_folder_ids.append(folder_share.folder_id)
    
    # Combine: owner OR user shares OR role shares OR documents in shared folders
    access_conditions = [owner_condition]
    
    if user_shared_doc_ids_query is not None:
        access_conditions.append(Document.id.in_(user_shared_doc_ids_query))
    
    if role_shared_doc_ids:
        access_conditions.append(Document.id.in_(role_shared_doc_ids))
    
    # Add documents in folders shared with user
    folder_access_conditions = []
    if user_shared_folder_ids_query is not None:
        folder_access_conditions.append(Document.folder_id.in_(user_shared_folder_ids_query))
    
    if role_shared_folder_ids:
        folder_access_conditions.append(Document.folder_id.in_(role_shared_folder_ids))
    
    if folder_access_conditions:
        folder_access_condition = or_(*folder_access_conditions) if len(folder_access_conditions) > 1 else folder_access_conditions[0]
        access_conditions.append(folder_access_condition)
    
    access_condition = or_(*access_conditions) if len(access_conditions) > 1 else access_conditions[0]
    
    return base_query.where(
        and_(
            *conditions,
            access_condition
        )
    )


async def filter_accessible_documents(
    session: AsyncSession,
    user: User,
    documents: List[Document],
    required_permission: str = "view"  # view, search, chat
) -> List[Document]:
    """
    Filter a list of documents to only include those the user has access to.
    
    This is useful when you already have a list of documents (e.g., from vector search)
    and need to filter them based on permissions.
    
    Args:
        session: Database session
        user: User object
        documents: List of Document objects to filter
        required_permission: Required permission level (view/search/chat)
    
    Returns:
        List of Document objects the user has access to
    """
    accessible_docs = []
    
    for doc in documents:
        has_access, _, _ = await check_document_access(
            session, user, doc, required_permission
        )
        if has_access:
            accessible_docs.append(doc)
    
    return accessible_docs


async def get_user_role_names(session: AsyncSession, user: User) -> List[str]:
    """
    Get all role names for a user (from both roles relationship and legacy role field).
    
    Args:
        session: Database session
        user: User object
    
    Returns:
        List of role names
    """
    role_names = []
    
    # Always query roles from database to avoid lazy loading issues in async context
    # Use the user_roles association table to get roles
    from sqlalchemy import select as sql_select
    from ..models.roles import user_role
    
    roles_result = await session.execute(
        sql_select(Role)
        .join(user_role, Role.id == user_role.c.role_id)
        .where(user_role.c.user_id == user.id)
    )
    user_roles = roles_result.scalars().all()
    role_names.extend([role.name for role in user_roles])
    
    # Add legacy role field
    if user.role and user.role not in role_names:
        role_names.append(user.role)
    
    return role_names


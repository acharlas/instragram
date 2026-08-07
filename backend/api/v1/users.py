"""User profile endpoints."""

from __future__ import annotations

import asyncio
import logging
from typing import Annotated, Any, Literal, NoReturn, cast
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile, status
from pydantic import BaseModel, ConfigDict, EmailStr
from sqlalchemy import and_, case, delete, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import ColumnElement

from api.deps import _require_user_id, get_current_user, get_db
from core import settings
from db.query_helpers import _desc, _eq, _ilike, _is_not_null
from db.errors import is_unique_violation
from models import Follow, FollowRequest, Post, User, UserBlock
from .pagination import MAX_PAGE_SIZE, set_next_offset_header
from .post_views import collect_like_meta
from services.account_privacy import (
    can_view_account_content,
    is_follow_request_pending,
    is_following,
)
from services.auth import DEFAULT_AVATAR_OBJECT_KEY
from services.account_blocks import (
    BlockState,
    apply_user_block,
    build_not_blocked_either_direction_filter,
    get_block_state,
    remove_user_block,
)
from services import (
    UploadTooLargeError,
    delete_object,
    ensure_bucket,
    get_minio_client,
    process_image_bytes,
    read_upload_file,
    upload_image_bytes,
)
from services.post_policy import build_author_view_filter

router = APIRouter(tags=["users"])
MAX_PROFILE_NAME_LENGTH = 80
MAX_PROFILE_BIO_LENGTH = 120
logger = logging.getLogger(__name__)


async def _find_user_by_username(
    session: AsyncSession,
    username: str,
) -> User | None:
    result = await session.execute(select(User).where(_eq(User.username, username)))
    return result.scalar_one_or_none()


def _raise_user_not_found() -> NoReturn:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User not found",
    )


async def _resolve_target_user_context(
    session: AsyncSession,
    *,
    current_user: User,
    username: str,
) -> tuple[User, str, str, BlockState]:
    target_user = await _find_user_by_username(session, username)
    if target_user is None:
        _raise_user_not_found()

    viewer_id = _require_user_id(
        current_user,
        detail="User record missing identifier",
    )
    target_user_id = _require_user_id(
        target_user,
        detail="User record missing identifier",
    )
    if viewer_id == target_user_id:
        return target_user, viewer_id, target_user_id, BlockState(
            is_blocked=False,
            is_blocked_by=False,
        )

    block_state = await get_block_state(
        session,
        viewer_id=viewer_id,
        target_id=target_user_id,
    )
    return target_user, viewer_id, target_user_id, block_state


async def _can_view_target_content(
    session: AsyncSession,
    *,
    viewer: User,
    target: User,
) -> bool:
    viewer_id = _require_user_id(
        viewer,
        detail="User record missing identifier",
    )
    return await can_view_account_content(
        session,
        viewer_id=viewer_id,
        account=target,
    )


class UserProfilePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    name: str | None = None
    bio: str | None = None
    avatar_key: str | None = None
    is_private: bool = False


class UserProfilePrivate(UserProfilePublic):
    email: EmailStr


class UserPostSummary(BaseModel):
    id: int
    image_key: str
    caption: str | None = None
    like_count: int = 0
    viewer_has_liked: bool = False


class FollowStatusResponse(BaseModel):
    is_following: bool
    is_requested: bool = False
    is_private: bool = False
    is_blocked: bool = False
    is_blocked_by: bool = False


class FollowMutationResponse(BaseModel):
    detail: str
    state: Literal["none", "following", "requested"]


class BlockMutationResponse(BaseModel):
    detail: str
    blocked: bool


@router.get("/users/search", response_model=list[UserProfilePublic])
async def search_users(
    q: str = Query(..., min_length=1, max_length=30),
    limit: int = Query(default=10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[UserProfilePublic]:
    """Return users whose username or display name starts with the prefix."""
    term = q.strip()
    if not term:
        return []

    username_column = cast(Any, User.username)
    name_column = cast(Any, User.name)

    username_match = _ilike(username_column, f"{term}%")
    name_match = and_(_is_not_null(name_column), _ilike(name_column, f"{term}%"))

    stmt = (
        select(User)
        .where(or_(username_match, name_match))
        .order_by(
            case(
                (username_match, 0),
                (name_match, 1),
                else_=2,
            ),
            User.username,
        )
        .limit(limit)
    )

    if current_user.id is not None:
        viewer_id = current_user.id
        stmt = stmt.where(
            ~_eq(User.id, viewer_id),
            build_not_blocked_either_direction_filter(
                viewer_id=viewer_id,
                candidate_user_id_column=cast(ColumnElement[str], User.id),
            ),
        )

    result = await session.execute(stmt)
    users = result.scalars().all()
    return [UserProfilePublic.model_validate(user) for user in users]


@router.get("/users/{username}", response_model=UserProfilePublic)
async def get_user_profile(
    username: str,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserProfilePublic:
    """Fetch a user's public profile."""
    user, _viewer_id, _target_user_id, block_state = await _resolve_target_user_context(
        session,
        current_user=current_user,
        username=username,
    )
    if block_state.is_blocked_by:
        _raise_user_not_found()
    return UserProfilePublic.model_validate(user)


@router.get("/me", response_model=UserProfilePrivate)
async def get_me(current_user: User = Depends(get_current_user)) -> UserProfilePrivate:
    """Return the authenticated user's full profile."""
    return UserProfilePrivate.model_validate(current_user)


@router.get("/me/blocked-users", response_model=list[UserProfilePublic])
async def list_blocked_users(
    response: Response,
    limit: Annotated[int | None, Query(ge=1, le=MAX_PAGE_SIZE)] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[UserProfilePublic]:
    current_user_id = _require_user_id(
        current_user,
        detail="User record missing identifier",
    )

    blocked_query = (
        select(User)
        .join(UserBlock, _eq(UserBlock.blocked_id, User.id))
        .where(_eq(UserBlock.blocker_id, current_user_id))
        .order_by(User.username, User.id)
    )
    if offset > 0:
        blocked_query = blocked_query.offset(offset)
    if limit is not None:
        blocked_query = blocked_query.limit(limit + 1)

    blocked_result = await session.execute(blocked_query)
    blocked_users = blocked_result.scalars().all()
    if limit is not None:
        has_more = len(blocked_users) > limit
        if has_more:
            blocked_users = blocked_users[:limit]
        set_next_offset_header(response, offset=offset, limit=limit, has_more=has_more)

    return [UserProfilePublic.model_validate(user) for user in blocked_users]


@router.patch("/me", response_model=UserProfilePrivate)
async def update_me(
    name: str | None = Form(default=None),
    bio: str | None = Form(default=None),
    avatar: UploadFile | None = File(default=None),
    is_private: Annotated[bool | None, Form()] = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> UserProfilePrivate:
    """Update the authenticated user's profile."""
    updated = False
    uploaded_avatar_key: str | None = None
    previous_avatar_key = current_user.avatar_key
    previous_is_private = current_user.is_private

    if name is not None:
        normalized_name = name.strip()
        if len(normalized_name) > MAX_PROFILE_NAME_LENGTH:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Name must be at most {MAX_PROFILE_NAME_LENGTH} characters",
            )
        current_user.name = normalized_name or None
        updated = True
    if bio is not None:
        normalized_bio = bio.strip()
        if len(normalized_bio) > MAX_PROFILE_BIO_LENGTH:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Bio must be at most {MAX_PROFILE_BIO_LENGTH} characters",
            )
        current_user.bio = normalized_bio or None
        updated = True

    if is_private is not None:
        current_user.is_private = is_private
        updated = True

    if avatar is not None:
        try:
            data = await read_upload_file(avatar, settings.upload_max_bytes)
            processed_bytes, processed_content_type = await asyncio.to_thread(
                process_image_bytes,
                data,
            )
        except UploadTooLargeError as exc:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=str(exc),
            ) from exc
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc

        object_key = f"avatars/{uuid4().hex}.jpg"
        _client = get_minio_client()
        ensure_bucket(_client)
        await asyncio.to_thread(upload_image_bytes, _client, object_key, processed_bytes, processed_content_type)

        current_user.avatar_key = object_key
        uploaded_avatar_key = object_key
        updated = True

    if updated:
        if previous_is_private and not current_user.is_private:
            current_user_id = _require_user_id(
                current_user,
                detail="User record missing identifier",
            )
            await session.execute(
                delete(FollowRequest).where(
                    _eq(FollowRequest.target_id, current_user_id),
                )
            )
        session.add(current_user)
        try:
            await session.commit()
        except Exception as exc:
            await session.rollback()
            if uploaded_avatar_key is not None:
                try:
                    await asyncio.to_thread(delete_object, uploaded_avatar_key)
                except Exception as cleanup_error:
                    logger.warning(
                        "Failed to cleanup uploaded avatar after profile update commit failure",
                        extra={"avatar_key": uploaded_avatar_key},
                        exc_info=cleanup_error,
                    )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update profile",
            ) from exc
        await session.refresh(current_user)
        if (
            uploaded_avatar_key is not None
            and previous_avatar_key is not None
            and previous_avatar_key != uploaded_avatar_key
            and previous_avatar_key != DEFAULT_AVATAR_OBJECT_KEY
            and not previous_avatar_key.startswith("avatars/default/")
        ):
            try:
                await asyncio.to_thread(delete_object, previous_avatar_key)
            except Exception as cleanup_error:
                logger.warning(
                    "Failed to cleanup replaced avatar object after profile update",
                    extra={"avatar_key": previous_avatar_key},
                    exc_info=cleanup_error,
                )

    return UserProfilePrivate.model_validate(current_user)


@router.get("/users/{username}/posts", response_model=list[UserPostSummary])
async def list_user_posts(
    username: str,
    response: Response,
    limit: Annotated[int | None, Query(ge=1, le=MAX_PAGE_SIZE)] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[UserPostSummary]:
    """Return posts authored by the specified user when visible to the viewer."""
    author = await _find_user_by_username(session, username)
    if author is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    viewer_id = _require_user_id(
        current_user,
        detail="User record missing identifier",
    )
    author_id = _require_user_id(
        author,
        detail="Target user record missing identifier",
    )

    can_view = await _can_view_target_content(
        session,
        viewer=current_user,
        target=author,
    )
    if not can_view:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    post_created_at = cast(Any, Post.created_at)
    post_id_column = cast(Any, Post.id)
    posts_query = (
        select(Post)
        .where(_eq(Post.author_id, author_id))
        .order_by(
            _desc(post_created_at),
            _desc(post_id_column),
        )
    )
    if offset > 0:
        posts_query = posts_query.offset(offset)
    if limit is not None:
        posts_query = posts_query.limit(limit + 1)

    posts_result = await session.execute(posts_query)
    posts = posts_result.scalars().all()
    if limit is not None:
        has_more = len(posts) > limit
        if has_more:
            posts = posts[:limit]
        set_next_offset_header(response, offset=offset, limit=limit, has_more=has_more)

    post_ids = [post.id for post in posts if post.id is not None]
    like_counts, liked_set = await collect_like_meta(session, post_ids, viewer_id)

    summaries: list[UserPostSummary] = []
    for post in posts:
        if post.id is None:
            continue
        summaries.append(
            UserPostSummary(
                id=post.id,
                image_key=post.image_key,
                caption=post.caption,
                like_count=like_counts.get(post.id, 0),
                viewer_has_liked=post.id in liked_set,
            )
        )
    return summaries


@router.post(
    "/users/{username}/block",
    response_model=BlockMutationResponse,
    status_code=status.HTTP_200_OK,
)
async def block_user(
    username: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> BlockMutationResponse:
    if username == current_user.username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot block yourself",
        )

    _target_user, blocker_id, blocked_id, block_state = await _resolve_target_user_context(
        session,
        current_user=current_user,
        username=username,
    )
    if block_state.is_blocked_by and not block_state.is_blocked:
        _raise_user_not_found()

    created = await apply_user_block(
        session,
        blocker_id=blocker_id,
        blocked_id=blocked_id,
    )
    return BlockMutationResponse(
        detail="User blocked" if created else "Already blocked",
        blocked=True,
    )


@router.delete(
    "/users/{username}/block",
    response_model=BlockMutationResponse,
    status_code=status.HTTP_200_OK,
)
async def unblock_user(
    username: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> BlockMutationResponse:
    if username == current_user.username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot unblock yourself",
        )

    _target_user, blocker_id, blocked_id, block_state = await _resolve_target_user_context(
        session,
        current_user=current_user,
        username=username,
    )
    if block_state.is_blocked_by and not block_state.is_blocked:
        _raise_user_not_found()

    removed = await remove_user_block(
        session,
        blocker_id=blocker_id,
        blocked_id=blocked_id,
    )
    return BlockMutationResponse(
        detail="User unblocked" if removed else "User was not blocked",
        blocked=False,
    )


@router.post(
    "/users/{username}/follow",
    response_model=FollowMutationResponse,
    status_code=status.HTTP_200_OK,
)
async def follow_user(
    username: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> FollowMutationResponse:
    if username == current_user.username:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot follow yourself")

    followee, follower_id, followee_id, block_state = await _resolve_target_user_context(
        session,
        current_user=current_user,
        username=username,
    )
    if block_state.is_blocked_by:
        _raise_user_not_found()
    if block_state.is_blocked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot follow this user",
        )

    if await is_following(
        session,
        follower_id=follower_id,
        followee_id=followee_id,
    ):
        return FollowMutationResponse(detail="Already following", state="following")

    has_pending_request = await is_follow_request_pending(
        session,
        requester_id=follower_id,
        target_id=followee_id,
    )

    if followee.is_private:
        if has_pending_request:
            return FollowMutationResponse(detail="Follow request pending", state="requested")

        session.add(FollowRequest(requester_id=follower_id, target_id=followee_id))
        try:
            await session.commit()
        except IntegrityError as exc:
            await session.rollback()
            if is_unique_violation(exc):
                return FollowMutationResponse(detail="Follow request pending", state="requested")
            raise
        return FollowMutationResponse(detail="Follow request sent", state="requested")

    if has_pending_request:
        await session.execute(
            delete(FollowRequest).where(
                _eq(FollowRequest.requester_id, follower_id),
                _eq(FollowRequest.target_id, followee_id),
            )
        )

    session.add(Follow(follower_id=follower_id, followee_id=followee_id))
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        if is_unique_violation(exc):
            return FollowMutationResponse(detail="Already following", state="following")
        raise
    return FollowMutationResponse(detail="Followed", state="following")


@router.delete(
    "/users/{username}/follow",
    response_model=FollowMutationResponse,
    status_code=status.HTTP_200_OK,
)
async def unfollow_user(
    username: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> FollowMutationResponse:
    _followee, follower_id, followee_id, block_state = await _resolve_target_user_context(
        session,
        current_user=current_user,
        username=username,
    )
    if block_state.is_blocked_by:
        _raise_user_not_found()
    if block_state.is_blocked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify follow relationship for this user",
        )

    follow_deleted = await is_following(
        session,
        follower_id=follower_id,
        followee_id=followee_id,
    )
    request_deleted = await is_follow_request_pending(
        session,
        requester_id=follower_id,
        target_id=followee_id,
    )

    await session.execute(
        delete(Follow).where(
            _eq(Follow.follower_id, follower_id),
            _eq(Follow.followee_id, followee_id),
        )
    )
    await session.execute(
        delete(FollowRequest).where(
            _eq(FollowRequest.requester_id, follower_id),
            _eq(FollowRequest.target_id, followee_id),
        )
    )
    await session.commit()
    if follow_deleted:
        return FollowMutationResponse(detail="Unfollowed", state="none")
    if request_deleted:
        return FollowMutationResponse(detail="Follow request cancelled", state="none")
    return FollowMutationResponse(detail="Not following", state="none")


@router.get("/users/{username}/follow-status", response_model=FollowStatusResponse)
async def get_follow_status(
    username: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> FollowStatusResponse:
    target_user, viewer_id, target_id, block_state = await _resolve_target_user_context(
        session,
        current_user=current_user,
        username=username,
    )

    following_status = False
    is_requested = False
    is_blocked = block_state.is_blocked
    is_blocked_by = block_state.is_blocked_by
    if viewer_id != target_id:
        if is_blocked_by:
            _raise_user_not_found()
        if is_blocked:
            return FollowStatusResponse(
                is_following=False,
                is_requested=False,
                is_private=target_user.is_private,
                is_blocked=True,
                is_blocked_by=False,
            )

        following_status = await is_following(
            session,
            follower_id=viewer_id,
            followee_id=target_id,
        )
        if target_user.is_private and not following_status:
            is_requested = await is_follow_request_pending(
                session,
                requester_id=viewer_id,
                target_id=target_id,
            )

    return FollowStatusResponse(
        is_following=following_status,
        is_requested=is_requested,
        is_private=target_user.is_private,
        is_blocked=is_blocked,
        is_blocked_by=is_blocked_by,
    )


@router.get("/users/{username}/followers", response_model=list[UserProfilePublic])
async def list_followers(
    username: str,
    response: Response,
    limit: Annotated[int | None, Query(ge=1, le=MAX_PAGE_SIZE)] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[UserProfilePublic]:
    target_user = await _find_user_by_username(session, username)
    if target_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    current_user_id = _require_user_id(
        current_user,
        detail="User record missing identifier",
    )
    target_user_id = _require_user_id(
        target_user,
        detail="User record missing identifier",
    )
    can_view = await _can_view_target_content(
        session,
        viewer=current_user,
        target=target_user,
    )
    if not can_view:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    followers_query = (
        select(User)
        .join(Follow, _eq(Follow.follower_id, User.id))
        .where(
            _eq(Follow.followee_id, target_user_id),
            build_author_view_filter(
                viewer_id=current_user_id,
                post_author_column=cast(ColumnElement[str], User.id),
                author_is_private_column=cast(ColumnElement[bool], User.is_private),
            ),
        )
        .order_by(User.username, User.id)
    )
    if offset > 0:
        followers_query = followers_query.offset(offset)
    if limit is not None:
        followers_query = followers_query.limit(limit + 1)

    followers_result = await session.execute(followers_query)
    followers = followers_result.scalars().all()
    if limit is not None:
        has_more = len(followers) > limit
        if has_more:
            followers = followers[:limit]
        set_next_offset_header(response, offset=offset, limit=limit, has_more=has_more)

    return [UserProfilePublic.model_validate(user) for user in followers]


@router.get("/users/{username}/following", response_model=list[UserProfilePublic])
async def list_following(
    username: str,
    response: Response,
    limit: Annotated[int | None, Query(ge=1, le=MAX_PAGE_SIZE)] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[UserProfilePublic]:
    target_user = await _find_user_by_username(session, username)
    if target_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    current_user_id = _require_user_id(
        current_user,
        detail="User record missing identifier",
    )
    target_user_id = _require_user_id(
        target_user,
        detail="User record missing identifier",
    )
    can_view = await _can_view_target_content(
        session,
        viewer=current_user,
        target=target_user,
    )
    if not can_view:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    following_query = (
        select(User)
        .join(Follow, _eq(Follow.followee_id, User.id))
        .where(
            _eq(Follow.follower_id, target_user_id),
            build_author_view_filter(
                viewer_id=current_user_id,
                post_author_column=cast(ColumnElement[str], User.id),
                author_is_private_column=cast(ColumnElement[bool], User.is_private),
            ),
        )
        .order_by(User.username, User.id)
    )
    if offset > 0:
        following_query = following_query.offset(offset)
    if limit is not None:
        following_query = following_query.limit(limit + 1)

    following_result = await session.execute(following_query)
    following = following_result.scalars().all()
    if limit is not None:
        has_more = len(following) > limit
        if has_more:
            following = following[:limit]
        set_next_offset_header(response, offset=offset, limit=limit, has_more=has_more)

    return [UserProfilePublic.model_validate(user) for user in following]


@router.get("/users/{username}/follow-requests", response_model=list[UserProfilePublic])
async def list_follow_requests(
    username: str,
    response: Response,
    limit: Annotated[int | None, Query(ge=1, le=MAX_PAGE_SIZE)] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[UserProfilePublic]:
    target_user = await _find_user_by_username(session, username)
    if target_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    current_user_id = _require_user_id(
        current_user,
        detail="User record missing identifier",
    )
    target_user_id = _require_user_id(
        target_user,
        detail="User record missing identifier",
    )
    if current_user_id != target_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    requests_query = (
        select(User)
        .join(FollowRequest, _eq(FollowRequest.requester_id, User.id))
        .where(
            _eq(FollowRequest.target_id, target_user_id),
            build_not_blocked_either_direction_filter(
                viewer_id=current_user_id,
                candidate_user_id_column=cast(ColumnElement[str], User.id),
            ),
        )
        .order_by(User.username, User.id)
    )
    if offset > 0:
        requests_query = requests_query.offset(offset)
    if limit is not None:
        requests_query = requests_query.limit(limit + 1)

    requests_result = await session.execute(requests_query)
    requests = requests_result.scalars().all()
    if limit is not None:
        has_more = len(requests) > limit
        if has_more:
            requests = requests[:limit]
        set_next_offset_header(response, offset=offset, limit=limit, has_more=has_more)

    return [UserProfilePublic.model_validate(user) for user in requests]


@router.post(
    "/users/{username}/follow-requests/{requester_username}/approve",
    status_code=status.HTTP_200_OK,
)
async def approve_follow_request(
    username: str,
    requester_username: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    target_user = await _find_user_by_username(session, username)
    requester = await _find_user_by_username(session, requester_username)
    if target_user is None or requester is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    current_user_id = _require_user_id(
        current_user,
        detail="User record missing identifier",
    )
    target_user_id = _require_user_id(
        target_user,
        detail="User record missing identifier",
    )
    requester_id = _require_user_id(
        requester,
        detail="User record missing identifier",
    )
    if current_user_id != target_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    if requester_id == target_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot approve your own follow request",
        )
    block_state = await get_block_state(
        session,
        viewer_id=target_user_id,
        target_id=requester_id,
    )
    if block_state.is_blocked or block_state.is_blocked_by:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot process follow request for blocked user",
        )

    has_request = await is_follow_request_pending(
        session,
        requester_id=requester_id,
        target_id=target_user_id,
    )
    if not has_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Follow request not found",
        )

    await session.execute(
        delete(FollowRequest).where(
            _eq(FollowRequest.requester_id, requester_id),
            _eq(FollowRequest.target_id, target_user_id),
        )
    )
    session.add(Follow(follower_id=requester_id, followee_id=target_user_id))
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        if not is_unique_violation(exc):
            raise
        await session.execute(
            delete(FollowRequest).where(
                _eq(FollowRequest.requester_id, requester_id),
                _eq(FollowRequest.target_id, target_user_id),
            )
        )
        await session.commit()
        return {"detail": "Already following"}

    return {"detail": "Follow request approved"}


@router.delete(
    "/users/{username}/follow-requests/{requester_username}",
    status_code=status.HTTP_200_OK,
)
async def decline_follow_request(
    username: str,
    requester_username: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    target_user = await _find_user_by_username(session, username)
    requester = await _find_user_by_username(session, requester_username)
    if target_user is None or requester is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    current_user_id = _require_user_id(
        current_user,
        detail="User record missing identifier",
    )
    target_user_id = _require_user_id(
        target_user,
        detail="User record missing identifier",
    )
    requester_id = _require_user_id(
        requester,
        detail="User record missing identifier",
    )
    if current_user_id != target_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    block_state = await get_block_state(
        session,
        viewer_id=target_user_id,
        target_id=requester_id,
    )
    if block_state.is_blocked or block_state.is_blocked_by:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot process follow request for blocked user",
        )

    has_request = await is_follow_request_pending(
        session,
        requester_id=requester_id,
        target_id=target_user_id,
    )
    if not has_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Follow request not found",
        )

    await session.execute(
        delete(FollowRequest).where(
            _eq(FollowRequest.requester_id, requester_id),
            _eq(FollowRequest.target_id, target_user_id),
        )
    )
    await session.commit()
    return {"detail": "Follow request declined"}

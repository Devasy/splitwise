"""Synchronous wrapper for AsyncSplitwise client.

Provides backward-compatible synchronous API using asyncio.run().
Use AsyncSplitwise directly for better performance in async applications.

Typical usage:
    >>> from splitwise.sync_wrapper import SyncSplitwise
    >>> sw = SyncSplitwise("key", "secret", api_key="...")
    >>> user = sw.getCurrentUser()
    >>> groups = sw.getGroups()
"""

import asyncio
from typing import Optional, Dict, List, Tuple
from functools import wraps

from splitwise.async_client import AsyncSplitwise
from splitwise.user import User, Friend, CurrentUser
from splitwise.currency import Currency
from splitwise.group import Group
from splitwise.category import Category
from splitwise.expense import Expense
from splitwise.comment import Comment
from splitwise.notification import Notification
from splitwise.error import SplitwiseError


def _run_sync(coro):
    """Run a coroutine synchronously."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    
    if loop and loop.is_running():
        # If we're already in an async context, create a new thread
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, coro)
            return future.result()
    else:
        return asyncio.run(coro)


class SyncSplitwise:
    """Synchronous wrapper for AsyncSplitwise.
    
    Provides the same API as AsyncSplitwise but with synchronous methods.
    Useful for backward compatibility or when async is not required.
    
    For better performance, use AsyncSplitwise directly in async applications.
    """
    
    def __init__(
        self,
        consumer_key: str,
        consumer_secret: str,
        access_token: Optional[Dict[str, str]] = None,
        oauth2_access_token: Optional[Dict[str, str]] = None,
        api_key: Optional[str] = None,
        pool_size: int = 10,
        timeout: float = 30,
        retry_attempts: int = 3
    ):
        """Initialize the sync Splitwise client.
        
        Args:
            consumer_key: OAuth consumer key from Splitwise
            consumer_secret: OAuth consumer secret from Splitwise
            access_token: Optional OAuth 1.0 access token dict
            oauth2_access_token: Optional OAuth 2.0 access token dict
            api_key: Optional API key for simple authentication
            pool_size: Max concurrent connections
            timeout: Request timeout in seconds
            retry_attempts: Number of retries for failed requests
        """
        self._async_client = AsyncSplitwise(
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
            access_token=access_token,
            oauth2_access_token=oauth2_access_token,
            api_key=api_key,
            pool_size=pool_size,
            timeout=timeout,
            retry_attempts=retry_attempts
        )
    
    def __enter__(self) -> 'SyncSplitwise':
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()
    
    def close(self) -> None:
        """Close the client and release resources."""
        _run_sync(self._async_client.close())
    
    def setAccessToken(self, access_token: Dict[str, str]) -> None:
        """Set OAuth 1.0 access token."""
        self._async_client.setAccessToken(access_token)
    
    def setOAuth2AccessToken(self, access_token: Dict[str, str]) -> None:
        """Set OAuth 2.0 access token."""
        self._async_client.setOAuth2AccessToken(access_token)
    
    # ========== User Methods ==========
    
    def getCurrentUser(self) -> CurrentUser:
        """Get the current authorized user's data."""
        return _run_sync(self._async_client.getCurrentUser())
    
    def getUser(self, id: int) -> User:
        """Get a user's data by ID."""
        return _run_sync(self._async_client.getUser(id))
    
    def updateUser(self, user: CurrentUser) -> Tuple[Optional[CurrentUser], Optional[SplitwiseError]]:
        """Update user information."""
        return _run_sync(self._async_client.updateUser(user))
    
    def getFriends(self) -> List[Friend]:
        """Get list of user's friends."""
        return _run_sync(self._async_client.getFriends())
    
    # ========== Group Methods ==========
    
    def getGroups(self) -> List[Group]:
        """Get list of groups the user is part of."""
        return _run_sync(self._async_client.getGroups())
    
    def getGroup(self, id: int = 0) -> Optional[Group]:
        """Get details of a specific group."""
        return _run_sync(self._async_client.getGroup(id))
    
    def createGroup(self, group: Group) -> Tuple[Optional[Group], Optional[SplitwiseError]]:
        """Create a new group."""
        return _run_sync(self._async_client.createGroup(group))
    
    def addUserToGroup(self, user: User, group_id: int) -> Tuple[bool, Optional[Friend], Optional[SplitwiseError]]:
        """Add a user to a group."""
        return _run_sync(self._async_client.addUserToGroup(user, group_id))
    
    def deleteGroup(self, id: int) -> Tuple[bool, Optional[SplitwiseError]]:
        """Delete a group."""
        return _run_sync(self._async_client.deleteGroup(id))
    
    # ========== Expense Methods ==========
    
    def getExpenses(
        self,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
        group_id: Optional[int] = None,
        friend_id: Optional[int] = None,
        dated_after: Optional[str] = None,
        dated_before: Optional[str] = None,
        updated_after: Optional[str] = None,
        updated_before: Optional[str] = None,
        visible: Optional[bool] = None
    ) -> List[Expense]:
        """Get list of expenses with optional filters."""
        return _run_sync(self._async_client.getExpenses(
            offset=offset, limit=limit, group_id=group_id,
            friend_id=friend_id, dated_after=dated_after,
            dated_before=dated_before, updated_after=updated_after,
            updated_before=updated_before, visible=visible
        ))
    
    def getExpense(self, id: int) -> Optional[Expense]:
        """Get details of a specific expense."""
        return _run_sync(self._async_client.getExpense(id))
    
    def createExpense(self, expense: Expense) -> Tuple[Optional[Expense], Optional[SplitwiseError]]:
        """Create a new expense."""
        return _run_sync(self._async_client.createExpense(expense))
    
    def updateExpense(self, expense: Expense) -> Tuple[Optional[Expense], Optional[SplitwiseError]]:
        """Update an existing expense."""
        return _run_sync(self._async_client.updateExpense(expense))
    
    def deleteExpense(self, id: int) -> Tuple[bool, Optional[SplitwiseError]]:
        """Delete an expense."""
        return _run_sync(self._async_client.deleteExpense(id))
    
    # ========== Other Methods ==========
    
    def getCurrencies(self) -> List[Currency]:
        """Get list of supported currencies."""
        return _run_sync(self._async_client.getCurrencies())
    
    def getCategories(self) -> List[Category]:
        """Get list of expense categories."""
        return _run_sync(self._async_client.getCategories())
    
    def getComments(self, expense_id: int) -> List[Comment]:
        """Get comments for an expense."""
        return _run_sync(self._async_client.getComments(expense_id))
    
    def createComment(self, expense_id: int, content: str) -> Tuple[Optional[Comment], Optional[SplitwiseError]]:
        """Create a comment on an expense."""
        return _run_sync(self._async_client.createComment(expense_id, content))
    
    def getNotifications(self, updated_since: Optional[str] = None, limit: Optional[int] = None) -> List[Notification]:
        """Get user notifications."""
        return _run_sync(self._async_client.getNotifications(updated_since, limit))
    
    # ========== Batch Operations ==========
    
    def getAllGroupsWithExpenses(self, limit_per_group: int = 50) -> Dict[int, List[Expense]]:
        """Fetch all groups and their expenses."""
        return _run_sync(self._async_client.getAllGroupsWithExpenses(limit_per_group))
    
    def getAllExpensesPaginated(
        self,
        group_id: Optional[int] = None,
        page_size: int = 100,
        max_pages: int = 10
    ) -> List[Expense]:
        """Fetch all expenses with automatic pagination."""
        return _run_sync(self._async_client.getAllExpensesPaginated(group_id, page_size, max_pages))

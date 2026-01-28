"""Async Splitwise Client.

An asynchronous implementation of the Splitwise API client using aiohttp.
Optimized for edge/low-compute devices with:
- Non-blocking I/O
- Connection pooling
- Concurrent request support
- Memory-efficient operations

Typical usage:
    >>> async with AsyncSplitwise("key", "secret", api_key="...") as sw:
    ...     user = await sw.getCurrentUser()
    ...     groups = await sw.getGroups()
    ...     # Concurrent fetching
    ...     expenses, friends = await asyncio.gather(
    ...         sw.getExpenses(limit=100),
    ...         sw.getFriends()
    ...     )
"""

import json
import asyncio
from typing import Optional, Dict, Any, List, Tuple
from urllib.parse import urlencode

from splitwise.user import User, Friend, CurrentUser
from splitwise.currency import Currency
from splitwise.group import Group
from splitwise.category import Category
from splitwise.expense import Expense
from splitwise.comment import Comment
from splitwise.notification import Notification
from splitwise.error import SplitwiseError
from splitwise.exception import (
    SplitwiseException,
    SplitwiseUnauthorizedException,
    SplitwiseBadRequestException,
    SplitwiseNotAllowedException,
    SplitwiseNotFoundException
)
from splitwise.session import AsyncSessionManager
from splitwise.oauth import AsyncOAuth1, AsyncOAuth2, AsyncOAuthClient
from splitwise import base


class AsyncSplitwise:
    """Async Splitwise API client.
    
    An asynchronous implementation using aiohttp for non-blocking I/O.
    Designed for high-throughput and edge/low-compute environments.
    
    Attributes:
        consumer_key: Splitwise OAuth consumer key
        consumer_secret: Splitwise OAuth consumer secret
        api_key: Optional API key for authentication
    """
    
    def __init__(
        self,
        consumer_key: str,
        consumer_secret: str,
        access_token: Optional[Dict[str, str]] = None,
        oauth2_access_token: Optional[Dict[str, str]] = None,
        api_key: Optional[str] = None,
        pool_size: int = base.DEFAULT_POOL_SIZE,
        timeout: float = base.DEFAULT_TIMEOUT,
        retry_attempts: int = 3
    ):
        """Initialize the async Splitwise client.
        
        Args:
            consumer_key: OAuth consumer key from Splitwise
            consumer_secret: OAuth consumer secret from Splitwise
            access_token: Optional OAuth 1.0 access token dict
            oauth2_access_token: Optional OAuth 2.0 access token dict
            api_key: Optional API key for simple authentication
            pool_size: Max concurrent connections (default: 10)
            timeout: Request timeout in seconds (default: 30)
            retry_attempts: Number of retries for failed requests
        """
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.api_key = api_key
        self._access_token = access_token
        self._oauth2_access_token = oauth2_access_token
        
        # Session manager for connection pooling
        self._session_manager = AsyncSessionManager(
            pool_size=pool_size,
            timeout=timeout,
            retry_attempts=retry_attempts
        )
    
    async def __aenter__(self) -> 'AsyncSplitwise':
        """Async context manager entry."""
        await self._session_manager.get_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()
    
    async def close(self) -> None:
        """Close the client and release resources."""
        await self._session_manager.close()
    
    def setAccessToken(self, access_token: Dict[str, str]) -> None:
        """Set OAuth 1.0 access token.
        
        Args:
            access_token: Dict with oauth_token and oauth_token_secret
        """
        self._access_token = access_token
    
    def setOAuth2AccessToken(self, access_token: Dict[str, str]) -> None:
        """Set OAuth 2.0 access token.
        
        Args:
            access_token: Dict with access_token and token_type
        """
        self._oauth2_access_token = access_token
    
    def _get_auth_headers(
        self,
        method: str = "GET",
        url: str = "",
        data: Optional[Dict] = None
    ) -> Dict[str, str]:
        """Get authentication headers.
        
        Args:
            method: HTTP method (needed for OAuth 1.0 signature)
            url: Request URL (needed for OAuth 1.0 signature)
            data: Request data (needed for OAuth 1.0 signature)
        
        Returns:
            Headers dict with authorization
        """
        headers = {}
        
        if self._oauth2_access_token:
            token = self._oauth2_access_token.get('access_token', '')
            headers['Authorization'] = f'Bearer {token}'
        elif self._access_token:
            # OAuth 1.0 authentication
            oauth = AsyncOAuth1(
                self.consumer_key,
                self.consumer_secret,
                resource_owner_key=self._access_token.get('oauth_token'),
                resource_owner_secret=self._access_token.get('oauth_token_secret')
            )
            headers['Authorization'] = oauth.get_auth_header(method, url, data)
        elif self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'
        
        return headers
    
    @staticmethod
    def _handle_uppercase_boolean(data: Optional[Dict]) -> Optional[Dict]:
        """Convert Python booleans to lowercase strings.
        
        Args:
            data: Request data dict
            
        Returns:
            Modified data dict
        """
        if data is not None:
            for key, val in data.items():
                if isinstance(val, bool):
                    data[key] = str(val).lower()
        return data
    
    def _prepare_options_url(self, options: Dict) -> str:
        """Prepare URL query string.
        
        Args:
            options: Query parameters
            
        Returns:
            URL-encoded query string
        """
        return "?" + urlencode(options) if options else ""
    
    async def _make_request(
        self,
        url: str,
        method: str = "GET",
        data: Optional[Dict] = None,
        files: Optional[Dict] = None
    ) -> str:
        """Make an async HTTP request.
        
        Args:
            url: Request URL
            method: HTTP method
            data: Request data
            files: Files to upload
            
        Returns:
            Response content
        """
        processed_data = self._handle_uppercase_boolean(data.copy() if data else None)
        headers = self._get_auth_headers(method, url, processed_data)
        
        return await self._session_manager.request(
            method=method,
            url=url,
            headers=headers,
            data=processed_data,
            files=files
        )
    
    # ========== OAuth Methods ==========
    
    async def getRequestToken(self) -> Tuple[str, str]:
        """Get OAuth 1.0 request token.
        
        Returns:
            Tuple of (authorize_url, oauth_token_secret)
        """
        client = AsyncOAuthClient(self.consumer_key, self.consumer_secret)
        oauth_token, oauth_token_secret = await client.get_request_token()
        authorize_url = client.get_authorize_url(oauth_token)
        return authorize_url, oauth_token_secret
    
    async def getAccessToken(
        self,
        oauth_token: str,
        oauth_token_secret: str,
        oauth_verifier: str
    ) -> Dict[str, str]:
        """Exchange request token for access token.
        
        Args:
            oauth_token: OAuth token from redirect URL
            oauth_token_secret: Token secret from getRequestToken
            oauth_verifier: Verifier from redirect URL
            
        Returns:
            Dict with oauth_token and oauth_token_secret
        """
        client = AsyncOAuthClient(self.consumer_key, self.consumer_secret)
        return await client.get_access_token(
            oauth_token, oauth_token_secret, oauth_verifier
        )
    
    def getOAuth2AuthorizeURL(self, redirect_uri: str, state: Optional[str] = None) -> str:
        """Get OAuth 2.0 authorization URL.
        
        Args:
            redirect_uri: Redirect URI for callback
            state: Optional state for CSRF protection
            
        Returns:
            Authorization URL
        """
        client = AsyncOAuthClient(self.consumer_key, self.consumer_secret)
        return client.get_oauth2_authorize_url(redirect_uri, state)
    
    async def getOAuth2AccessToken(self, code: str, redirect_uri: str) -> Optional[Dict[str, Any]]:
        """Exchange OAuth 2.0 code for access token.
        
        Args:
            code: Authorization code from redirect
            redirect_uri: Redirect URI used for authorization
            
        Returns:
            Dict with access_token and token_type
        """
        client = AsyncOAuthClient(self.consumer_key, self.consumer_secret)
        return await client.get_oauth2_access_token(code, redirect_uri)
    
    # ========== User Methods ==========
    
    async def getCurrentUser(self) -> CurrentUser:
        """Get the current authorized user's data.
        
        Returns:
            CurrentUser object containing user data
        """
        content = await self._make_request(base.GET_CURRENT_USER_URL)
        data = json.loads(content)
        return CurrentUser(data["user"])
    
    async def getUser(self, id: int) -> User:
        """Get a user's data by ID.
        
        Args:
            id: User ID
            
        Returns:
            User object containing user data
        """
        try:
            content = await self._make_request(f"{base.GET_USER_URL}/{id}")
        except SplitwiseNotAllowedException as e:
            e.setMessage(f"You are not allowed to fetch user with id {id}")
            raise
        except SplitwiseNotFoundException as e:
            e.setMessage(f"User with id {id} does not exist")
            raise
        
        data = json.loads(content)
        return User(data["user"])
    
    async def updateUser(self, user: CurrentUser) -> Tuple[Optional[CurrentUser], Optional[SplitwiseError]]:
        """Update user information.
        
        Args:
            user: CurrentUser object with updated data
            
        Returns:
            Tuple of (updated user, errors)
        """
        if user.getId() is None:
            raise SplitwiseBadRequestException("User ID is required to update user")
        
        user_data = user.__dict__
        
        try:
            content = await self._make_request(base.UPDATE_USER_URL, "POST", user_data)
        except SplitwiseNotAllowedException as e:
            e.setMessage(f"You are not allowed to access user with id {user.getId()}")
            raise
        except SplitwiseNotFoundException as e:
            e.setMessage(f"User with id {user.getId()} does not exist")
            raise
        
        data = json.loads(content)
        updated_user = None
        errors = None
        
        if "user" in data and data["user"] is not None:
            updated_user = CurrentUser(data["user"])
        if "errors" in data and len(data["errors"]) != 0:
            errors = SplitwiseError(data["errors"])
        
        return updated_user, errors
    
    async def getFriends(self) -> List[Friend]:
        """Get list of user's friends.
        
        Returns:
            List of Friend objects
        """
        content = await self._make_request(base.GET_FRIENDS_URL)
        data = json.loads(content)
        
        friends = []
        if "friends" in data:
            for f in data["friends"]:
                friends.append(Friend(f))
        
        return friends
    
    # ========== Group Methods ==========
    
    async def getGroups(self) -> List[Group]:
        """Get list of groups the user is part of.
        
        Returns:
            List of Group objects
        """
        content = await self._make_request(base.GET_GROUPS_URL)
        data = json.loads(content)
        
        groups = []
        if "groups" in data:
            for g in data["groups"]:
                groups.append(Group(g))
        
        return groups
    
    async def getGroup(self, id: int = 0) -> Optional[Group]:
        """Get details of a specific group.
        
        Args:
            id: Group ID (0 for non-group expenses)
            
        Returns:
            Group object
        """
        try:
            content = await self._make_request(f"{base.GET_GROUP_URL}/{id}")
        except SplitwiseNotAllowedException as e:
            e.setMessage(f"You are not allowed to fetch group with id {id}")
            raise
        except SplitwiseNotFoundException as e:
            e.setMessage(f"Group with id {id} does not exist")
            raise
        
        data = json.loads(content)
        if "group" in data:
            return Group(data["group"])
        return None
    
    async def createGroup(self, group: Group) -> Tuple[Optional[Group], Optional[SplitwiseError]]:
        """Create a new group.
        
        Args:
            group: Group object with group details
            
        Returns:
            Tuple of (created group, errors)
        """
        group_info = group.__dict__
        
        if "members" in group_info:
            group_members = group.getMembers()
            del group_info["members"]
            self._set_user_array(group_members, group_info)
        
        content = await self._make_request(base.CREATE_GROUP_URL, "POST", group_info)
        data = json.loads(content)
        
        group_detail = None
        errors = None
        
        if "group" in data:
            group_detail = Group(data["group"])
            if "errors" in data["group"] and len(data["group"]["errors"]) != 0:
                errors = SplitwiseError(data["group"]["errors"])
        
        return group_detail, errors
    
    async def addUserToGroup(self, user: User, group_id: int) -> Tuple[bool, Optional[Friend], Optional[SplitwiseError]]:
        """Add a user to a group.
        
        Args:
            user: User to add
            group_id: Target group ID
            
        Returns:
            Tuple of (success, added user, errors)
        """
        request_data = user.__dict__
        request_data["group_id"] = group_id
        
        if "id" in request_data:
            request_data["user_id"] = request_data["id"]
            del request_data["id"]
        
        try:
            content = await self._make_request(base.ADD_USER_TO_GROUP_URL, "POST", request_data)
        except SplitwiseNotAllowedException as e:
            e.setMessage(f"You are not allowed to access group with id {group_id}")
            raise
        except SplitwiseNotFoundException as e:
            e.setMessage(f"Group with id {group_id} does not exist")
            raise
        
        data = json.loads(content)
        errors = None
        success = False
        added_user = None
        
        if "success" in data:
            success = data["success"]
        if "errors" in data and len(data["errors"]) != 0:
            errors = SplitwiseError(data["errors"])
        if "user" in data and data["user"] is not None:
            added_user = Friend(data["user"])
        
        return success, added_user, errors
    
    async def deleteGroup(self, id: int) -> Tuple[bool, Optional[SplitwiseError]]:
        """Delete a group.
        
        Args:
            id: Group ID to delete
            
        Returns:
            Tuple of (success, errors)
        """
        try:
            content = await self._make_request(f"{base.DELETE_GROUP_URL}/{id}", "POST")
        except SplitwiseNotAllowedException as e:
            e.setMessage(f"You are not allowed to access group with id {id}")
            raise
        except SplitwiseNotFoundException as e:
            e.setMessage(f"Group with id {id} does not exist")
            raise
        
        data = json.loads(content)
        success = data.get("success", False)
        errors = None
        
        if "errors" in data and len(data["errors"]) != 0:
            errors = SplitwiseError(data["errors"])
        
        return success, errors
    
    # ========== Expense Methods ==========
    
    async def getExpenses(
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
        """Get list of expenses with optional filters.
        
        Args:
            offset: Number of expenses to skip
            limit: Max expenses to return
            group_id: Filter by group ID
            friend_id: Filter by friend ID
            dated_after: ISO 8601 date filter
            dated_before: ISO 8601 date filter
            updated_after: ISO 8601 date filter
            updated_before: ISO 8601 date filter
            visible: Show only non-deleted expenses
            
        Returns:
            List of Expense objects
        """
        options = {}
        params = {
            'offset': offset, 'limit': limit, 'group_id': group_id,
            'friend_id': friend_id, 'dated_after': dated_after,
            'dated_before': dated_before, 'updated_after': updated_after,
            'updated_before': updated_before, 'visible': visible
        }
        
        for key, value in params.items():
            if value is not None:
                options[key] = str(value).lower() if isinstance(value, bool) else value
        
        url = base.GET_EXPENSES_URL + self._prepare_options_url(options)
        content = await self._make_request(url)
        data = json.loads(content)
        
        expenses = []
        if "expenses" in data:
            for e in data["expenses"]:
                expenses.append(Expense(e))
        
        return expenses
    
    async def getExpense(self, id: int) -> Optional[Expense]:
        """Get details of a specific expense.
        
        Args:
            id: Expense ID
            
        Returns:
            Expense object
        """
        content = await self._make_request(f"{base.GET_EXPENSE_URL}/{id}")
        data = json.loads(content)
        
        if "expense" in data:
            return Expense(data["expense"])
        return None
    
    async def createExpense(self, expense: Expense) -> Tuple[Optional[Expense], Optional[SplitwiseError]]:
        """Create a new expense.
        
        Args:
            expense: Expense object with expense details
            
        Returns:
            Tuple of (created expense, errors)
        """
        expense_data = expense.__dict__.copy()
        
        # Handle users
        expense_users = expense.getUsers()
        if expense_users:
            del expense_data['users']
            self._set_user_array(expense_users, expense_data)
        
        # Handle category
        category = expense.getCategory()
        if category:
            expense_data["category_id"] = category.getId()
            del expense_data["category"]
        
        # Handle receipt
        files = None
        receipt = expense.getReceiptPath()
        if receipt:
            files = {"receipt": open(receipt, "rb")}
            del expense_data["receiptPath"]
        
        try:
            content = await self._make_request(base.CREATE_EXPENSE_URL, "POST", expense_data, files=files)
        finally:
            if files:
                files["receipt"].close()
        
        data = json.loads(content)
        created_expense = None
        errors = None
        
        if "expenses" in data and len(data["expenses"]) > 0:
            created_expense = Expense(data["expenses"][0])
        if "errors" in data and len(data["errors"]) != 0:
            errors = SplitwiseError(data["errors"])
        
        return created_expense, errors
    
    async def updateExpense(self, expense: Expense) -> Tuple[Optional[Expense], Optional[SplitwiseError]]:
        """Update an existing expense.
        
        Args:
            expense: Expense object with updated data (id required)
            
        Returns:
            Tuple of (updated expense, errors)
        """
        expense_id = expense.id
        if expense_id is None:
            raise SplitwiseBadRequestException("Expense Id cannot be null")
        
        expense_data = expense.__dict__.copy()
        del expense_data['id']
        
        # Handle users
        expense_users = expense.getUsers()
        if expense_users:
            del expense_data['users']
            self._set_user_array(expense_users, expense_data)
        
        # Handle category
        category = expense.getCategory()
        if category:
            expense_data["category_id"] = category.getId()
            del expense_data["category"]
        
        # Remove read-only fields
        readonly_fields = [
            "created_by", "repayments", "next_repeat", "comments_count",
            "updated_by", "transaction_confirmed", "deleted_at", "friendship_id",
            "expense_bundle_id", "updated_at", "deleted_by", "created_at"
        ]
        for field in readonly_fields:
            expense_data.pop(field, None)
        
        # Handle receipt
        files = None
        receipt = expense.getReceiptPath()
        if receipt:
            files = {"receipt": open(receipt, "rb")}
            del expense_data["receiptPath"]
        
        try:
            content = await self._make_request(
                f"{base.UPDATE_EXPENSE_URL}/{expense_id}", "POST", expense_data, files=files
            )
        finally:
            if files:
                files["receipt"].close()
        
        data = json.loads(content)
        updated_expense = None
        errors = None
        
        if "expenses" in data and len(data["expenses"]) > 0:
            updated_expense = Expense(data["expenses"][0])
        if "errors" in data and len(data["errors"]) != 0:
            errors = SplitwiseError(data["errors"])
        
        return updated_expense, errors
    
    async def deleteExpense(self, id: int) -> Tuple[bool, Optional[SplitwiseError]]:
        """Delete an expense.
        
        Args:
            id: Expense ID to delete
            
        Returns:
            Tuple of (success, errors)
        """
        try:
            content = await self._make_request(f"{base.DELETE_EXPENSE_URL}/{id}", "POST")
        except SplitwiseNotAllowedException as e:
            e.setMessage(f"You are not allowed to access expense with id {id}")
            raise
        except SplitwiseNotFoundException as e:
            e.setMessage(f"Expense with id {id} does not exist")
            raise
        
        data = json.loads(content)
        success = data.get("success", False)
        errors = None
        
        if "errors" in data and len(data["errors"]) != 0:
            errors = SplitwiseError(data["errors"])
        
        return success, errors
    
    # ========== Other Methods ==========
    
    async def getCurrencies(self) -> List[Currency]:
        """Get list of supported currencies.
        
        Returns:
            List of Currency objects
        """
        content = await self._make_request(base.GET_CURRENCY_URL)
        data = json.loads(content)
        
        currencies = []
        if "currencies" in data:
            for c in data["currencies"]:
                currencies.append(Currency(c))
        
        return currencies
    
    async def getCategories(self) -> List[Category]:
        """Get list of expense categories.
        
        Returns:
            List of Category objects
        """
        content = await self._make_request(base.GET_CATEGORY_URL)
        data = json.loads(content)
        
        categories = []
        if "categories" in data:
            for c in data["categories"]:
                categories.append(Category(c))
        
        return categories
    
    async def getComments(self, expense_id: int) -> List[Comment]:
        """Get comments for an expense.
        
        Args:
            expense_id: Expense ID
            
        Returns:
            List of Comment objects
        """
        try:
            content = await self._make_request(f"{base.GET_COMMENTS_URL}?expense_id={expense_id}")
        except SplitwiseNotAllowedException as e:
            e.setMessage(f"You are not allowed to fetch expense with id {expense_id}")
            raise
        except SplitwiseNotFoundException as e:
            e.setMessage(f"Expense with id {expense_id} does not exist")
            raise
        
        data = json.loads(content)
        comments = []
        if "comments" in data:
            for c in data["comments"]:
                comments.append(Comment(c))
        
        return comments
    
    async def createComment(self, expense_id: int, content: str) -> Tuple[Optional[Comment], Optional[SplitwiseError]]:
        """Create a comment on an expense.
        
        Args:
            expense_id: Expense ID
            content: Comment content
            
        Returns:
            Tuple of (created comment, errors)
        """
        if content is None:
            raise SplitwiseBadRequestException("Content cannot be empty")
        
        request_data = {
            "expense_id": expense_id,
            "content": content
        }
        
        try:
            response = await self._make_request(base.CREATE_COMMENT_URL, "POST", request_data)
        except SplitwiseNotAllowedException as e:
            e.setMessage(f"You are not allowed to access expense with id {expense_id}")
            raise
        except SplitwiseNotFoundException as e:
            e.setMessage(f"Expense with id {expense_id} does not exist")
            raise
        
        data = json.loads(response)
        comment = None
        errors = None
        
        if "comment" in data and len(data["comment"]) > 0:
            comment = Comment(data["comment"])
        if "errors" in data and len(data["errors"]) != 0:
            errors = SplitwiseError(data["errors"])
        
        return comment, errors
    
    async def getNotifications(self, updated_since: Optional[str] = None, limit: Optional[int] = None) -> List[Notification]:
        """Get user notifications.
        
        Args:
            updated_since: ISO 8601 timestamp filter
            limit: Max notifications to return
            
        Returns:
            List of Notification objects
        """
        try:
            content = await self._make_request(base.GET_NOTIFICATIONS_URL)
        except SplitwiseNotAllowedException as e:
            e.setMessage("You are not allowed to fetch notifications")
            raise
        
        data = json.loads(content)
        notifications = []
        if "notifications" in data:
            for n in data["notifications"]:
                notifications.append(Notification(n))
        
        return notifications
    
    # ========== Batch/Concurrent Operations ==========
    
    async def getAllGroupsWithExpenses(self, limit_per_group: int = 50) -> Dict[int, List[Expense]]:
        """Fetch all groups and their expenses concurrently.
        
        Optimized for edge devices - fetches all data in parallel.
        
        Args:
            limit_per_group: Max expenses per group
            
        Returns:
            Dict mapping group_id to list of expenses
        """
        groups = await self.getGroups()
        
        async def fetch_group_expenses(group: Group) -> Tuple[int, List[Expense]]:
            expenses = await self.getExpenses(group_id=group.getId(), limit=limit_per_group)
            return group.getId(), expenses
        
        results = await asyncio.gather(*[
            fetch_group_expenses(g) for g in groups
        ], return_exceptions=True)
        
        group_expenses = {}
        for result in results:
            if isinstance(result, tuple):
                group_id, expenses = result
                group_expenses[group_id] = expenses
        
        return group_expenses
    
    async def getAllExpensesPaginated(
        self,
        group_id: Optional[int] = None,
        page_size: int = 100,
        max_pages: int = 10
    ) -> List[Expense]:
        """Fetch all expenses with automatic pagination.
        
        Memory-efficient paginated fetching.
        
        Args:
            group_id: Optional group filter
            page_size: Expenses per page
            max_pages: Maximum pages to fetch
            
        Returns:
            List of all expenses
        """
        all_expenses = []
        
        for page in range(max_pages):
            offset = page * page_size
            expenses = await self.getExpenses(
                group_id=group_id,
                offset=offset,
                limit=page_size
            )
            
            if not expenses:
                break
            
            all_expenses.extend(expenses)
            
            if len(expenses) < page_size:
                break
        
        return all_expenses
    
    # ========== Helper Methods ==========
    
    @staticmethod
    def _set_user_array(users: List, user_array: Dict) -> None:
        """Convert user list to indexed dict format for API.
        
        Args:
            users: List of user objects
            user_array: Dict to populate
        """
        for count, user in enumerate(users):
            user_dict = user.__dict__
            for key in user_dict:
                if key == "id":
                    gen_key = "user_id"
                elif key == "picture":
                    continue
                else:
                    gen_key = key
                user_array[f"users__{count}__{gen_key}"] = user_dict[key]

"""Async tests for user-related methods in AsyncSplitwise.

Uses aioresponses to mock aiohttp requests.
"""

import pytest
from aioresponses import aioresponses
from splitwise.async_client import AsyncSplitwise
from splitwise import base


# Sample response data
CURRENT_USER_RESPONSE = {
    "user": {
        "id": 12345,
        "first_name": "Naman",
        "last_name": "Aggarwal",
        "picture": {
            "small": "https://splitwise.s3.amazonaws.com/uploads/user/avatar/12345/small_mypic.jpg",
            "medium": "https://splitwise.s3.amazonaws.com/uploads/user/avatar/12345/medium_mypic.jpg",
            "large": "https://splitwise.s3.amazonaws.com/uploads/user/avatar/12345/large_mypic.jpg"
        },
        "custom_picture": True,
        "email": "naman@naman.com",
        "registration_status": "confirmed",
        "force_refresh_at": "2017-03-18T11:41:36Z",
        "locale": "en",
        "country_code": "IN",
        "date_format": "MM/DD/YYYY",
        "default_currency": "SGD",
        "default_group_id": None,
        "notifications_read": "2020-06-10T14:12:01Z",
        "notifications_count": 8,
        "notifications": {
            "added_as_friend": True,
            "added_to_group": True,
            "expense_added": False,
            "expense_updated": False,
            "bills": True,
            "payments": True,
            "monthly_summary": True,
            "announcements": True
        }
    }
}

USER_RESPONSE = {
    "user": {
        "id": 67890,
        "first_name": "John",
        "last_name": "Doe",
        "picture": {
            "small": "https://example.com/small.jpg",
            "medium": "https://example.com/medium.jpg",
            "large": "https://example.com/large.jpg"
        },
        "email": "john@example.com",
        "registration_status": "confirmed"
    }
}

FRIENDS_RESPONSE = {
    "friends": [
        {
            "id": 11111,
            "first_name": "Alice",
            "last_name": "Smith",
            "email": "alice@example.com",
            "registration_status": "confirmed",
            "picture": {
                "small": "https://example.com/alice_small.jpg",
                "medium": "https://example.com/alice_medium.jpg",
                "large": "https://example.com/alice_large.jpg"
            },
            "balance": [],
            "groups": []
        },
        {
            "id": 22222,
            "first_name": "Bob",
            "last_name": "Jones",
            "email": "bob@example.com",
            "registration_status": "confirmed",
            "picture": {
                "small": "https://example.com/bob_small.jpg",
                "medium": "https://example.com/bob_medium.jpg",
                "large": "https://example.com/bob_large.jpg"
            },
            "balance": [],
            "groups": []
        }
    ]
}


class TestAsyncGetCurrentUser:
    """Test cases for getCurrentUser async method."""

    @pytest.mark.asyncio
    async def test_get_current_user_success(self):
        """Test successful getCurrentUser call."""
        with aioresponses() as m:
            m.get(base.GET_CURRENT_USER_URL, payload=CURRENT_USER_RESPONSE)
            
            async with AsyncSplitwise("key", "secret", api_key="test_key") as sw:
                user = await sw.getCurrentUser()
                
                assert user.getId() == 12345
                assert user.getFirstName() == "Naman"
                assert user.getLastName() == "Aggarwal"
                assert user.getEmail() == "naman@naman.com"
                assert user.getRegistrationStatus() == "confirmed"

    @pytest.mark.asyncio
    async def test_get_current_user_with_picture(self):
        """Test getCurrentUser returns picture data."""
        with aioresponses() as m:
            m.get(base.GET_CURRENT_USER_URL, payload=CURRENT_USER_RESPONSE)
            
            async with AsyncSplitwise("key", "secret", api_key="test_key") as sw:
                user = await sw.getCurrentUser()
                
                picture = user.getPicture()
                assert picture.getSmall() == "https://splitwise.s3.amazonaws.com/uploads/user/avatar/12345/small_mypic.jpg"
                assert picture.getMedium() == "https://splitwise.s3.amazonaws.com/uploads/user/avatar/12345/medium_mypic.jpg"
                assert picture.getLarge() == "https://splitwise.s3.amazonaws.com/uploads/user/avatar/12345/large_mypic.jpg"


class TestAsyncGetUser:
    """Test cases for getUser async method."""

    @pytest.mark.asyncio
    async def test_get_user_success(self):
        """Test successful getUser call."""
        with aioresponses() as m:
            m.get(f"{base.GET_USER_URL}/67890", payload=USER_RESPONSE)
            
            async with AsyncSplitwise("key", "secret", api_key="test_key") as sw:
                user = await sw.getUser(67890)
                
                assert user.getId() == 67890
                assert user.getFirstName() == "John"
                assert user.getLastName() == "Doe"

    @pytest.mark.asyncio
    async def test_get_user_not_found(self):
        """Test getUser with non-existent user."""
        from splitwise.exception import SplitwiseNotFoundException
        
        with aioresponses() as m:
            m.get(f"{base.GET_USER_URL}/99999", status=404)
            
            async with AsyncSplitwise("key", "secret", api_key="test_key") as sw:
                with pytest.raises(SplitwiseNotFoundException):
                    await sw.getUser(99999)


class TestAsyncGetFriends:
    """Test cases for getFriends async method."""

    @pytest.mark.asyncio
    async def test_get_friends_success(self):
        """Test successful getFriends call."""
        with aioresponses() as m:
            m.get(base.GET_FRIENDS_URL, payload=FRIENDS_RESPONSE)
            
            async with AsyncSplitwise("key", "secret", api_key="test_key") as sw:
                friends = await sw.getFriends()
                
                assert len(friends) == 2
                assert friends[0].getId() == 11111
                assert friends[0].getFirstName() == "Alice"
                assert friends[1].getId() == 22222
                assert friends[1].getFirstName() == "Bob"

    @pytest.mark.asyncio
    async def test_get_friends_empty(self):
        """Test getFriends with no friends."""
        with aioresponses() as m:
            m.get(base.GET_FRIENDS_URL, payload={"friends": []})
            
            async with AsyncSplitwise("key", "secret", api_key="test_key") as sw:
                friends = await sw.getFriends()
                
                assert len(friends) == 0


class TestAsyncConcurrentRequests:
    """Test concurrent request handling."""

    @pytest.mark.asyncio
    async def test_concurrent_user_and_friends(self):
        """Test fetching user and friends concurrently."""
        import asyncio
        
        with aioresponses() as m:
            m.get(base.GET_CURRENT_USER_URL, payload=CURRENT_USER_RESPONSE)
            m.get(base.GET_FRIENDS_URL, payload=FRIENDS_RESPONSE)
            
            async with AsyncSplitwise("key", "secret", api_key="test_key") as sw:
                user, friends = await asyncio.gather(
                    sw.getCurrentUser(),
                    sw.getFriends()
                )
                
                assert user.getId() == 12345
                assert len(friends) == 2

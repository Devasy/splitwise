"""Async tests for group-related methods in AsyncSplitwise.

Uses aioresponses to mock aiohttp requests.
"""

import pytest
from aioresponses import aioresponses
from splitwise.async_client import AsyncSplitwise
from splitwise import base


# Sample response data
GROUPS_RESPONSE = {
    "groups": [
        {
            "id": 100,
            "name": "Apartment",
            "created_at": "2020-01-01T00:00:00Z",
            "updated_at": "2020-06-01T00:00:00Z",
            "simplify_by_default": False,
            "group_type": "apartment",
            "original_debts": [],
            "simplified_debts": [],
            "members": [
                {
                    "id": 12345,
                    "first_name": "Naman",
                    "last_name": "Aggarwal",
                    "email": "naman@naman.com",
                    "registration_status": "confirmed",
                    "picture": {
                        "small": "https://example.com/small.jpg",
                        "medium": "https://example.com/medium.jpg",
                        "large": "https://example.com/large.jpg"
                    },
                    "balance": []
                }
            ]
        },
        {
            "id": 200,
            "name": "Trip to Paris",
            "created_at": "2020-02-01T00:00:00Z",
            "updated_at": "2020-07-01T00:00:00Z",
            "simplify_by_default": True,
            "group_type": "trip",
            "original_debts": [],
            "simplified_debts": [],
            "members": []
        }
    ]
}

GROUP_RESPONSE = {
    "group": {
        "id": 100,
        "name": "Apartment",
        "created_at": "2020-01-01T00:00:00Z",
        "updated_at": "2020-06-01T00:00:00Z",
        "simplify_by_default": False,
        "group_type": "apartment",
        "whiteboard": "Welcome to the apartment group!",
        "invite_link": "https://splitwise.com/join/abc123",
        "original_debts": [
            {"from": 12345, "to": 67890, "amount": "50.00", "currency_code": "USD"}
        ],
        "simplified_debts": [
            {"from": 12345, "to": 67890, "amount": "50.00", "currency_code": "USD"}
        ],
        "members": [
            {
                "id": 12345,
                "first_name": "Naman",
                "last_name": "Aggarwal",
                "email": "naman@naman.com",
                "registration_status": "confirmed",
                "picture": {
                    "small": "https://example.com/small.jpg",
                    "medium": "https://example.com/medium.jpg",
                    "large": "https://example.com/large.jpg"
                },
                "balance": []
            },
            {
                "id": 67890,
                "first_name": "John",
                "last_name": "Doe",
                "email": "john@example.com",
                "registration_status": "confirmed",
                "picture": {
                    "small": "https://example.com/john_small.jpg",
                    "medium": "https://example.com/john_medium.jpg",
                    "large": "https://example.com/john_large.jpg"
                },
                "balance": []
            }
        ]
    }
}

CREATE_GROUP_RESPONSE = {
    "group": {
        "id": 300,
        "name": "New Group",
        "created_at": "2020-03-01T00:00:00Z",
        "updated_at": "2020-03-01T00:00:00Z",
        "simplify_by_default": False,
        "original_debts": [],
        "simplified_debts": [],
        "members": []
    }
}

DELETE_GROUP_RESPONSE = {
    "success": True
}


class TestAsyncGetGroups:
    """Test cases for getGroups async method."""

    @pytest.mark.asyncio
    async def test_get_groups_success(self):
        """Test successful getGroups call."""
        with aioresponses() as m:
            m.get(base.GET_GROUPS_URL, payload=GROUPS_RESPONSE)
            
            async with AsyncSplitwise("key", "secret", api_key="test_key") as sw:
                groups = await sw.getGroups()
                
                assert len(groups) == 2
                assert groups[0].getId() == 100
                assert groups[0].getName() == "Apartment"
                assert groups[1].getId() == 200
                assert groups[1].getName() == "Trip to Paris"

    @pytest.mark.asyncio
    async def test_get_groups_with_members(self):
        """Test getGroups returns group members."""
        with aioresponses() as m:
            m.get(base.GET_GROUPS_URL, payload=GROUPS_RESPONSE)
            
            async with AsyncSplitwise("key", "secret", api_key="test_key") as sw:
                groups = await sw.getGroups()
                
                members = groups[0].getMembers()
                assert len(members) == 1
                assert members[0].getId() == 12345
                assert members[0].getFirstName() == "Naman"

    @pytest.mark.asyncio
    async def test_get_groups_empty(self):
        """Test getGroups with no groups."""
        with aioresponses() as m:
            m.get(base.GET_GROUPS_URL, payload={"groups": []})
            
            async with AsyncSplitwise("key", "secret", api_key="test_key") as sw:
                groups = await sw.getGroups()
                
                assert len(groups) == 0


class TestAsyncGetGroup:
    """Test cases for getGroup async method."""

    @pytest.mark.asyncio
    async def test_get_group_success(self):
        """Test successful getGroup call."""
        with aioresponses() as m:
            m.get(f"{base.GET_GROUP_URL}/100", payload=GROUP_RESPONSE)
            
            async with AsyncSplitwise("key", "secret", api_key="test_key") as sw:
                group = await sw.getGroup(100)
                
                assert group.getId() == 100
                assert group.getName() == "Apartment"
                assert len(group.getMembers()) == 2

    @pytest.mark.asyncio
    async def test_get_group_with_debts(self):
        """Test getGroup returns debt information."""
        with aioresponses() as m:
            m.get(f"{base.GET_GROUP_URL}/100", payload=GROUP_RESPONSE)
            
            async with AsyncSplitwise("key", "secret", api_key="test_key") as sw:
                group = await sw.getGroup(100)
                
                original_debts = group.getOriginalDebts()
                assert len(original_debts) == 1

    @pytest.mark.asyncio
    async def test_get_group_not_found(self):
        """Test getGroup with non-existent group."""
        from splitwise.exception import SplitwiseNotFoundException
        
        with aioresponses() as m:
            m.get(f"{base.GET_GROUP_URL}/99999", status=404)
            
            async with AsyncSplitwise("key", "secret", api_key="test_key") as sw:
                with pytest.raises(SplitwiseNotFoundException):
                    await sw.getGroup(99999)


class TestAsyncDeleteGroup:
    """Test cases for deleteGroup async method."""

    @pytest.mark.asyncio
    async def test_delete_group_success(self):
        """Test successful deleteGroup call."""
        with aioresponses() as m:
            m.post(f"{base.DELETE_GROUP_URL}/100", payload=DELETE_GROUP_RESPONSE)
            
            async with AsyncSplitwise("key", "secret", api_key="test_key") as sw:
                success, errors = await sw.deleteGroup(100)
                
                assert success is True
                assert errors is None

    @pytest.mark.asyncio
    async def test_delete_group_not_found(self):
        """Test deleteGroup with non-existent group."""
        from splitwise.exception import SplitwiseNotFoundException
        
        with aioresponses() as m:
            m.post(f"{base.DELETE_GROUP_URL}/99999", status=404)
            
            async with AsyncSplitwise("key", "secret", api_key="test_key") as sw:
                with pytest.raises(SplitwiseNotFoundException):
                    await sw.deleteGroup(99999)


class TestAsyncConcurrentGroupRequests:
    """Test concurrent group request handling."""

    @pytest.mark.asyncio
    async def test_concurrent_groups_fetch(self):
        """Test fetching multiple groups concurrently."""
        import asyncio
        
        group1_response = {"group": {**GROUP_RESPONSE["group"], "id": 100}}
        group2_response = {"group": {**GROUP_RESPONSE["group"], "id": 200, "name": "Trip to Paris"}}
        
        with aioresponses() as m:
            m.get(f"{base.GET_GROUP_URL}/100", payload=group1_response)
            m.get(f"{base.GET_GROUP_URL}/200", payload=group2_response)
            
            async with AsyncSplitwise("key", "secret", api_key="test_key") as sw:
                group1, group2 = await asyncio.gather(
                    sw.getGroup(100),
                    sw.getGroup(200)
                )
                
                assert group1.getId() == 100
                assert group2.getId() == 200

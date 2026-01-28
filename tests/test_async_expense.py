"""Async tests for expense-related methods in AsyncSplitwise.

Uses aioresponses to mock aiohttp requests.
"""

import pytest
from aioresponses import aioresponses
from splitwise.async_client import AsyncSplitwise
from splitwise import base


# Sample expense data
EXPENSE_DATA = {
    "id": 50000,
    "group_id": 100,
    "description": "Dinner",
    "repeats": False,
    "repeat_interval": "never",
    "email_reminder": False,
    "email_reminder_in_advance": -1,
    "next_repeat": None,
    "details": "Italian restaurant",
    "comments_count": 0,
    "payment": False,
    "creation_method": "split",
    "transaction_method": "offline",
    "transaction_confirmed": False,
    "cost": "100.00",
    "currency_code": "USD",
    "created_by": {
        "id": 12345,
        "first_name": "Naman",
        "last_name": "Aggarwal",
        "picture": {
            "small": "https://example.com/small.jpg",
            "medium": "https://example.com/medium.jpg",
            "large": "https://example.com/large.jpg"
        },
        "email": "naman@naman.com"
    },
    "date": "2020-06-15T00:00:00Z",
    "created_at": "2020-06-15T12:00:00Z",
    "updated_at": "2020-06-15T12:00:00Z",
    "deleted_at": None,
    "receipt": {"large": None, "original": None},
    "category": {
        "id": 18,
        "name": "Food and Drink"
    },
    "updated_by": None,
    "deleted_by": None,
    "repayments": [
        {"from": 67890, "to": 12345, "amount": "50.00"}
    ],
    "users": [
        {
            "user": {
                "id": 12345,
                "first_name": "Naman",
                "last_name": "Aggarwal",
                "picture": {
                    "small": "https://example.com/small.jpg",
                    "medium": "https://example.com/medium.jpg",
                    "large": "https://example.com/large.jpg"
                }
            },
            "user_id": 12345,
            "paid_share": "100.00",
            "owed_share": "50.00",
            "net_balance": "50.00"
        },
        {
            "user": {
                "id": 67890,
                "first_name": "John",
                "last_name": "Doe",
                "picture": {
                    "small": "https://example.com/john_small.jpg",
                    "medium": "https://example.com/john_medium.jpg",
                    "large": "https://example.com/john_large.jpg"
                }
            },
            "user_id": 67890,
            "paid_share": "0.00",
            "owed_share": "50.00",
            "net_balance": "-50.00"
        }
    ]
}

EXPENSES_RESPONSE = {
    "expenses": [
        EXPENSE_DATA,
        {**EXPENSE_DATA, "id": 50001, "description": "Lunch", "cost": "30.00"}
    ]
}

EXPENSE_RESPONSE = {
    "expense": EXPENSE_DATA
}

CREATE_EXPENSE_RESPONSE = {
    "expenses": [EXPENSE_DATA]
}

DELETE_EXPENSE_RESPONSE = {
    "success": True
}


class TestAsyncGetExpenses:
    """Test cases for getExpenses async method."""

    @pytest.mark.asyncio
    async def test_get_expenses_success(self):
        """Test successful getExpenses call."""
        with aioresponses() as m:
            m.get(base.GET_EXPENSES_URL, payload=EXPENSES_RESPONSE)
            
            async with AsyncSplitwise("key", "secret", api_key="test_key") as sw:
                expenses = await sw.getExpenses()
                
                assert len(expenses) == 2
                assert expenses[0].getId() == 50000
                assert expenses[0].getDescription() == "Dinner"
                assert expenses[0].getCost() == "100.00"
                assert expenses[1].getId() == 50001
                assert expenses[1].getDescription() == "Lunch"

    @pytest.mark.asyncio
    async def test_get_expenses_with_group_filter(self):
        """Test getExpenses with group_id filter."""
        with aioresponses() as m:
            m.get(f"{base.GET_EXPENSES_URL}?group_id=100", payload=EXPENSES_RESPONSE)
            
            async with AsyncSplitwise("key", "secret", api_key="test_key") as sw:
                expenses = await sw.getExpenses(group_id=100)
                
                assert len(expenses) == 2
                assert all(e.getGroupId() == 100 for e in expenses)

    @pytest.mark.asyncio
    async def test_get_expenses_with_limit(self):
        """Test getExpenses with limit."""
        with aioresponses() as m:
            m.get(f"{base.GET_EXPENSES_URL}?limit=10", payload={"expenses": [EXPENSE_DATA]})
            
            async with AsyncSplitwise("key", "secret", api_key="test_key") as sw:
                expenses = await sw.getExpenses(limit=10)
                
                assert len(expenses) == 1

    @pytest.mark.asyncio
    async def test_get_expenses_with_date_filters(self):
        """Test getExpenses with date filters."""
        with aioresponses() as m:
            m.get(
                f"{base.GET_EXPENSES_URL}?dated_after=2020-01-01&dated_before=2020-12-31",
                payload=EXPENSES_RESPONSE
            )
            
            async with AsyncSplitwise("key", "secret", api_key="test_key") as sw:
                expenses = await sw.getExpenses(
                    dated_after="2020-01-01",
                    dated_before="2020-12-31"
                )
                
                assert len(expenses) == 2

    @pytest.mark.asyncio
    async def test_get_expenses_empty(self):
        """Test getExpenses with no expenses."""
        with aioresponses() as m:
            m.get(base.GET_EXPENSES_URL, payload={"expenses": []})
            
            async with AsyncSplitwise("key", "secret", api_key="test_key") as sw:
                expenses = await sw.getExpenses()
                
                assert len(expenses) == 0


class TestAsyncGetExpense:
    """Test cases for getExpense async method."""

    @pytest.mark.asyncio
    async def test_get_expense_success(self):
        """Test successful getExpense call."""
        with aioresponses() as m:
            m.get(f"{base.GET_EXPENSE_URL}/50000", payload=EXPENSE_RESPONSE)
            
            async with AsyncSplitwise("key", "secret", api_key="test_key") as sw:
                expense = await sw.getExpense(50000)
                
                assert expense.getId() == 50000
                assert expense.getDescription() == "Dinner"
                assert expense.getCost() == "100.00"
                assert expense.getCurrencyCode() == "USD"

    @pytest.mark.asyncio
    async def test_get_expense_with_users(self):
        """Test getExpense returns user data."""
        with aioresponses() as m:
            m.get(f"{base.GET_EXPENSE_URL}/50000", payload=EXPENSE_RESPONSE)
            
            async with AsyncSplitwise("key", "secret", api_key="test_key") as sw:
                expense = await sw.getExpense(50000)
                
                users = expense.getUsers()
                assert len(users) == 2

    @pytest.mark.asyncio
    async def test_get_expense_with_category(self):
        """Test getExpense returns category data."""
        with aioresponses() as m:
            m.get(f"{base.GET_EXPENSE_URL}/50000", payload=EXPENSE_RESPONSE)
            
            async with AsyncSplitwise("key", "secret", api_key="test_key") as sw:
                expense = await sw.getExpense(50000)
                
                category = expense.getCategory()
                assert category.getId() == 18
                assert category.getName() == "Food and Drink"


class TestAsyncDeleteExpense:
    """Test cases for deleteExpense async method."""

    @pytest.mark.asyncio
    async def test_delete_expense_success(self):
        """Test successful deleteExpense call."""
        with aioresponses() as m:
            m.post(f"{base.DELETE_EXPENSE_URL}/50000", payload=DELETE_EXPENSE_RESPONSE)
            
            async with AsyncSplitwise("key", "secret", api_key="test_key") as sw:
                success, errors = await sw.deleteExpense(50000)
                
                assert success is True
                assert errors is None

    @pytest.mark.asyncio
    async def test_delete_expense_not_found(self):
        """Test deleteExpense with non-existent expense."""
        from splitwise.exception import SplitwiseNotFoundException
        
        with aioresponses() as m:
            m.post(f"{base.DELETE_EXPENSE_URL}/99999", status=404)
            
            async with AsyncSplitwise("key", "secret", api_key="test_key") as sw:
                with pytest.raises(SplitwiseNotFoundException):
                    await sw.deleteExpense(99999)


class TestAsyncBatchOperations:
    """Test batch/concurrent expense operations."""

    @pytest.mark.asyncio
    async def test_get_all_expenses_paginated(self):
        """Test getAllExpensesPaginated fetches multiple pages."""
        with aioresponses() as m:
            # First page - full
            m.get(
                f"{base.GET_EXPENSES_URL}?offset=0&limit=2",
                payload={"expenses": [
                    {**EXPENSE_DATA, "id": 1},
                    {**EXPENSE_DATA, "id": 2}
                ]}
            )
            # Second page - partial (signals end)
            m.get(
                f"{base.GET_EXPENSES_URL}?offset=2&limit=2",
                payload={"expenses": [
                    {**EXPENSE_DATA, "id": 3}
                ]}
            )
            
            async with AsyncSplitwise("key", "secret", api_key="test_key") as sw:
                expenses = await sw.getAllExpensesPaginated(page_size=2, max_pages=10)
                
                assert len(expenses) == 3
                assert [e.getId() for e in expenses] == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_concurrent_expense_fetches(self):
        """Test fetching multiple expenses concurrently."""
        import asyncio
        
        with aioresponses() as m:
            m.get(f"{base.GET_EXPENSE_URL}/50000", payload={"expense": {**EXPENSE_DATA, "id": 50000}})
            m.get(f"{base.GET_EXPENSE_URL}/50001", payload={"expense": {**EXPENSE_DATA, "id": 50001}})
            m.get(f"{base.GET_EXPENSE_URL}/50002", payload={"expense": {**EXPENSE_DATA, "id": 50002}})
            
            async with AsyncSplitwise("key", "secret", api_key="test_key") as sw:
                expenses = await asyncio.gather(
                    sw.getExpense(50000),
                    sw.getExpense(50001),
                    sw.getExpense(50002)
                )
                
                assert len(expenses) == 3
                assert [e.getId() for e in expenses] == [50000, 50001, 50002]


class TestAsyncErrorHandling:
    """Test error handling in async expense methods."""

    @pytest.mark.asyncio
    async def test_unauthorized_error(self):
        """Test 401 error handling."""
        from splitwise.exception import SplitwiseUnauthorizedException
        
        with aioresponses() as m:
            m.get(base.GET_EXPENSES_URL, status=401)
            
            async with AsyncSplitwise("key", "secret", api_key="bad_key") as sw:
                with pytest.raises(SplitwiseUnauthorizedException):
                    await sw.getExpenses()

    @pytest.mark.asyncio
    async def test_forbidden_error(self):
        """Test 403 error handling."""
        from splitwise.exception import SplitwiseNotAllowedException
        
        with aioresponses() as m:
            m.get(f"{base.GET_EXPENSE_URL}/50000", status=403)
            
            async with AsyncSplitwise("key", "secret", api_key="test_key") as sw:
                with pytest.raises(SplitwiseNotAllowedException):
                    await sw.getExpense(50000)

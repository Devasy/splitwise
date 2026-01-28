"""Base constants and URLs for Splitwise API.

This module contains shared constants used by both sync and async clients.
"""

# Base URLs
SPLITWISE_BASE_URL = "https://secure.splitwise.com/"
SPLITWISE_VERSION = "v3.0"
OAUTH_BASE_URL = "https://www.splitwise.com/"

# OAuth URLs
REQUEST_TOKEN_URL = SPLITWISE_BASE_URL + "api/" + SPLITWISE_VERSION + "/get_request_token"
ACCESS_TOKEN_URL = SPLITWISE_BASE_URL + "api/" + SPLITWISE_VERSION + "/get_access_token"
AUTHORIZE_URL = SPLITWISE_BASE_URL + "authorize"
OAUTH_AUTHORIZE_URL = OAUTH_BASE_URL + "oauth/authorize"
OAUTH2_TOKEN_URL = OAUTH_BASE_URL + "oauth/token"

# API Endpoints
GET_CURRENT_USER_URL = SPLITWISE_BASE_URL + "api/" + SPLITWISE_VERSION + "/get_current_user"
GET_USER_URL = SPLITWISE_BASE_URL + "api/" + SPLITWISE_VERSION + "/get_user"
UPDATE_USER_URL = SPLITWISE_BASE_URL + "api/" + SPLITWISE_VERSION + "/update_user"
GET_FRIENDS_URL = SPLITWISE_BASE_URL + "api/" + SPLITWISE_VERSION + "/get_friends"
GET_GROUPS_URL = SPLITWISE_BASE_URL + "api/" + SPLITWISE_VERSION + "/get_groups"
GET_GROUP_URL = SPLITWISE_BASE_URL + "api/" + SPLITWISE_VERSION + "/get_group"
GET_CURRENCY_URL = SPLITWISE_BASE_URL + "api/" + SPLITWISE_VERSION + "/get_currencies"
GET_CATEGORY_URL = SPLITWISE_BASE_URL + "api/" + SPLITWISE_VERSION + "/get_categories"
GET_EXPENSES_URL = SPLITWISE_BASE_URL + "api/" + SPLITWISE_VERSION + "/get_expenses"
GET_EXPENSE_URL = SPLITWISE_BASE_URL + "api/" + SPLITWISE_VERSION + "/get_expense"
CREATE_EXPENSE_URL = SPLITWISE_BASE_URL + "api/" + SPLITWISE_VERSION + "/create_expense"
UPDATE_EXPENSE_URL = SPLITWISE_BASE_URL + "api/" + SPLITWISE_VERSION + "/update_expense"
DELETE_EXPENSE_URL = SPLITWISE_BASE_URL + "api/" + SPLITWISE_VERSION + "/delete_expense"
CREATE_GROUP_URL = SPLITWISE_BASE_URL + "api/" + SPLITWISE_VERSION + "/create_group"
ADD_USER_TO_GROUP_URL = SPLITWISE_BASE_URL + "api/" + SPLITWISE_VERSION + "/add_user_to_group"
DELETE_GROUP_URL = SPLITWISE_BASE_URL + "api/" + SPLITWISE_VERSION + "/delete_group"
GET_COMMENTS_URL = SPLITWISE_BASE_URL + "api/" + SPLITWISE_VERSION + "/get_comments"
CREATE_COMMENT_URL = SPLITWISE_BASE_URL + "api/" + SPLITWISE_VERSION + "/create_comment"
GET_NOTIFICATIONS_URL = SPLITWISE_BASE_URL + "api/" + SPLITWISE_VERSION + "/get_notifications"

# Default timeout for requests (in seconds)
DEFAULT_TIMEOUT = 30

# Connection pool settings for edge/low-compute devices
DEFAULT_POOL_SIZE = 10
DEFAULT_POOL_TIMEOUT = 60

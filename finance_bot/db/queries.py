# finance_bot/db/queries.py
from typing import Optional, Dict, Any, List

# --- User Queries ---

async def get_user(db_conn: Any, telegram_id: int) -> Optional[Dict]:
    print(f"[DB MOCK] Attempting to get user: {telegram_id}")
    # Simulate DB call
    # Example: if telegram_id == 123: return {"telegram_id": telegram_id, "full_name": "Test User", "nickname": "tester"}
    # For the get_user_display_name mock to work well with this, we can pre-populate some users.
    mock_users_store = {
        12345: {"id": 1, "telegram_id": 12345, "full_name": "Alice Payer", "nickname": "alice_mock"},
        67890: {"id": 2, "telegram_id": 67890, "full_name": "Bob Debtor", "nickname": "bob_mock"},
        77777: {"id": 3, "telegram_id": 77777, "full_name": "Charlie Admin", "nickname": "charlie_mock"},
    }
    if telegram_id in mock_users_store:
        return mock_users_store[telegram_id]
    return None

async def add_user(db_conn: Any, telegram_id: int, full_name: str, nickname: Optional[str]) -> Dict:
    print(f"[DB MOCK] Adding user: {telegram_id}, {full_name}, {nickname}")
    # Simulate adding to mock_users_store for consistency, though not strictly needed for this function's return
    # In a real DB, this would insert and potentially return the new user record.
    new_user_id_pk = max(u['id'] for u in (await get_user(db_conn, tid) for tid in [12345, 67890, 77777] if await get_user(db_conn, tid)) if u) +1 if hasattr(add_user,'mock_users_store') else 4
    # For now, just return the input as if it was successfully added/retrieved.
    return {"id": new_user_id_pk, "telegram_id": telegram_id, "full_name": full_name, "nickname": nickname}

async def update_user(db_conn: Any, telegram_id: int, full_name: str, nickname: Optional[str]) -> Dict:
    print(f"[DB MOCK] Updating user: {telegram_id}, {full_name}, {nickname}")
    # Simulate update and return
    return {"id": 1,"telegram_id": telegram_id, "full_name": full_name, "nickname": nickname}


# --- Group Queries ---

# Global mock store for groups to allow status, rules, timer to be reflected across calls
mock_group_data_store: Dict[int, Dict[str, Any]] = {
    # Example: 1: {"telegram_chat_id": -1001, "name": "Test Group", "admin_id": 12345, "status": "active", "rules": "No rules yet", "timer_interval": 24}
}
_next_mock_group_internal_id = 1 # Counter for new group internal IDs

async def get_group(db_conn: Any, telegram_chat_id: int) -> Optional[Dict]:
    global mock_group_data_store
    print(f"[DB MOCK] Attempting to get group by telegram_chat_id: {telegram_chat_id}")
    for internal_id, data in mock_group_data_store.items():
        if data.get("telegram_chat_id") == telegram_chat_id:
            # Return a copy of the stored data, including current status and internal_id
            return {"id": internal_id, **data} # Ensure 'status' is part of data
    return None

async def add_group(db_conn: Any, telegram_chat_id: int, name: str, admin_telegram_id: int) -> Dict:
    global mock_group_data_store, _next_mock_group_internal_id
    
    existing_group = await get_group(db_conn, telegram_chat_id)
    if existing_group:
        print(f"[DB MOCK] Group with telegram_chat_id {telegram_chat_id} already exists with internal ID {existing_group['id']}. Returning existing.")
        # Ensure it has a status if fetched this way
        if 'status' not in existing_group:
             mock_group_data_store[existing_group['id']]['status'] = 'active' # Patch if missing
             existing_group['status'] = 'active'
        return existing_group

    new_internal_id = _next_mock_group_internal_id
    _next_mock_group_internal_id += 1
    
    print(f"[DB MOCK] Adding group: TG_ChatID={telegram_chat_id}, Name='{name}', Admin={admin_telegram_id}. Assigned Internal ID: {new_internal_id}")
    
    group_data = {
        "telegram_chat_id": telegram_chat_id,
        "name": name,
        "admin_id": admin_telegram_id,
        "status": "active", # Default status on creation
        "rules": None,       # Default rules
        "timer_interval": None # Default timer
    }
    mock_group_data_store[new_internal_id] = group_data
    
    return {"id": new_internal_id, **group_data}

async def update_group_admin(db_conn: Any, telegram_chat_id: int, admin_telegram_id: int) -> Optional[Dict]:
    global mock_group_data_store
    print(f"[DB MOCK] Updating group admin for chat_id: {telegram_chat_id}, new admin: {admin_telegram_id}")
    
    internal_id_to_update = None
    for internal_id, data in mock_group_data_store.items():
        if data.get("telegram_chat_id") == telegram_chat_id:
            internal_id_to_update = internal_id
            break
    
    if internal_id_to_update:
        mock_group_data_store[internal_id_to_update]["admin_id"] = admin_telegram_id
        print(f"[DB MOCK] Group {internal_id_to_update} admin updated.")
        return {"id": internal_id_to_update, **mock_group_data_store[internal_id_to_update]}
    
    print(f"[DB MOCK WARNING] Group with chat_id {telegram_chat_id} not found for admin update.")
    return None

async def update_group_rules(db_conn: Any, internal_group_id: int, rules_text: str) -> Optional[Dict]:
    global mock_group_data_store
    print(f"[DB MOCK] Updating rules for group {internal_group_id}. New rules: '{rules_text[:50]}...'")
    if internal_group_id in mock_group_data_store:
        mock_group_data_store[internal_group_id]["rules"] = rules_text
        print(f"[DB MOCK] Group {internal_group_id} rules updated.")
        return {"id": internal_group_id, **mock_group_data_store[internal_group_id]}
    print(f"[DB MOCK WARNING] Group {internal_group_id} not found for rules update.")
    return None

async def update_group_timer(db_conn: Any, internal_group_id: int, interval_hours: int) -> Optional[Dict]:
    global mock_group_data_store
    print(f"[DB MOCK] Updating timer for group {internal_group_id} to {interval_hours} hours.")
    if internal_group_id in mock_group_data_store:
        mock_group_data_store[internal_group_id]["timer_interval"] = interval_hours
        print(f"[DB MOCK] Group {internal_group_id} timer interval updated to {interval_hours} hours.")
        return {"id": internal_group_id, **mock_group_data_store[internal_group_id]}
    print(f"[DB MOCK WARNING] Group {internal_group_id} not found for timer update.")
    return None

async def update_group_status(db_conn: Any, internal_group_id: int, new_status: str) -> Optional[Dict]:
    global mock_group_data_store
    print(f"[DB MOCK] Updating status for group {internal_group_id} to '{new_status}'.")
    if internal_group_id in mock_group_data_store:
        mock_group_data_store[internal_group_id]['status'] = new_status
        print(f"[DB MOCK] Group {internal_group_id} status updated to {new_status}.")
        return {"id": internal_group_id, **mock_group_data_store[internal_group_id]} # Return a copy
    else:
        print(f"[DB MOCK WARNING] Group {internal_group_id} not found in mock_group_data_store during status update.")
        return None

# --- Expense Queries ---

async def create_expense(db_conn: Any, user_id: int, group_id: int, amount: float, description: str, split_type: str = 'PENDING_SPLIT') -> Dict:
    print(f"[DB MOCK] Creating expense: User {user_id} in Group {group_id}, Amount {amount}, Desc: {description}, Split: {split_type}")
    return {"id": 1, "user_id": user_id, "group_id": group_id, "amount": amount, "description": description, "split_type": split_type}

async def get_user_pending_expenses(db_conn: Any, user_telegram_id: int, internal_group_id: int) -> List[Dict]:
    print(f"[DB MOCK] Getting pending expenses for user {user_telegram_id} in group {internal_group_id}")
    # This mock should align with an expense created by create_expense, paid by user_telegram_id in internal_group_id
    # For now, return a generic one if testing split logic.
    return [{"id": 1, "description": "Mocked Pending Expense from get_user_pending_expenses", "amount": 50.0, "user_id": user_telegram_id, "group_id": internal_group_id, "split_type": "PENDING_SPLIT"}]

async def get_group_members_telegram_ids(db_conn: Any, internal_group_id: int) -> List[int]:
    print(f"[DB MOCK] Getting member telegram_ids for group {internal_group_id}")
    # This is a placeholder. In reality, you'd query a group_members table or users associated with the group.
    # For testing, ensure this list contains distinct mock telegram_ids.
    # Let's assume the group (internal_group_id 1) might have users 12345, 67890, 77777.
    if internal_group_id == 1: # Example specific group
        return [12345, 67890, 77777] 
    return [11111, 22222] # Default mock members for other groups

async def add_expense_participants(db_conn: Any, expense_id: int, participants_data: List[Dict[str, Any]]) -> None:
    print(f"[DB MOCK] Adding participants for expense {expense_id}: {participants_data}")
    return None

async def update_expense_split_type(db_conn: Any, expense_id: int, new_split_type: str) -> Optional[Dict]:
    print(f"[DB MOCK] Updating expense {expense_id} to split_type {new_split_type}")
    return {"id": expense_id, "split_type": new_split_type}


# --- Debt and Transaction Queries ---

async def get_user_total_owed_to_them(db_conn: Any, user_telegram_id: int, internal_group_id: Optional[int] = None) -> List[Dict]:
    print(f"[DB MOCK] Getting amounts owed TO user {user_telegram_id} (group: {internal_group_id})")
    if user_telegram_id == 12345: 
         return [{"owed_by_user_telegram_id": 67890, "amount": 10.00, "expense_description": "Pizza Night", "group_id": 1, "expense_id":1}]
    return []

async def get_user_total_they_owe(db_conn: Any, user_telegram_id: int, internal_group_id: Optional[int] = None) -> List[Dict]:
    print(f"[DB MOCK] Getting amounts OWED BY user {user_telegram_id} (group: {internal_group_id})")
    if user_telegram_id == 67890: 
        return [{"owed_to_user_telegram_id": 12345, "amount": 10.00, "expense_description": "Pizza Night", "group_id": 1, "expense_id":1}]
    if user_telegram_id == 77777:
         return [{"owed_to_user_telegram_id": 12345, "amount": 25.00, "expense_description": "Movie Tickets", "group_id": 1, "expense_id":2}]
    return []

async def get_confirmed_transactions_summary(db_conn: Any, user_telegram_id: int, internal_group_id: Optional[int] = None) -> Dict[str, float]:
    print(f"[DB MOCK] Getting confirmed transactions for user {user_telegram_id} (group: {internal_group_id})")
    if user_telegram_id == 67890: return {"sent": 5.00, "received": 0.0}
    if user_telegram_id == 12345: return {"sent": 0.0, "received": 5.00}
    return {"sent": 0.0, "received": 0.0}

async def get_user_display_name(db_conn: Any, user_telegram_id: int) -> str:
    user_details = await get_user(db_conn, user_telegram_id) # Uses the enhanced get_user mock
    if user_details and user_details.get('full_name'):
        return user_details['full_name']
    # Fallback if user not in our limited mock_users_store
    return f"User_{user_telegram_id}"

async def get_user_by_nickname(db_conn: Any, nickname: str) -> Optional[Dict]:
    print(f"[DB MOCK] Getting user by nickname: @{nickname}")
    # Uses the enhanced get_user mock by looking up its mock_users_store via telegram_id
    mock_nick_to_id = { "alice_mock": 12345, "bob_mock": 67890, "charlie_mock": 77777 }
    if nickname in mock_nick_to_id:
        return await get_user(db_conn, mock_nick_to_id[nickname])
    return None

async def create_transaction(db_conn: Any, sender_telegram_id: int, receiver_telegram_id: int, amount: float, internal_group_id: Optional[int] = None, status: str = 'pending') -> Dict:
    print(f"[DB MOCK] Creating transaction: {sender_telegram_id} -> {receiver_telegram_id}, Amount: {amount}, Group: {internal_group_id}, Status: {status}")
    return {"id": 123, "sender_id": sender_telegram_id, "receiver_id": receiver_telegram_id, "amount": amount, "status": status, "group_id": internal_group_id}

async def get_transaction_by_id(db_conn: Any, transaction_id: int) -> Optional[Dict]:
    print(f"[DB MOCK] Getting transaction by ID: {transaction_id}")
    if transaction_id == 123: 
         return {"id": 123, "sender_id": 12345, "receiver_id": 67890, "amount": 20.0, "status": "pending", "group_id": 1} # Example
    return None

async def update_transaction_status(db_conn: Any, transaction_id: int, new_status: str) -> Optional[Dict]:
    print(f"[DB MOCK] Updating transaction {transaction_id} to status {new_status}")
    if transaction_id == 123: # Assuming this transaction exists
        return {"id": transaction_id, "sender_id": 12345, "receiver_id": 67890, "amount": 20.0, "status": new_status, "group_id": 1}
    return None

# --- Admin / Group Management Queries ---

async def is_user_group_admin(db_conn: Any, user_telegram_id: int, internal_group_id: int) -> bool:
    global mock_group_data_store
    print(f"[DB MOCK] Checking if user {user_telegram_id} is admin of group {internal_group_id}")
    if internal_group_id in mock_group_data_store:
        is_admin = mock_group_data_store[internal_group_id].get("admin_id") == user_telegram_id
        print(f"[DB MOCK] User {user_telegram_id} admin status for group {internal_group_id}: {is_admin}")
        return is_admin
    print(f"[DB MOCK WARNING] Group {internal_group_id} not found in admin map for is_user_group_admin.")
    return False

async def delete_group_expenses(db_conn: Any, internal_group_id: int) -> bool:
    print(f"[DB MOCK] Deleting all expenses for group {internal_group_id}.")
    return True

async def delete_group_transactions_if_group_specific(db_conn: Any, internal_group_id: int) -> bool:
    print(f"[DB MOCK] Deleting group-specific transactions for group {internal_group_id}.")
    return True

# --- Reporting Queries (Mock) ---

async def get_expenses_for_report(db_conn: Any, internal_group_id: int) -> List[Dict]:
    print(f"[DB MOCK] Getting expenses for report for group {internal_group_id}.")
    # Simulate returning a list of all expenses for the group.
    # Each dict should represent an expense row.
    # Example: [{"id": 1, "amount": 50.0, "description": "Team Lunch", "user_id": 12345, "timestamp": "2023-10-26T10:00:00Z"}, ...]
    return [
        {"id": 1, "amount": 50.0, "description": "Team Lunch", "user_id": 12345, "timestamp": "2023-10-26T10:00:00Z", "group_id": internal_group_id},
        {"id": 2, "amount": 20.0, "description": "Coffee Supplies", "user_id": 67890, "timestamp": "2023-10-27T11:00:00Z", "group_id": internal_group_id}
    ] # Return a couple of mock expenses

async def get_transactions_for_report(db_conn: Any, internal_group_id: int) -> List[Dict]:
    print(f"[DB MOCK] Getting transactions for report for group {internal_group_id}.")
    # Simulate returning a list of all confirmed transactions associated with the group.
    # Each dict should represent a transaction row.
    # Example: [{"id": 101, "sender_id": 12345, "receiver_id": 67890, "amount": 10.0, "status": "confirmed", "confirmed_at": "2023-10-28T12:00:00Z"}, ...]
    # Note: Assumes transactions can be linked to internal_group_id.
    return [
        {"id": 123, "sender_id": 12345, "receiver_id": 67890, "amount": 10.0, "status": "confirmed", "confirmed_at": "2023-10-28T12:00:00Z", "group_id": internal_group_id}
    ] # Return one mock transaction

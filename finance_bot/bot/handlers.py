from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.enums import ChatType, ParseMode 
from aiogram.fsm.context import FSMContext
from typing import Optional, Any, Dict, List 
import sys # For path manipulation if using local imports
import os # For path manipulation

# Attempt to import database query functions and states
try:
    from ..db import queries as db_queries
    # Assuming states.py is in the same directory (bot)
    from .states import AddExpenseStates, SendMoneyStates, AdminStates 
except ImportError:
    # Fallback for local development if run directly from bot directory
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # finance_bot directory
    if parent_dir not in sys.path:
        sys.path.append(parent_dir)
    from db import queries as db_queries
    
    current_dir = os.path.dirname(os.path.abspath(__file__)) # bot directory
    if current_dir not in sys.path:
        sys.path.append(current_dir)
    from states import AddExpenseStates, SendMoneyStates, AdminStates


router = Router()

@router.message(CommandStart())
async def command_start_handler(message: Message) -> None: 
    db_conn: Any = None 
    user_id = message.from_user.id
    full_name = message.from_user.full_name
    nickname = message.from_user.username

    try:
        user = await db_queries.get_user(db_conn, user_id)
        if user:
            if user.get('full_name') != full_name or user.get('nickname') != nickname:
                await db_queries.update_user(db_conn, user_id, full_name, nickname)
        else:
            await db_queries.add_user(db_conn, user_id, full_name, nickname)

        if message.chat.type == ChatType.PRIVATE:
            await message.answer(f"Hello, {full_name}! I'm ready to help manage your finances. You can add me to a group to start tracking shared expenses.")
        elif message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
            telegram_chat_id = message.chat.id
            group_name = message.chat.title
            group_record = await db_queries.get_group(db_conn, telegram_chat_id) # Use group_record consistently

            if group_record:
                await message.answer(f"Hello {full_name}! FinanceBot is active in {group_name} (ID: {group_record['id']}). The group is already registered. Status: {group_record.get('status', 'unknown')}.")
            else:
                new_group = await db_queries.add_group(db_conn, telegram_chat_id, group_name, user_id)
                await message.answer(f"Hello {full_name}! FinanceBot has been activated for the group: {group_name} (ID: {new_group['id']}). You are set as the admin for this group in the bot. Status: {new_group.get('status', 'active')}.")
    except Exception as e:
        print(f"An error occurred in command_start_handler: {e}")
        await message.answer("Sorry, something went wrong while processing your request. Please try again later.")

# --- Add Expense Command Handlers ---
@router.message(Command("addexpense"))
async def command_add_expense_start(message: Message, state: FSMContext):
    db_conn: Any = None 
    if message.chat.type == ChatType.PRIVATE:
        await message.answer("This command can only be used in a group chat where I am active.")
        return

    group_record = await db_queries.get_group(db_conn, message.chat.id) 
    if not group_record: 
        await message.answer("This group is not registered with me yet. Please ask an admin to use /start first.")
        return
    
    # Check group status
    if group_record.get('status') == 'finished': 
        await message.answer(f"Group '{group_record['name']}' is finished. No new expenses can be added unless an admin uses /restart.")
        return
    
    await state.set_state(AddExpenseStates.awaiting_amount)
    await message.answer("Okay, let's add a new expense. Please enter the amount (e.g., 123.45):")

@router.message(AddExpenseStates.awaiting_amount)
async def process_expense_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text)
        if amount <= 0:
            await message.answer("The amount must be a positive number. Please try again:")
            return
        await state.update_data(amount=amount)
        await state.set_state(AddExpenseStates.awaiting_description)
        await message.answer("Got it. Now, please enter a short description for this expense (max 100 characters):")
    except ValueError:
        await message.answer("That doesn't look like a valid amount. Please enter a number (e.g., 123.45):")

@router.message(AddExpenseStates.awaiting_description)
async def process_expense_description(message: Message, state: FSMContext):
    db_conn: Any = None 
    description = message.text
    if not description or len(description) > 100:
        await message.answer("The description cannot be empty and must be 100 characters or less. Please try again:")
        return

    data = await state.get_data()
    amount = data.get('amount')
    user_id = message.from_user.id
    telegram_chat_id = message.chat.id

    group_record = await db_queries.get_group(db_conn, telegram_chat_id)
    if not group_record:
        await message.answer("Error: Could not find this group's registration. Please try /start again or ask an admin to do so.")
        await state.clear()
        return
    
    internal_group_id = group_record['id']
    try:
        expense = await db_queries.create_expense(db_conn, user_id, internal_group_id, amount, description)
        await message.answer(f"Expense added: '{description}' for {amount:.2f}. Expense ID: {expense['id']}\nNext, you can use /splitexpense to divide it amongst members.")
    except Exception as e:
        print(f"Error creating expense: {e}")
        await message.answer("Sorry, there was an error adding your expense. Please try again.")
    await state.clear()

# --- Split Expense Command Handlers ---
@router.message(Command("splitexpense"))
async def command_split_expense(message: Message, state: FSMContext): 
    db_conn: Any = None 
    user_telegram_id = message.from_user.id
    telegram_chat_id = message.chat.id

    if message.chat.type == ChatType.PRIVATE:
        await message.answer("This command can only be used in a group chat.")
        return

    group_record = await db_queries.get_group(db_conn, telegram_chat_id) 
    if not group_record: 
        await message.answer("This group is not registered. Please use /start first.")
        return
    internal_group_id = group_record['id']
    
    # Check group status
    if group_record.get('status') == 'finished': 
        await message.answer(f"Group '{group_record['name']}' is finished. No expenses can be split unless an admin uses /restart.")
        return

    pending_expenses = await db_queries.get_user_pending_expenses(db_conn, user_telegram_id, internal_group_id)
    if not pending_expenses:
        await message.answer("You don't have any expenses pending a split in this group. Use /addexpense first.")
        return

    expense_to_split = pending_expenses[0]
    expense_id = expense_to_split['id']
    expense_amount = float(expense_to_split['amount'])
    expense_description = expense_to_split['description']
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Split '{expense_description[:20]}' ({expense_amount:.2f}) equally?", callback_data=f"split_confirm_equal_{expense_id}")]
    ])
    await message.answer(f"Found expense: '{expense_description}' for {expense_amount:.2f}. Do you want to split it equally among all group members?", reply_markup=keyboard)

@router.callback_query(lambda c: c.data and c.data.startswith("split_confirm_equal_"))
async def process_split_confirm_equal(callback_query: CallbackQuery, state: FSMContext): 
    db_conn: Any = None 
    expense_id = int(callback_query.data.split("_")[-1])
    user_telegram_id = callback_query.from_user.id             
    telegram_chat_id = callback_query.message.chat.id
    group_record = await db_queries.get_group(db_conn, telegram_chat_id)
    if not group_record:
        await callback_query.answer("Error: Group not found.", show_alert=True)
        try: await callback_query.message.edit_text("Error processing split: Group information is missing.")
        except Exception as e: print(f"Error editing message: {e}") 
        return
    internal_group_id = group_record['id']

    all_pending_for_user = await db_queries.get_user_pending_expenses(db_conn, user_telegram_id, internal_group_id)
    expense_to_split = next((exp for exp in all_pending_for_user if exp['id'] == expense_id), None)
    if not expense_to_split:
        await callback_query.answer("Error: Could not find the expense to split.", show_alert=True)
        try: await callback_query.message.edit_text("Error processing split. Expense not found.")
        except Exception as e: print(f"Error editing message: {e}")
        return
    
    expense_amount = float(expense_to_split['amount'])
    payer_telegram_id = expense_to_split['user_id']
    group_member_ids = await db_queries.get_group_members_telegram_ids(db_conn, internal_group_id)
    
    if not group_member_ids:
        await callback_query.answer("No members found for this group to split with.", show_alert=True)
        try: await callback_query.message.edit_text("Could not split: No members found in the group.")
        except Exception as e: print(f"Error editing message: {e}")
        return

    num_members = len(group_member_ids)
    if num_members == 0:
        await callback_query.answer("Cannot split with zero members.", show_alert=True)
        try: await callback_query.message.edit_text("Error: No members to split with.")
        except Exception as e: print(f"Error editing message: {e}")
        return

    amount_per_person = round(expense_amount / num_members, 2)
    participants_to_add = []
    for member_id in group_member_ids:
        if member_id != payer_telegram_id: # Payer does not owe themselves in this context
            participants_to_add.append({"user_telegram_id": member_id, "amount_owed": amount_per_person})
    
    if not participants_to_add: # If payer is the only member or all others are the payer
         await db_queries.update_expense_split_type(db_conn, expense_id, 'EQUALLY_SPLIT_SELF')
         try: await callback_query.message.edit_text(f"Expense '{expense_to_split['description']}' of {expense_amount:.2f} is considered covered by you as you are the only participant.")
         except Exception as e: print(f"Error editing message: {e}")
         await callback_query.answer("Expense split (self covered).")
         return

    await db_queries.add_expense_participants(db_conn, expense_id, participants_to_add)
    await db_queries.update_expense_split_type(db_conn, expense_id, 'EQUALLY_SPLIT')
    
    try: await callback_query.message.edit_text(f"Expense '{expense_to_split['description']}' ({expense_amount:.2f}) has been split equally among {num_members} members. Each owes {amount_per_person:.2f} (excluding the payer from this list of debtors).")
    except Exception as e: print(f"Error editing message: {e}")
    await callback_query.answer("Expense split successfully!")

# --- MyDebt Command Handler ---
@router.message(Command("mydebt"))
async def command_my_debt(message: Message, state: FSMContext): 
    db_conn: Any = None 
    user_telegram_id = message.from_user.id
    user_full_name = await db_queries.get_user_display_name(db_conn, user_telegram_id) 
    internal_group_id = None 
    group_title_str = ""
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        group_record = await db_queries.get_group(db_conn, message.chat.id)
        if group_record:
            internal_group_id = group_record['id']
            group_title_str = f" for group '{group_record['name']}'"
        else: # In group but group not registered with bot yet
            await message.answer("This group isn't registered with me yet. Please use /start first to enable group-specific debt tracking.")
            return # Or show global summary, but spec implies group context for group commands

    credits_list = await db_queries.get_user_total_owed_to_them(db_conn, user_telegram_id, internal_group_id)
    debits_list = await db_queries.get_user_total_they_owe(db_conn, user_telegram_id, internal_group_id)
    transactions_summary = await db_queries.get_confirmed_transactions_summary(db_conn, user_telegram_id, internal_group_id)

    total_owed_to_user = sum(c['amount'] for c in credits_list)
    total_user_owes = sum(d['amount'] for d in debits_list)
    total_sent_by_user = transactions_summary.get('sent', 0.0)
    total_received_by_user = transactions_summary.get('received', 0.0)
    net_expense_balance = total_owed_to_user - total_user_owes
    net_overall_balance = net_expense_balance + (total_received_by_user - total_sent_by_user)

    response_lines = [f"Hello {user_full_name}, here's your debt summary{group_title_str}:\n"]
    if not credits_list and not debits_list and abs(net_overall_balance) < 0.009:
        response_lines.append("Looks like you have no outstanding debts or credits. All settled up!")
    else:
        if credits_list:
            response_lines.append("--- You are Owed (from expenses) ---")
            for i, credit in enumerate(credits_list[:5]): 
                owed_by_name = await db_queries.get_user_display_name(db_conn, credit['owed_by_user_telegram_id'])
                group_info = f" (Group ID: {credit['group_id']})" if not internal_group_id and 'group_id' in credit else "" 
                response_lines.append(f"{i+1}. {credit['amount']:.2f} from {owed_by_name} for '{credit['expense_description']}'{group_info}")
        if debits_list:
            response_lines.append("\n--- You Owe (from expenses) ---")
            for i, debit in enumerate(debits_list[:5]): 
                owed_to_name = await db_queries.get_user_display_name(db_conn, debit['owed_to_user_telegram_id'])
                group_info = f" (Group ID: {debit['group_id']})" if not internal_group_id and 'group_id' in debit else ""
                response_lines.append(f"{i+1}. {debit['amount']:.2f} to {owed_to_name} for '{debit['expense_description']}'{group_info}")
        response_lines.append("\n--- Transactions Summary ---")
        response_lines.append(f"Total money you've sent directly: {total_sent_by_user:.2f}")
        response_lines.append(f"Total money you've received directly: {total_received_by_user:.2f}")
        response_lines.append("\n--- Net Balance ---")
        response_lines.append(f"Based on expenses only: You are owed {net_expense_balance:.2f}" if net_expense_balance > 0.009 else f"Based on expenses only: You owe {abs(net_expense_balance):.2f}" if net_expense_balance < -0.009 else "Based on expenses only: Settled (0.00)")
        if net_overall_balance > 0.009: response_lines.append(f"Overall, considering direct transactions, you are owed: {net_overall_balance:.2f}")
        elif net_overall_balance < -0.009: response_lines.append(f"Overall, considering direct transactions, you owe: {abs(net_overall_balance):.2f}")
        else: response_lines.append("Overall, considering direct transactions, your balance is settled (0.00).")
    await message.answer("\n".join(response_lines))

# --- Send Money Command Handlers ---
@router.message(Command("send"))
async def command_send_start(message: Message, state: FSMContext):
    db_conn: Any = None 
    fsm_data = {}
    if message.chat.type != ChatType.PRIVATE:
        group_record = await db_queries.get_group(db_conn, message.chat.id)
        if not group_record:
            await message.answer("This group is not registered. Please use /start first if you want this transaction associated with the group.")
            # Decide if we allow non-group sends or stop. For now, let's allow but internal_group_id will be None.
        else:
            fsm_data['internal_group_id'] = group_record['id']
            # Check group status
            if group_record.get('status') == 'finished':
                await message.answer(f"Group '{group_record['name']}' is finished. Transactions cannot be recorded for this group unless an admin uses /restart.")
                return # Stop if group is finished

    await state.update_data(**fsm_data)
    await state.set_state(SendMoneyStates.awaiting_recipient_select)
    await message.answer("Who do you want to send money to? Please provide their Telegram @username (e.g., @example_user):")

@router.message(SendMoneyStates.awaiting_recipient_select)
async def process_send_recipient(message: Message, state: FSMContext):
    db_conn: Any = None 
    recipient_username = message.text.strip()
    if recipient_username.startswith('@'): recipient_username = recipient_username[1:] 

    recipient_user = await db_queries.get_user_by_nickname(db_conn, recipient_username)
    if not recipient_user:
        await message.answer(f"Sorry, I couldn't find a user with the username @{recipient_username} in my records. Please ask them to /start with me first.")
        return
    if recipient_user['telegram_id'] == message.from_user.id:
        await message.answer("You can't send money to yourself! Please enter a different recipient @username.")
        return

    await state.update_data(recipient_telegram_id=recipient_user['telegram_id'], recipient_name=recipient_user['full_name'])
    await state.set_state(SendMoneyStates.awaiting_amount)
    await message.answer(f"Okay, sending to {recipient_user['full_name']}. How much do you want to send?")

@router.message(SendMoneyStates.awaiting_amount)
async def process_send_amount(message: Message, state: FSMContext):
    db_conn: Any = None 
    try:
        amount = float(message.text)
        if amount <= 0:
            await message.answer("The amount must be a positive number. Please try again:")
            return
    except ValueError:
        await message.answer("That doesn't look like a valid amount. Please enter a number (e.g., 10.50):")
        return

    fsm_data = await state.get_data()
    sender_telegram_id = message.from_user.id
    recipient_telegram_id = fsm_data['recipient_telegram_id']
    recipient_name = fsm_data['recipient_name']
    internal_group_id = fsm_data.get('internal_group_id') # Will be None if sent from PM or unregistered group

    transaction = await db_queries.create_transaction(db_conn, sender_telegram_id, recipient_telegram_id, amount, internal_group_id, status='pending')
    if not transaction:
        await message.answer("Sorry, something went wrong while trying to record the transaction. Please try again.")
        await state.clear()
        return

    transaction_id = transaction['id']
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Accept", callback_data=f"send_accept_{transaction_id}"),
         InlineKeyboardButton(text="Reject", callback_data=f"send_reject_{transaction_id}")]])
    sender_name = await db_queries.get_user_display_name(db_conn, sender_telegram_id)
    try:
        await message.bot.send_message(chat_id=recipient_telegram_id, text=f"{sender_name} wants to send you {amount:.2f}. Do you accept?", reply_markup=keyboard)
        await message.answer(f"Request to send {amount:.2f} to {recipient_name} has been sent. They need to accept it.")
    except Exception as e:
        print(f"Error sending DM to recipient {recipient_telegram_id}: {e}")
        await message.answer(f"Request to send {amount:.2f} to {recipient_name} has been recorded (ID: {transaction_id}). I couldn't notify them directly; please ask them to check or use a different method to confirm with them if needed.")
    await state.clear()

@router.callback_query(lambda c: c.data and c.data.startswith("send_accept_"))
async def process_send_accept(callback_query: CallbackQuery, state: FSMContext):
    db_conn: Any = None 
    transaction_id = int(callback_query.data.split("_")[-1])
    transaction = await db_queries.get_transaction_by_id(db_conn, transaction_id)
    if not transaction or transaction['receiver_id'] != callback_query.from_user.id:
        await callback_query.answer("This is not for you or the transaction is invalid.", show_alert=True)
        return
    if transaction['status'] != 'pending':
        await callback_query.answer(f"This transaction is already '{transaction['status']}'.", show_alert=True)
        try: await callback_query.message.edit_text(f"Transaction already {transaction['status']}.")
        except Exception as e: print(f"Error editing message on send_accept status check: {e}")
        return

    updated_transaction = await db_queries.update_transaction_status(db_conn, transaction_id, "confirmed")
    if not updated_transaction:
         await callback_query.answer("Error confirming transaction.", show_alert=True)
         return
    sender_name = await db_queries.get_user_display_name(db_conn, updated_transaction['sender_id'])
    try: await callback_query.message.edit_text(f"You have accepted the payment of {updated_transaction['amount']:.2f} from {sender_name}.")
    except Exception as e: print(f"Error editing message on send_accept success: {e}")
    await callback_query.answer("Payment accepted!")
    try: await callback_query.bot.send_message(updated_transaction['sender_id'], f"Your payment of {updated_transaction['amount']:.2f} to {await db_queries.get_user_display_name(db_conn, updated_transaction['receiver_id'])} has been accepted.")
    except Exception as e: print(f"Error notifying sender about acceptance: {e}")

@router.callback_query(lambda c: c.data and c.data.startswith("send_reject_"))
async def process_send_reject(callback_query: CallbackQuery, state: FSMContext):
    db_conn: Any = None 
    transaction_id = int(callback_query.data.split("_")[-1])
    transaction = await db_queries.get_transaction_by_id(db_conn, transaction_id)
    if not transaction or transaction['receiver_id'] != callback_query.from_user.id:
        await callback_query.answer("This is not for you or the transaction is invalid.", show_alert=True)
        return
    if transaction['status'] != 'pending':
        await callback_query.answer(f"This transaction is already '{transaction['status']}'.", show_alert=True)
        try: await callback_query.message.edit_text(f"Transaction already {transaction['status']}.")
        except Exception as e: print(f"Error editing message on send_reject status check: {e}")
        return

    updated_transaction = await db_queries.update_transaction_status(db_conn, transaction_id, "rejected")
    if not updated_transaction:
         await callback_query.answer("Error rejecting transaction.", show_alert=True)
         return
    sender_name = await db_queries.get_user_display_name(db_conn, updated_transaction['sender_id'])
    try: await callback_query.message.edit_text(f"You have rejected the payment of {updated_transaction['amount']:.2f} from {sender_name}.")
    except Exception as e: print(f"Error editing message on send_reject success: {e}")
    await callback_query.answer("Payment rejected.")
    try: await callback_query.bot.send_message(updated_transaction['sender_id'], f"Your payment of {updated_transaction['amount']:.2f} to {await db_queries.get_user_display_name(db_conn, updated_transaction['receiver_id'])} has been rejected.")
    except Exception as e: print(f"Error notifying sender about rejection: {e}")

# --- Admin Command Handlers ---
@router.message(Command("admin"))
async def command_admin_menu(message: Message, state: FSMContext): 
    db_conn: Any = None 
    user_telegram_id = message.from_user.id
    if message.chat.type == ChatType.PRIVATE:
        await message.answer("The /admin command can only be used in a group chat.")
        return

    telegram_chat_id = message.chat.id
    group_record = await db_queries.get_group(db_conn, telegram_chat_id)
    if not group_record:
        await message.answer("This group is not registered with me. Please use /start first.")
        return
    internal_group_id = group_record['id'] 
    is_admin = await db_queries.is_user_group_admin(db_conn, user_telegram_id, internal_group_id)
    if not is_admin:
        await message.answer("You are not authorized to use admin commands for this group.")
        return

    admin_menu_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Set Group Rules", callback_data=f"admin_set_rules_{internal_group_id}")],
        [InlineKeyboardButton(text="Set Reminder Timer", callback_data=f"admin_set_timer_{internal_group_id}")],
        [InlineKeyboardButton(text="Reset Group Data", callback_data=f"admin_reset_data_{internal_group_id}")]])
    await message.answer(f"Admin Menu for group '{group_record['name']}':", reply_markup=admin_menu_keyboard)

@router.callback_query(lambda c: c.data and c.data.startswith("admin_set_rules_"))
async def process_admin_set_rules_prompt(callback_query: CallbackQuery, state: FSMContext):
    internal_group_id = int(callback_query.data.split("_")[-1])
    await state.update_data(admin_action_group_id=internal_group_id) 
    await state.set_state(AdminStates.awaiting_rules_text)
    await callback_query.message.answer("Please send the text for the group rules (max 500 characters). Send /cancel to abort.")
    await callback_query.answer() 

@router.message(AdminStates.awaiting_rules_text)
async def process_admin_new_rules_text(message: Message, state: FSMContext):
    db_conn: Any = None 
    rules_text = message.text
    if not rules_text or len(rules_text) > 500:
        await message.answer("Rules text cannot be empty and must be 500 characters or less. Please try again, or send /cancel to abort.")
        return

    fsm_data = await state.get_data()
    internal_group_id = fsm_data.get('admin_action_group_id')
    if internal_group_id is None: 
        await message.answer("Error: Could not determine the group. Please try from /admin again.")
        await state.clear()
        return

    updated_group = await db_queries.update_group_rules(db_conn, internal_group_id, rules_text)
    if updated_group: await message.answer(f"Group rules for '{updated_group['name']}' have been updated.")
    else: await message.answer("Sorry, there was an error updating group rules.")
    await state.clear()

@router.callback_query(lambda c: c.data and c.data.startswith("admin_set_timer_"))
async def process_admin_set_timer_menu(callback_query: CallbackQuery, state: FSMContext): 
    internal_group_id = int(callback_query.data.split("_")[-1])
    await state.update_data(admin_action_group_id=internal_group_id) 
    timer_options_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="12h", callback_data=f"admin_timer_val_12h_{internal_group_id}"), InlineKeyboardButton(text="24h", callback_data=f"admin_timer_val_24h_{internal_group_id}")],
        [InlineKeyboardButton(text="48h", callback_data=f"admin_timer_val_48h_{internal_group_id}"), InlineKeyboardButton(text="72h", callback_data=f"admin_timer_val_72h_{internal_group_id}")],
        [InlineKeyboardButton(text="Disable Timer", callback_data=f"admin_timer_val_0h_{internal_group_id}")]])
    try: await callback_query.message.edit_text(f"Select reminder interval for group (ID: {internal_group_id}):", reply_markup=timer_options_keyboard)
    except Exception as e: 
        print(f"Error editing message for timer options: {e}")
        await callback_query.message.answer(f"Select reminder interval for group (ID: {internal_group_id}):", reply_markup=timer_options_keyboard)
    await callback_query.answer()

@router.callback_query(lambda c: c.data and c.data.startswith("admin_timer_val_"))
async def process_admin_timer_set_value(callback_query: CallbackQuery, state: FSMContext): 
    db_conn: Any = None 
    parts = callback_query.data.split("_")
    hours_str = parts[-2] 
    internal_group_id = int(parts[-1])
    try:
        interval_hours = int(hours_str.replace('h', ''))
        if not (0 <= interval_hours <= 72): raise ValueError("Invalid hour range")
    except ValueError:
        await callback_query.answer("Invalid timer value selected.", show_alert=True)
        try: await callback_query.message.edit_text("Error: Invalid timer. Try from /admin.")
        except Exception as e: print(f"Error editing msg on invalid timer: {e}")
        return

    updated_group = await db_queries.update_group_timer(db_conn, internal_group_id, interval_hours)
    try:
        if updated_group:
            group_name = updated_group.get('name', f'Group {internal_group_id}')
            msg = f"Timer for '{group_name}' disabled." if interval_hours == 0 else f"Timer for '{group_name}' set to {interval_hours}h."
            await callback_query.message.edit_text(msg)
        else: await callback_query.message.edit_text("Error updating timer.")
    except Exception as e:
        print(f"Error editing msg after timer update: {e}")
        await callback_query.message.answer("Timer update processed. (Failed to edit previous message).")
    await callback_query.answer() 
    await state.clear() 

@router.callback_query(lambda c: c.data and c.data.startswith("admin_reset_data_"))
async def process_admin_reset_data_prompt(callback_query: CallbackQuery, state: FSMContext):
    db_conn: Any = None 
    internal_group_id = int(callback_query.data.split("_")[-1])
    user_telegram_id = callback_query.from_user.id
    is_admin = await db_queries.is_user_group_admin(db_conn, user_telegram_id, internal_group_id)
    if not is_admin:
        await callback_query.answer("Authorization failed.", show_alert=True)
        try: await callback_query.message.edit_text("Error: You are no longer admin.")
        except Exception as e: print(f"Error editing msg (reset auth fail): {e}")
        return

    group_record = await db_queries.get_group(db_conn, callback_query.message.chat.id) 
    group_name = group_record['name'] if group_record else f"Group ID {internal_group_id}"
    confirm_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"YES, Reset '{group_name}'", callback_data=f"admin_confirm_reset_{internal_group_id}")],
        [InlineKeyboardButton(text="NO, Cancel", callback_data=f"admin_cancel_reset_{internal_group_id}")]])
    try: await callback_query.message.edit_text(f"⚠️ **WARNING!** Are you sure you want to reset all financial data (expenses, splits, group-specific transactions) for group '{group_name}'? This action cannot be undone.", reply_markup=confirm_keyboard, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        print(f"Error editing msg for reset prompt: {e}")
        await callback_query.message.answer(f"⚠️ **WARNING!** Are you sure you want to reset all financial data for group '{group_name}'? This action cannot be undone. (Previous message edit failed)", reply_markup=confirm_keyboard, parse_mode=ParseMode.MARKDOWN)
    await callback_query.answer("Confirmation required.")

@router.callback_query(lambda c: c.data and c.data.startswith("admin_confirm_reset_"))
async def process_admin_confirm_reset(callback_query: CallbackQuery, state: FSMContext):
    db_conn: Any = None 
    internal_group_id = int(callback_query.data.split("_")[-1])
    user_telegram_id = callback_query.from_user.id
    is_admin = await db_queries.is_user_group_admin(db_conn, user_telegram_id, internal_group_id)
    if not is_admin:
        await callback_query.answer("Authorization failed.", show_alert=True)
        try: await callback_query.message.edit_text("Error: Admin rights lost.")
        except Exception as e: print(f"Error editing msg (reset final auth fail): {e}")
        return

    expenses_deleted = await db_queries.delete_group_expenses(db_conn, internal_group_id)
    transactions_deleted = await db_queries.delete_group_transactions_if_group_specific(db_conn, internal_group_id)
    group_record = await db_queries.get_group(db_conn, callback_query.message.chat.id)
    group_name = group_record['name'] if group_record else f"Group ID {internal_group_id}"

    if expenses_deleted and transactions_deleted:
        response_text = f"All financial data for group '{group_name}' has been reset."
        try: await callback_query.bot.send_message(callback_query.message.chat.id, response_text)
        except Exception as e: print(f"Error sending reset confirmation to group chat: {e}")
        try: await callback_query.message.edit_text(response_text + "\n(Admin message updated.)")
        except Exception as e: 
            print(f"Error editing admin msg after reset: {e}")
            await callback_query.message.answer(response_text + "\n(Previous message edit failed.)")
    else:
        error_response = f"An error occurred while resetting data for group '{group_name}'."
        try: await callback_query.message.edit_text(error_response)
        except Exception as e:
            print(f"Error editing admin msg on reset error: {e}")
            await callback_query.message.answer(error_response + "\n(Previous message edit failed.)")
    await callback_query.answer("Reset processed.")
    await state.clear()

@router.callback_query(lambda c: c.data and c.data.startswith("admin_cancel_reset_"))
async def process_admin_cancel_reset(callback_query: CallbackQuery, state: FSMContext):
    try: await callback_query.message.edit_text("Group data reset has been cancelled. Your data is safe.")
    except Exception as e:
        print(f"Error editing msg on reset cancel: {e}")
        await callback_query.message.answer("Group data reset has been cancelled. (Previous message edit failed.)")
    await callback_query.answer("Reset cancelled.")
    await state.clear()

# --- Finish/Restart Group Commands ---
@router.message(Command("finish"))
async def command_finish_group(message: Message, state: FSMContext):
    db_conn: Any = None 
    user_telegram_id = message.from_user.id

    if message.chat.type == ChatType.PRIVATE:
        await message.answer("This command can only be used in a group chat.")
        return

    telegram_chat_id = message.chat.id
    group_record = await db_queries.get_group(db_conn, telegram_chat_id)
    if not group_record:
        await message.answer("This group is not registered. Please use /start first.")
        return
    
    internal_group_id = group_record['id']
    is_admin = await db_queries.is_user_group_admin(db_conn, user_telegram_id, internal_group_id)
    if not is_admin:
        await message.answer("Only the group admin can use the /finish command.")
        return

    if group_record.get('status') == 'finished':
        await message.answer(f"Group '{group_record['name']}' is already marked as finished.")
        return

    updated_group = await db_queries.update_group_status(db_conn, internal_group_id, 'finished')
    if updated_group:
        await message.answer(f"Group '{updated_group['name']}' has been marked as finished. New expenses cannot be added or split.")
    else:
        await message.answer("There was an error trying to finish the group.")

@router.message(Command("restart"))
async def command_restart_group(message: Message, state: FSMContext):
    db_conn: Any = None 
    user_telegram_id = message.from_user.id

    if message.chat.type == ChatType.PRIVATE:
        await message.answer("This command can only be used in a group chat.")
        return

    telegram_chat_id = message.chat.id
    group_record = await db_queries.get_group(db_conn, telegram_chat_id)
    if not group_record:
        await message.answer("This group is not registered. Please use /start first.")
        return

    internal_group_id = group_record['id']
    is_admin = await db_queries.is_user_group_admin(db_conn, user_telegram_id, internal_group_id)
    if not is_admin:
        await message.answer("Only the group admin can use the /restart command.")
        return

    if group_record.get('status') == 'active':
        await message.answer(f"Group '{group_record['name']}' is already active.")
        return

    updated_group = await db_queries.update_group_status(db_conn, internal_group_id, 'active')
    if updated_group:
        await message.answer(f"Group '{updated_group['name']}' has been restarted. You can now add and split expenses again.")
    else:
        await message.answer("There was an error trying to restart the group.")

# --- Report Command ---
@router.message(Command("report"))
async def command_report(message: Message, state: FSMContext): 
    db_conn: Any = None 
    
    if message.chat.type == ChatType.PRIVATE:
        await message.answer("The /report command is intended for use within a group chat to generate a report for that group.")
        return

    telegram_chat_id = message.chat.id
    group_record = await db_queries.get_group(db_conn, telegram_chat_id)

    if not group_record:
        await message.answer("This group is not registered with me. Please use /start first to enable group functionalities.")
        return
    
    internal_group_id = group_record['id']
    group_name = group_record.get('name', f"Group ID {internal_group_id}")

    # Call mock DB functions
    mock_expenses = await db_queries.get_expenses_for_report(db_conn, internal_group_id)
    mock_transactions = await db_queries.get_transactions_for_report(db_conn, internal_group_id)

    num_expenses = len(mock_expenses)
    num_transactions = len(mock_transactions)

    response_text = (
        f"Report generation for group '{group_name}' initiated (mock)...\n"
        f"- Fetched {num_expenses} expense(s).\n"
        f"- Fetched {num_transactions} transaction(s) associated with the group.\n\n"
        "Actual Excel and PDF file generation, along with emailing to the admin, will be implemented in a future update. "
        "For now, this confirms the data fetching step (mocked)."
    )
    
    await message.answer(response_text)

# Generic cancel handler for any state
@router.message(Command("cancel"), state="*") 
async def cancel_handler(message: Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("No active operation to cancel.")
        return
    print(f"Cancelling state {current_state}")
    await state.clear()
    await message.answer("Operation cancelled.")

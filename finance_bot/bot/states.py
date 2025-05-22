from aiogram.fsm.state import State, StatesGroup

class AddExpenseStates(StatesGroup):
    awaiting_amount = State()
    awaiting_description = State()

class SendMoneyStates(StatesGroup):
    awaiting_recipient_select = State() # Or awaiting_recipient_mention
    awaiting_amount = State()
    awaiting_confirmation = State() # If we add a final confirm step for sender

class AdminStates(StatesGroup):
    awaiting_rules_text = State()
    awaiting_timer_value = State()
    # Add more admin-specific states as needed

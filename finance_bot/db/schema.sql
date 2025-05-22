-- Table for storing user information
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    phone VARCHAR(255), -- To be encrypted, actual storage might be TEXT or BYTEA depending on encryption output
    full_name VARCHAR(255),
    nickname VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Table for storing group information
CREATE TABLE groups (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    rules TEXT,
    timer_interval INTEGER, -- Assuming this is in hours as per 3.1.3 (12-72 hours)
    status VARCHAR(50) DEFAULT 'active', -- e.g., active, finished
    admin_id BIGINT NOT NULL, -- REFERENCES users(telegram_id) -- Consider if admin_id should reference users.id or users.telegram_id
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    -- If admin_id references users.telegram_id, ensure users.telegram_id is indexed.
    -- If it references users.id, then:
    -- CONSTRAINT fk_admin FOREIGN KEY (admin_id) REFERENCES users(id)
);

-- Table for storing expense records
CREATE TABLE expenses (
    id SERIAL PRIMARY KEY,
    amount DECIMAL(10, 2) NOT NULL,
    description VARCHAR(100) NOT NULL,
    user_id BIGINT NOT NULL, -- REFERENCES users(telegram_id)
    group_id INTEGER NOT NULL,
    split_type VARCHAR(50) NOT NULL, -- e.g., 'equally', 'proportionally' (though spec only mentions 'equally' and 'selectively')
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES users(telegram_id), -- Assuming user_id is telegram_id for direct mapping
    CONSTRAINT fk_group FOREIGN KEY (group_id) REFERENCES groups(id)
);

-- Table for storing transaction records between users
CREATE TABLE transactions (
    id SERIAL PRIMARY KEY,
    sender_id BIGINT NOT NULL, -- REFERENCES users(telegram_id)
    receiver_id BIGINT NOT NULL, -- REFERENCES users(telegram_id)
    amount DECIMAL(10, 2) NOT NULL,
    status VARCHAR(50) NOT NULL, -- e.g., 'pending', 'confirmed', 'rejected'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    confirmed_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT fk_sender FOREIGN KEY (sender_id) REFERENCES users(telegram_id),
    CONSTRAINT fk_receiver FOREIGN KEY (receiver_id) REFERENCES users(telegram_id)
);

-- Add indexes for frequently queried columns, especially foreign keys and telegram_id
CREATE INDEX idx_users_telegram_id ON users(telegram_id);
CREATE INDEX idx_groups_admin_id ON groups(admin_id);
CREATE INDEX idx_expenses_user_id ON expenses(user_id);
CREATE INDEX idx_expenses_group_id ON expenses(group_id);
CREATE INDEX idx_transactions_sender_id ON transactions(sender_id);
CREATE INDEX idx_transactions_receiver_id ON transactions(receiver_id);

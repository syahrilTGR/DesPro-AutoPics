-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Tabel users
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    balance NUMERIC DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Tabel rfid_cards
CREATE TABLE rfid_cards (
    uid VARCHAR(50) PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    card_name VARCHAR(100),
    vehicle_type VARCHAR(20) CHECK (vehicle_type IN ('Mobil', 'Motor')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Tabel parking_history
CREATE TABLE parking_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rfid_uid VARCHAR(50) REFERENCES rfid_cards(uid),
    time_in TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    time_out TIMESTAMP WITH TIME ZONE,
    duration_minutes NUMERIC,
    total_fee NUMERIC,
    status VARCHAR(20) DEFAULT 'PARKED' CHECK (status IN ('PARKED', 'COMPLETED'))
);

-- 4. Tabel topup_transactions
CREATE TABLE topup_transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    amount NUMERIC NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 5. Tabel parking_slots
CREATE TABLE parking_slots (
    slot_id VARCHAR(20) PRIMARY KEY,
    status VARCHAR(20) DEFAULT 'EMPTY' CHECK (status IN ('EMPTY', 'FULL')),
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

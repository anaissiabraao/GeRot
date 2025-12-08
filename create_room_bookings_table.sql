-- Tabela para agendamentos de salas de reunião
CREATE TABLE IF NOT EXISTS room_bookings (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users_new(id) ON DELETE CASCADE,
    room VARCHAR(50) NOT NULL,
    title VARCHAR(200) NOT NULL,
    date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    participants INTEGER NOT NULL,
    subject TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    CONSTRAINT valid_time_range CHECK (end_time > start_time),
    CONSTRAINT valid_participants CHECK (participants > 0)
);

-- Índices para melhor performance
CREATE INDEX idx_room_bookings_date ON room_bookings(date);
CREATE INDEX idx_room_bookings_room ON room_bookings(room);
CREATE INDEX idx_room_bookings_user ON room_bookings(user_id);
CREATE INDEX idx_room_bookings_active ON room_bookings(is_active);

-- Trigger para atualizar updated_at automaticamente
CREATE OR REPLACE FUNCTION update_room_bookings_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_room_bookings_timestamp
BEFORE UPDATE ON room_bookings
FOR EACH ROW
EXECUTE FUNCTION update_room_bookings_timestamp();

-- Comentários na tabela
COMMENT ON TABLE room_bookings IS 'Agendamentos de salas de reunião do CD';
COMMENT ON COLUMN room_bookings.room IS 'Identificador da sala (sala1, sala2)';
COMMENT ON COLUMN room_bookings.title IS 'Título/nome da reunião';
COMMENT ON COLUMN room_bookings.subject IS 'Assunto/descrição detalhada da reunião';
COMMENT ON COLUMN room_bookings.participants IS 'Número de participantes esperados';

CREATE TABLE IF NOT EXISTS device_tb (
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    shift VARCHAR(1),
    device_id VARCHAR(20),
    broker VARCHAR(1),
    modbus VARCHAR(1),
    mac_id VARCHAR(20),
    duration DOUBLE PRECISION DEFAULT 0
);

CREATE TABLE IF NOT EXISTS status_tb (
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    shift VARCHAR(1),
    device_id VARCHAR(20),
    status VARCHAR(20),
    duration DOUBLE PRECISION DEFAULT 0
);

CREATE TABLE IF NOT EXISTS alarm_tb (
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    shift VARCHAR(1),
    device_id VARCHAR(20),
    status VARCHAR(20),
    duration DOUBLE PRECISION DEFAULT 0
);


CREATE OR REPLACE FUNCTION update_duration_device_tb()
RETURNS TRIGGER AS $$
DECLARE
    last_time TIMESTAMP;
BEGIN
    SELECT created_at INTO last_time 
    FROM device_tb 
    WHERE device_id = NEW.device_id AND created_at < NEW.created_at
    ORDER BY created_at DESC 
    LIMIT 1;

    IF last_time IS NOT NULL THEN
        NEW.duration := EXTRACT(EPOCH FROM (NEW.created_at - last_time));
    ELSE
        NEW.duration := 0;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_calc_duration_device_tb
BEFORE INSERT ON device_tb
FOR EACH ROW EXECUTE FUNCTION update_duration_device_tb();


CREATE OR REPLACE FUNCTION update_duration_status_tb()
RETURNS TRIGGER AS $$
DECLARE
    last_time TIMESTAMP;
BEGIN
    SELECT created_at INTO last_time 
    FROM status_tb 
    WHERE device_id = NEW.device_id AND created_at < NEW.created_at
    ORDER BY created_at DESC 
    LIMIT 1;

    IF last_time IS NOT NULL THEN
        NEW.duration := EXTRACT(EPOCH FROM (NEW.created_at - last_time));
    ELSE
        NEW.duration := 0;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_calc_duration_status_tb
BEFORE INSERT ON status_tb
FOR EACH ROW EXECUTE FUNCTION update_duration_status_tb();



CREATE OR REPLACE FUNCTION update_duration_alarm_tb()
RETURNS TRIGGER AS $$
DECLARE
    last_time TIMESTAMP;
BEGIN
    SELECT created_at INTO last_time 
    FROM alarm_tb 
    WHERE device_id = NEW.device_id AND created_at < NEW.created_at
    ORDER BY created_at DESC 
    LIMIT 1;

    IF last_time IS NOT NULL THEN
        NEW.duration := EXTRACT(EPOCH FROM (NEW.created_at - last_time));
    ELSE
        NEW.duration := 0;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_calc_duration_alarm_tb
BEFORE INSERT ON alarm_tb
FOR EACH ROW EXECUTE FUNCTION update_duration_alarm_tb();
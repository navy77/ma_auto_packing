CREATE TABLE status_raw_tb(
    created_at DateTime('Asia/Bangkok') DEFAULT now(),
    shift String,
    device_id String,
    status String
) ENGINE = MergeTree()
ORDER BY created_at ;

CREATE TABLE alarm_raw_tb(
    created_at DateTime('Asia/Bangkok') DEFAULT now(),
    shift String,
    device_id String,
    status String
) ENGINE = MergeTree()
ORDER BY created_at ;


CREATE TABLE status_tb(
    created_at DateTime('Asia/Bangkok') DEFAULT now(),
    ts DateTime,
    shift String,
    device_id String,
    status String
) ENGINE = MergeTree()
ORDER BY created_at ;

CREATE TABLE alarm_tb(
    created_at DateTime('Asia/Bangkok') DEFAULT now(),
    ts DateTime,
    shift String,
    device_id String,
    status String
) ENGINE = MergeTree()
ORDER BY created_at ;

CREATE TABLE device_tb(
    created_at DateTime('Asia/Bangkok') DEFAULT now(),
    status String,
    shift String,
    device_id String,
    broker String,
    modbus String,
    mac_id String
) ENGINE = MergeTree()
ORDER BY created_at ;
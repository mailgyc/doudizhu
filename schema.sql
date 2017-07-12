--   mysql --user=user --password=pwd --database=ddz < schema.sql

CREATE DATABASE IF NOT EXISTS ddz DEFAULT CHARSET utf8 COLLATE utf8_general_ci;

CREATE TABLE IF NOT EXISTS account (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(20) NOT NULL UNIQUE,
    username VARCHAR(10) NOT NULL,
    password VARCHAR(100) NOT NULL,
    coin INT default 4000,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS record (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    a_id INT NOT NULL,
    b_id INT NOT NULL,
    c_id INT NOT NULL,
    round VARCHAR(100) NOT NULL,
    created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


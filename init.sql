CREATE TABLE location (
    username VARCHAR(64),
    contact VARCHAR(128),
    expires INT,
    PRIMARY KEY (username)
);

CREATE TABLE redial_list(
    user VARCHAR(64),
    dest VARCHAR(64)
);

CREATE TABLE activations(
    user VARCHAR(64),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

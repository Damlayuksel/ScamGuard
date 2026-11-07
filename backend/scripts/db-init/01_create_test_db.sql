-- Runs once, when the Postgres volume is first initialised.
-- Tests use this separate database so they never touch development data.
CREATE DATABASE scamshield_test;

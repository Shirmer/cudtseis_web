sudo -u postgres psql

CREATE DATABASE quakes;
\c quakes
CREATE EXTENSION postgis;
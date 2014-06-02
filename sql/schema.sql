BEGIN TRANSACTION;
CREATE TABLE IF NOT EXISTS customer (id INTEGER PRIMARY KEY, name TEXT, reference TEXT, postcode TEXT, city TEXT, address1 TEXT, address2 TEXT);
INSERT OR IGNORE INTO customer VALUES(1,'Standardkund','-',NULL,NULL,NULL,NULL);
CREATE TABLE IF NOT EXISTS order_products (id INTEGER PRIMARY KEY, price NUMERIC, orderId INTEGER, productId INTEGER, comment TEXT, count NUMERIC);
CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY, description TEXT, customerId INTEGER, status INTEGER, invoiceFile TEXT, created datetime);
CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY,description TEXT, physical_product INTEGER, distributor_price money, price money, stock NUMERIC,  name TEXT, distributor NUMERIC, UPC TEXT);
CREATE TABLE IF NOT EXISTS stock (productId NUMERIC, stock NUMERIC);
CREATE TABLE IF NOT EXISTS distributor (id INTEGER PRIMARY KEY, name TEXT);
INSERT OR IGNORE INTO distributor VALUES(1,'Skeppshult');
INSERT OR IGNORE INTO distributor VALUES(2,'Shimano');

COMMIT;

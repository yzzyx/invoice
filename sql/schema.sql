BEGIN TRANSACTION;
CREATE TABLE customer (id INTEGER PRIMARY KEY, name TEXT, reference TEXT, postcode TEXT, city TEXT, address1 TEXT, address2 TEXT);
INSERT INTO customer VALUES(1,'Standardkund','-',NULL,NULL,NULL,NULL);
CREATE TABLE order_products (price NUMERIC, orderId INTEGER, productId INTEGER, comment TEXT, count NUMERIC);
CREATE TABLE orders (id INTEGER PRIMARY KEY, description TEXT, customerId INTEGER, status INTEGER, invoiceFile TEXT, created datetime);
INSERT INTO orders VALUES(NULL,1,1,NULL,NULL,NULL);
CREATE TABLE products (id INTEGER PRIMARY KEY,description TEXT, physical_product NUMERIC, distributor_price money, price money, stock NUMERIC,  name TEXT, distributor NUMERIC, UPC TEXT);
CREATE TABLE stock (productId NUMERIC, stock NUMERIC);
COMMIT;

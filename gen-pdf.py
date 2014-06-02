#!/usr/bin/python
# -*- coding: utf-8 -*-
import fileinput
import sqlite3
import subprocess
import sys
from datetime import datetime

db_conn = sqlite3.connect('invoice.db')
db_cursor = db_conn.cursor()

class product():
    """Product representation"""

    def __init__(self, id = None):
        """ """

        self.id = -1
        self.price = 0.0
        self.stock = 0
        self.name = ""
        self.description = ""
        self.distributor = 0
        self.distributor_price = 0.0
        self.UPC = ""
        self.physical_product = 1

        if id is not None:
            print type(id)
            try:
                db_cursor.execute("""
                    SELECT id, price, stock, name, description,
                    distributor, distributor_price, UPC, physical_product
                    FROM products WHERE id = ?""", (id,))
                prod = db_cursor.fetchone()
                self.id = prod[0]
                self.price = prod[1]
                self.stock = prod[2]
                self.name = prod[3]
                self.description = prod[4]
                self.distributor = prod[5]
                self.distributor_price = prod[6]
                self.UPC = prod[7]
                self.physical_product = prod[8]
            except sqlite3.Error:
                print "Cannot find product with id %d" %id

    def save():
        try:
            if self.id != -1:
                db_cursor.execute("""
                    UPDATE products SET
                        price = ?,
                        stock = ?,
                        name = ?,
                        description = ?,
                        distributor = ?,
                        distributor_price = ?,
                        UPC = ?,
                        physical_product = ?
                    WHERE id = ?""",
                    (self.price, self.stock, self.name, self.description,
                    self.distributor, self.distributor_price,
                    self.UPC, self.physical_product, self.id))
            else:
                db_cursor.execute("""
                    INSERT INTO products
                        (price, stock, name, description,
                        distributor, distributor_price,
                        UPC, physical_product)
                        VALUES ( ?, ?, ?, ?, ?, ?, ?, ?) """,
                    (self.price, self.stock, self.name, self.description,
                    self.distributor, self.distributor_price,
                    self.UPC, self.physical_product))
                self.id = db_cursor.lastrowid
                print "Created product with id %d" % self.id
        except:
            print "Could not save product!"

    def delete():
        if self.id == -1:
            return
        try:
            db_cursor.execute("DELETE FROM products WHERE id = ?",
                    (self.id,))
        except:
            print "Could not delete product!"

#p = product(1)
#print p.__dict__
#quit()


date = datetime.now()
dateStr = date.strftime('%Y-%m-%d')


if len(sys.argv) < 2:
    print "Usage: %s <orderid>" % sys.argv[0]
    quit()

orderId = int(sys.argv[1])

db_cursor.execute("SELECT status, invoiceFile, created FROM orders WHERE id = %d" %
        orderId)
orderInfo = db_cursor.fetchone();

"""
orders.status
  0 - not processed
  1 - sent
  2 - paid
if orderInfo[0] == 0:
"""


db_cursor.execute("""
SELECT name, reference, postcode, city, address1, address2
FROM orders o
LEFT JOIN customer c ON c.id = o.customerId
WHERE o.id = %d""" % orderId)
customerInfo = db_cursor.fetchone()

db_cursor.execute("""
SELECT p.name, op.price, op.count, op.comment FROM order_products op
LEFT JOIN products p ON p.id = op.productId
WHERE orderId = %d""" % orderId)
productsStr = u""
for p in db_cursor.fetchall():
    price = p[1] if p[1] is not None else 0
    count = p[2] if p[2] is not None else 0

    if len(p[3]):
        productsStr = productsStr + u"\\product{%s - %s}{%.2f}{%.2f}\n" % (p[0], p[3], price, count)
    else:
        productsStr = productsStr + u"\\product{%s}{%.2f}{%.2f}\n" % (p[0], price, count)

p = subprocess.Popen(['pdflatex', '-jobname', 'invoice-%s-%d' % (dateStr,orderId),
    '-output-directory','output'], stdin = subprocess.PIPE, stdout = None)

with open("invoice.tex","r") as inputFile:
    for line in inputFile:
        line = line.decode("utf-8")
        fieldNames = [ "customerName", "customerReference", "customerPostcode",
        "customerCity", "customerAddress1", "customerAddress2" ]
        for k,field in enumerate(fieldNames):
            if customerInfo[k] is not None and len(customerInfo[k]):
                line = line.replace(u"\\replacevar{%s}" % field, customerInfo[k] + u"\\\\")
        line = line.replace(u"\\replacevar{articles}", productsStr)
        line = line.replace(u"\\replacevar{invoiceNumber}", str(orderId))
        line = line.replace(u"\\replacevar{invoiceDate}", dateStr)

        p.stdin.write(line.encode("utf-8"))
#        print line.encode("utf-8"),

print "Waiting for pdflatex to finish..."
p.wait()

#!/usr/bin/env python
# encoding: utf-8
import npyscreen
import sqlite3
import os
import logging
from decimal import Decimal, DecimalException

DB_FILENAME = 'invoice.db'
LOG_FILENAME = '/tmp/iv.log'
logging.basicConfig(filename=LOG_FILENAME,
                    level=logging.DEBUG,
                    )

# Setup our decimal-helper
sqlite3.register_converter("DECIMAL", Decimal)
sqlite3.register_adapter(Decimal, str)

class SQLite3DB():
    """ Wrapper for SQLite3 database and cursor objects,
        which sets up adapters and converters,
        and closes the database
    """
    def __enter__(self):
        self.db = sqlite3.connect(DB_FILENAME, detect_types=sqlite3.PARSE_DECLTYPES)
        self.c = self.db.cursor()
        return self

    def __exit__(self, type, value, traceback):
        self.c.close()
        self.db.close()

    def execute(self, *args, **kwargs):
        return self.c.execute(*args,**kwargs)

    def commit(self, *args, **kwargs):
        return self.db.commit(*args,**kwargs)

class SubRow(sqlite3.Row):
    def __init__(self, *args, **kwargs):
        if len(args):
            super(SubRow, self).__init__(*args,**kwargs)

            for k in self.keys():
                setattr(self,k.lower(),self[k])

    def save(self):
        pass

class Distributor(SubRow):
    pass

class Product(SubRow):
    id = -1
    name = ''
    description = ''
    price = 0.0
    stock = 0
    distributor = 0
    distributor_price = 0
    upc = ''
    physical_product = 1

    def save(self):
        with SQLite3DB() as db:
            if self.id == -1:
                db.execute("""
                    INSERT INTO products (name, price, stock, description,
                        distributor, distributor_price, UPC, physical_product)
                        VALUES (?,?,?,?,?,?,?,?)""",
                        (self.name, self.price, self.stock, self.description,
                            self.distributor, self.distributor_price, self.upc,
                            self.physical_product,))
                self.id = db.c.lastrowid
            else:
                db.execute("""
                    UPDATE products SET
                        name = ?, price = ?, stock = ?, description = ?,
                        distributor = ?, distributor_price = ?,
                        UPC = ?, physical_product = ?
                        WHERE id = ?""",
                        (self.name, self.price, self.stock, self.description,
                            self.distributor, self.distributor_price, self.upc,
                            self.physical_product,self.id,))
            db.commit()
        return self.id
    pass

class Customer(SubRow):
    id = -1
    name = ''
    reference = ''
    address1 = ''
    address2 = ''
    postcode = ''
    city = ''

    def save(self):
        with SQLite3DB() as db:
            if self.id == -1:
                logging.debug("""Executing:
                    INSERT INTO customer
                    (name, reference, address1, address2, postcode, city)
                    VALUES (%s) """, self.__dict__)
                db.execute("""
                    INSERT INTO customer
                    (name, reference, address1, address2, postcode, city)
                    VALUES (?, ?, ?, ?, ?, ?) """,
                    (self.name, self.reference, self.address1, self.address2,
                        self.postcode, self.city,))
                self.id = db.c.lastrowid
            else:
                logging.debug("""
                    UPDATE customer SET
                    name = ?,
                    reference = ?,
                    address1 = ?,
                    address2 = ?,
                    postcode = ?,
                    city = ?
                    WHERE  id = ? [ %s ] """, self.__dict__)
                db.execute("""
                    UPDATE customer SET
                    name = ?,
                    reference = ?,
                    address1 = ?,
                    address2 = ?,
                    postcode = ?,
                    city = ?
                    WHERE  id = ?""",
                    (self.name, self.reference, self.address1, self.address2,
                        self.postcode, self.city, self.id,))
            db.commit()

class OrderProduct():
    id = -1
    orderid = 0
    productid = 0
    price = 0
    count = 0
    comment = ''

    # From Product
    name = ''
    description = ''
    price = 0.0
    stock = 0
    distributor = 0
    distributor_price = 0
    upc = ''
    physical_product = 1

    def __init__(self, orderid = None, product = None):
        """ Initialize from a product """
        self.count = 1
        if orderid:
            self.orderid = orderid
        if product is not None:
            self.productid = product.id
            self.name = product.name
            self.description = product.description
            self.price = product.price
            self.stock = product.stock
            self.distributor = product.distributor
            self.distributor_price = product.distributor_price
            self.upc = product.upc
            self.physical_product = product.physical_product
            logging.debug("self: %s",self.__dict__)
        else:
            logging.debug("no product!")

    def save(self):
        with SQLite3DB() as db:
            if self.id == -1:
                logging.debug("""
                        INSERT INTO order_products
                        (orderId, productId, comment, price, count)
                        VALUES (%d, %d, %s, %d, %d)
                        """ % (self.orderid, self.productid, self.comment,
                            self.price, self.count,))
                db.execute("""
                        INSERT INTO order_products
                        (orderId, productId, comment, price, count)
                        VALUES (?, ?, ?, ?,?)
                        """, (self.orderid, self.productid, self.comment,
                            self.price, self.count,))
                self.id = db.c.lastrowid
            else:
                db.execute("""
                        UPDATE order_products
                        SET comment = ?, price = ?, count = ?
                        WHERE id = ?
                        """, (self.comment, self.price, self.count, self.id))
            db.commit()

    def delete(self):
        if self.id == -1:
            return

        with SQLite3DB() as db:
            db.execute("DELETE FROM order_products WHERE id = ?", (self.id,))
            db.commit()
        self.id = -1

def OrderProductFactory(cursor, row):
    r = OrderProduct()
    for idx, col in enumerate(cursor.description):
        r.__dict__[col[0].lower()] = row[idx]
    return r


class Order(SubRow):
    id = -1
    description = ''
    customerid = 0
    status = 0
    invoicefile = ''
    created = 0

    def listProducts(self):
        products = []
        with SQLite3DB() as db:
            db.c.row_factory = OrderProductFactory
            db.c.execute("""
                        SELECT op.id, op.orderId, op.productId, op.price, op.count,
                        op.comment,
                        p.name, p.description, p.distributor, p.distributor_price,
                        p.upc, p.physical_product
                        distributor, distributor_price, UPC, physical_product
                        FROM order_products op
                        INNER JOIN products p ON p.id = op.productId
                        WHERE op.orderId = ?""", (self.id,))
            products = db.c.fetchall()
        return products


    def save(self):
        with SQLite3DB() as db:
            if self.id == -1:
                db.c.execute("""
                    INSERT INTO orders
                    (description, customerId, status, invoiceFile, created)
                    VALUES (?, ?, ?, ?, ?) """,
                    (self.description, self.customerid, self.status,
                        self.invoicefile, self.created))
                self.id = db.c.lastrowid
            else:
                db.c.execute("""
                    UPDATE orders SET
                    description = ?,
                    customerId = ?,
                    status = ?,
                    invoiceFile = ?,
                    created = ?
                    WHERE  id = ?""",
                    (self.description, self.customerid, self.status,
                        self.invoicefile, self.created, self.id))

            db.db.commit()

class IvDB():
    def __init__(self):
        with SQLite3DB() as db:
            script = ""
            with open('sql/schema.sql', 'r') as content_file:
                script = content_file.read()
            db.c.executescript(script)
            db.db.commit()

    def listDistributors(self, filter = ''):
        with SQLite3DB() as db:
            db.c.row_factory = Distributor
            db.c.execute("""SELECT * FROM distributor %s""" % filter)
            dist = db.c.fetchall()
        return dist

    def listProducts(self, filter = ''):
        with SQLite3DB() as db:
            db.c.row_factory = Product
            db.c.execute("""SELECT * FROM products %s ORDER BY name""" % filter)
            products = db.c.fetchall()
        return products

    def listOrders(self, filter = ''):
        with SQLite3DB() as db:
            db.c.row_factory = Order
            db.c.execute("SELECT * FROM orders %s ORDER BY id" % filter)
            orders = db.c.fetchall()
        return orders

    def listCustomers(self, filter = ''):
        with SQLite3DB() as db:
            db.c.row_factory = Customer
            db.c.execute("SELECT * FROM customer %s" % filter)
            customers = db.c.fetchall()
        return customers

App = None

class IvApp(npyscreen.NPSAppManaged):
    def onStart(self):
        npyscreen.setTheme(npyscreen.Themes.TransparentThemeLightText)

        self.db = IvDB()

        self.addForm("MAIN", MainMenuForm)
        self.addForm("PRODUCTFORM", ProductForm)
        self.addForm("PRODUCTEDITFORM", ProductEditForm)
        self.addForm("ORDERFORM", OrderForm)
        self.addForm("ORDEREDITFORM", OrderEditForm)
        self.addForm("ORDEREDITPRODUCTFORM", OrderEditProductForm);
        self.addForm("CUSTOMERFORM", CustomerForm)
        self.addForm("CUSTOMEREDITFORM", CustomerEditForm)

class IvList(npyscreen.MultiLineAction):
    def __init__(self, *args, **kwargs):
        super(IvList, self).__init__(*args, **kwargs)
        self.add_handlers({
            "^A": self.add_record,
            "^D": self.delete_record
        })

        self.fmt = "%s"
        self.selectForm = None
        self._display_value_func = None

        if 'fmt' in kwargs:
            self.fmt = kwargs['fmt']

        if 'selectForm' in kwargs:
            self.selectForm = kwargs['selectForm']

        if 'display_value' in kwargs:
            self._display_value_func = kwargs['display_value']

    def display_value(self, vl):
        if self._display_value_func is not None:
            return self._display_value_func(self,vl)
        else:
            return self.fmt.format(*vl)

    def actionHighlighted(self, selected, keypress):
        if self.selectForm is not None:
            self.parent.parentApp.getForm(self.selectForm).value = selected
            self.parent.parentApp.switchForm(self.selectForm)

    def add_record(self, *args, **keywords):
        if self.selectForm is not None:
            self.parent.parentApp.getForm(self.selectForm).value = None
            self.parent.parentApp.switchForm(self.selectForm)

    def delete_record(self, *args, **keywords):
        pass

class IvListTitle(npyscreen.TitleMultiLine):
    _entry_type = IvList

class IvListProducts(IvList):
    def delete_record(self, *args, **keywords):
        pass
        """
       self.parent.parentApp.myDatabase.delete_record(self.values[self.cursor_line][0])"""

class IvListOrderProducts(IvListTitle):
    def __init__(self, *args, **kwargs):
        super(IvListOrderProducts, self).__init__(*args, **kwargs)
        self.add_handlers({
            "+": self.increase_amount,
            "-": self.decrease_amount,
            "e": self.edit_post,
            "D": self.delete_post,
        })
    def increase_amount(self, *args, **keywords):
        op = self.parent.added_products[self.entry_widget.cursor_line]
        op.count += 1

        for p in self.parent.wProducts.values:
            if p.id == op.productid:
                if p.physical_product:
                    p.stock -= 1
                    p.updated_stock = True
                    logging.debug("-1 stock for product %s" % p.__dict__)
                break

        self.parent.update_list()

    def decrease_amount(self, *args, **keywords):
        op = self.parent.added_products[self.entry_widget.cursor_line]
        op.count -= 1

        for p in self.parent.wProducts.values:
            if p.id == op.productid:
                if p.physical_product:
                    logging.debug("+1 stock for product %s" % p.__dict__)
                    p.stock += 1
                    p.updated_stock = True
                break

        self.parent.update_list()

    def edit_post(self, *args, **keywords):
            self.parent.parentApp.getForm('ORDEREDITPRODUCTFORM').productIdx = self.entry_widget.cursor_line
            self.parent.parentApp.switchForm('ORDEREDITPRODUCTFORM')

    def delete_post(self, *args, **keywords):
        op = self.parent.added_products[self.entry_widget.cursor_line]
        self.parent.deleted_products.append(op)

        for p in self.parent.wProducts.values:
            if p.id == op.productid:
                if p.physical_product:
                    p.stock += op.count
                    p.updated_stock = True
                break

        del self.parent.added_products[self.entry_widget.cursor_line]
        self.parent.update_list()

class IvListOrderProductsAvailable(IvListTitle):
    def __init__(self, *args, **kwargs):
        super(IvListOrderProductsAvailable, self).__init__(*args, **kwargs)
        self.add_handlers({
            "+": self.increase_amount,
        })

    def increase_amount(self, *args, **keywords):
        """ Add this product to list of added products """

        logging.debug("added products before: %s" % (self.parent.added_products))
        logging.debug("product to add: %s %d" % (self.values,
            self.entry_widget.cursor_line))

        self.parent.added_products.append(
                OrderProduct(self.parent.value.id, self.values[self.entry_widget.cursor_line]))
        logging.debug("added products: %s" % (self.parent.added_products))
        self.parent.update_list()

        # Deduct one from this list
        self.values[self.entry_widget.cursor_line].stock -= 1
        self.update()

    def actionHighlighted(self, selected, keypress):
        """ Add this product to list of added products """
        self.parent.added_products += OrderProduct(orderid =
                self.parent.value.id, product = selected)

class IvListOrders(IvList):
    def delete_record(self, *args, **keywords):
        pass
        """
       self.parent.parentApp.myDatabase.delete_record(self.values[self.cursor_line][0])"""

class IvListCustomers(IvList):
    def delete_record(self, *args, **keywords):
        pass
        """
       self.parent.parentApp.myDatabase.delete_record(self.values[self.cursor_line][0])"""

class IvSelectOne(npyscreen.SelectOne):
    def __init__(self, *args, **kwargs):
        super(IvSelectOne, self).__init__(*args, **kwargs)
        self.fmt = "%s"
        self.selectForm = None
        self._display_value_func = None

        if 'fmt' in kwargs:
            self.fmt = kwargs['fmt']

        if 'selectForm' in kwargs:
            self.selectForm = kwargs['selectForm']

        if 'display_value' in kwargs:
            self._display_value_func = kwargs['display_value']

    def display_value(self, vl):
        if self._display_value_func is not None:
            return self._display_value_func(self,vl)
        else:
            return self.fmt.format(*vl)


class IvSelectOneTitle(npyscreen.TitleSelectOne):
    _entry_type = IvSelectOne

def product_fmt_func(current_widget,product):

        if product.physical_product:
            last_columns = "%7.2f kr %7.2f st" % (product.price, product.stock)
        else:
            last_columns = "%7.2f kr %7s st" % (product.price, '-')
        # 4 extra chars from npyscreen
        width =  current_widget.width - len(last_columns) - 4
        return u'{0:{width}}{1}'.format(product.name, last_columns, width=width)

def order_product_fmt_func(current_widget,product):
        last_columns = "%7.2f kr %7.2f st" % (product.price, product.count)
        # 4 extra chars from npyscreen
        width =  current_widget.width - len(last_columns) - 4
        width /= 2
        s = '{0:{width}}'.format(product.name.encode('utf-8'),width=width)
        s += '{0:{width}}'.format(product.comment.encode('utf-8'),width=width)
        s += last_columns
        return s

class SubForm(npyscreen.Form):
    def on_ok(self):
        self.parentApp.switchFormPrevious()

    def on_cancel(self):
        self.parentApp.switchFormPrevious()

class SubActionForm(npyscreen.ActionForm):
    def on_ok(self):
        self.parentApp.switchFormPrevious()

    def on_cancel(self):
        self.parentApp.switchFormPrevious()

class ProductEditForm(SubActionForm):
    def create(self):
        self.value = None
        self.wName = self.add(npyscreen.TitleText, name="Name:",value="")
        self.wDescription = self.add(npyscreen.TitleText, name="Description:",value="")
        self.wUPC = self.add(npyscreen.TitleText, name="UPC:",value="")
        self.wPrice = self.add(npyscreen.TitleText, name="Price:",value="")

        self.wDistributor = self.add(IvSelectOneTitle,
                name="Distributor:",
                fmt = "{1:}",
                scroll_exit=True, max_height=3, values =
                self.parentApp.db.listDistributors()
                )

        self.wDistributorPrice = self.add(npyscreen.TitleText,
                name="Purchase price:",value="",
                use_two_lines=False)

        self.wPhysicalProduct = self.add(npyscreen.TitleSelectOne,
                name="Is physical product:",
                scroll_exit=True, max_height=3, values =
                [ "No", "Yes" ], value = 1)
        self.wStock = self.add(npyscreen.TitleText, name="Current stock:",
                value="", use_two_lines=False)

    def beforeEditing(self):

        if self.value is None:
            self.value = Product()

        logging.debug(self.value)
        self.wName.value = self.value.name
        self.wPrice.value = str(self.value.price)
        self.wStock.value = str(self.value.stock)
        self.wDescription.value = self.value.description
        try:
            self.wDistributor.value = [x[0] for x in
                    self.wDistributor.values].index(self.value.distributor)
        except:
            self.wDistributor.value = 0
        self.wDistributorPrice.value = str(self.value.distributor_price)
        self.wUPC.value = self.value.upc
        self.wPhysicalProduct.value = self.value.physical_product

    def on_ok(self):
        self.value.name = self.wName.value

        try:
            self.value.price = Decimal(self.wPrice.value)
        except DecimalException:
            pass

        try:
            self.value.stock = Decimal(self.wStock.value)
        except DecimalException:
            pass

        self.value.description =  self.wDescription.value
        self.value.distributor = self.wDistributor.values[self.wDistributor.value[0]][0]

        try:
            self.value.distributor_price = Decimal(self.wDistributorPrice.value)
        except DecimalException:
            pass

        self.value.upc = self.wUPC.value
        self.value.physical_product = self.wPhysicalProduct.value[0]
        self.value.save()
        self.parentApp.getForm('PRODUCTFORM').wProductList.update()
        self.parentApp.switchFormPrevious()


class ProductForm(SubForm):
    def create(self):
        self.value = None

        self.wProductList = self.add(IvListProducts,
                selectForm = 'PRODUCTEDITFORM',
                display_value = product_fmt_func,
                name="Products list",
                scroll_exit=True, values =
                self.parentApp.db.listProducts()
                )

    def beforeEditing(self):
        self.update_list()

    def afterEditing(self):
        self.parentApp.switchFormPrevious()

    def update_list(self):
        self.wProductList.values = self.parentApp.db.listProducts()
        self.wProductList.display()

class OrderEditProductForm(npyscreen.ActionPopup):
    def create(self):
        self.productIdx = 0
        self.wComment = self.add(npyscreen.TitleText, name="Comment:", value = "")
        self.wPrice = self.add(npyscreen.TitleText, name="Price:", value = "")
        self.wAmount = self.add(npyscreen.TitleText, name="Amount:", value = "")

    def beforeEditing(self):
        form = self.parentApp.getForm('ORDEREDITFORM')

        self.wComment.value = form.added_products[self.productIdx].comment.encode('utf-8')
        self.wPrice.value = str(form.added_products[self.productIdx].price)
        self.wAmount.value = str(form.added_products[self.productIdx].count)

    def on_ok(self):

        form = self.parentApp.getForm('ORDEREDITFORM')

        op = form.added_products[self.productIdx]
        op.comment = self.wComment.value
        try: 
            op.price = Decimal(self.wPrice.value)
        except DecimalException:
            pass

        try:
            new_count = Decimal(self.wAmount.value)
            if op.count != new_count:
                # Update stock of product
                for p in form.wProducts.values:
                    if p.id == op.productid:
                        if p.physical_product:
                            p.stock -= new_count - op.count
                            p.updated_stock = True
                        break

                op.count = new_count
        except DecimalException:
            pass

        form.from_popup = True
        self.parentApp.switchFormPrevious()

    def on_cancel(self):
        self.parentApp.switchFormPrevious()


class OrderEditForm(SubActionForm):
    def create(self):
        self.value = None
        self.orderId = -1
        self.from_popup = False
        self.added_products = []
        self.deleted_products = []

        self.wDescription = self.add(npyscreen.TitleText, name="Description:",value="")
        self.wStatus = self.add(npyscreen.TitleSelectOne,
                name="Status:", scroll_exit=True, max_height=3, values =
                [ "New", "Ongoing", "Payed" ], value = 0)
        self.wCustomer = self.add(IvSelectOneTitle,
                name="Customer:",
                fmt = "{1:}",
                scroll_exit=True, max_height=3,
                values = self.parentApp.db.listCustomers())
        # Select first entry
        self.wCustomer.entry_widget.h_select('')
        self.wAddedProducts = self.add(IvListOrderProducts,
                name = "Currently added products:",
                display_value = order_product_fmt_func,
                max_height = len(self.added_products) + 5,
                begin_entry_at = 0,
                scroll_exit=True,
                values = self.added_products)

        self.wTotalSum = self.add(npyscreen.TitleFixedText,
                name = "Total sum:",
                value = "0 kr")

        self.wProducts = self.add(IvListOrderProductsAvailable,
                name = "Available products",
                display_value = product_fmt_func,
                scroll_exit=True,
                begin_entry_at = 0,
                values = self.parentApp.db.listProducts()
                )

    def beforeEditing(self):
        if self.from_popup:
            self.from_popup = False
            self.update_list()
            return

        logging.debug("added products = %s" % self.wAddedProducts.values)
        if self.value is None:
            self.value = Order()

        self.added_products = self.value.listProducts()
        self.deleted_products = []

        self.wDescription.value = self.value.description
        self.wStatus.value = self.value.status

        try:
            self.wCustomer.value = [x[0] for x in
                    self.wCustomer.values].index(self.value.customerid)
        except:
            self.wCustomer.value = 0

        self.update_list()

    def update_list(self):
        self.wAddedProducts.values = self.added_products

        # Recalculate total
        total = Decimal(0)
        for p in self.added_products:
            total = total + (p.price * p.count)
        self.wTotalSum.value = str(total) + " kr"

        self.wAddedProducts.display()
        self.wProducts.display()

    def on_ok(self):
        self.value.description = self.wDescription.value
        self.value.customerid = self.wCustomer.values[self.wCustomer.value[0]][0]
        self.value.status = self.wCustomer.value[0]
        self.value.invoicefile = ''
        self.value.created = 0
        self.value.save()

        for p in self.added_products:
            # Was this a new order?
            if p.orderid == -1:
                p.orderid = self.value.id
            p.save()

        for p in self.deleted_products:
            p.delete()

        # Check if stock has been modified
        for p in self.wProducts.values:
            if getattr(p,'updated_stock',False):
                logging.debug("Save product %s" % p.__dict__)
                p.save()
                p.updated_stock = False

        self.parentApp.switchFormPrevious()

class OrderForm(SubForm):
    def create(self):
        self.value = None

        self.wOrderList = self.add(IvListOrders,
                selectForm = 'ORDEREDITFORM',
                fmt = '{0:5d} {1:}',
                scroll_exit=True, values = []
                )

    def beforeEditing(self):
        if self.value == 1:
            # Only show status 0 (new) and 1 (ongoing)
            self.filter = "WHERE status IN (0, 1)"
        else:
            self.filter = "WHERE status = 2"

        self.update_list()

    def afterEditing(self):
        self.parentApp.switchFormPrevious()

    def update_list(self):
        self.wOrderList.values = self.parentApp.db.listOrders(self.filter)
        self.wOrderList.display()

class CustomerEditForm(SubActionForm):
    def create(self):
        self.value = None

        self.wName = self.add(npyscreen.TitleText, name="Name:",value="")
        self.wReference = self.add(npyscreen.TitleText, name="Reference:",value="")
        self.wAddress1 = self.add(npyscreen.TitleText, name="Address 1:",value="")
        self.wAddress2 = self.add(npyscreen.TitleText, name="Address 2:",value="")
        self.wPostcode = self.add(npyscreen.TitleText, name="Postcode:",value="")
        self.wCity = self.add(npyscreen.TitleText, name="City:",value="")

    def beforeEditing(self):
        if self.value is None:
            self.value = Customer()

        self.wName.value = self.value.name
        self.wReference.value = self.value.reference
        self.wAddress1.value = self.value.address1
        self.wAddress2.value = self.value.address2
        self.wPostcode.value = self.value.postcode
        self.wCity.value = self.value.city

    def on_ok(self):
        self.value.name = self.wName.value
        self.value.reference = self.wReference.value
        self.value.address1 = self.wAddress1.value
        self.value.address2 = self.wAddress2.value
        self.value.postcode = self.wPostcode.value
        self.value.city = self.wCity.value
        self.value.save()
        self.parentApp.switchFormPrevious()

class CustomerForm(SubForm):
    def create(self):
        self.value = None

        self.wCustomerList = self.add(IvListCustomers,
                selectForm = 'CUSTOMEREDITFORM',
                fmt = '{1:s}',
                scroll_exit=True, values =
                self.parentApp.db.listCustomers()
                )

    def beforeEditing(self):
        self.update_list()

    def afterEditing(self):
        self.parentApp.switchFormPrevious()

    def update_list(self):
        self.wCustomerList.values = self.parentApp.db.listCustomers()
        self.wCustomerList.display()

class MainMenuList(npyscreen.MultiLineAction):
    def display_value(self, vl):
        return "%s" % (vl[0],)

    def actionHighlighted(self, selected, keypress):
        self.parent.parentApp.getForm(selected[1]).value = selected[2]
        self.parent.parentApp.switchForm(selected[1])


class MainMenuForm(npyscreen.ActionForm):
    def create(self):
        self.wa = self.add(MainMenuList,
                scroll_exit=True, values =
                [
                    [ 'Produkter', 'PRODUCTFORM', 1 ],
                    [ 'Pågende Ordrar', 'ORDERFORM', 1 ],
                    [ 'Avslutade Ordrar', 'ORDERFORM', 2 ],
                    [ 'Kunder', 'CUSTOMERFORM', 1 ],
                ])

if __name__ == "__main__":
    App = IvApp()
    App.run()

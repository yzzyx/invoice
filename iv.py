#!/usr/bin/env python
# encoding: utf-8
import npyscreen
import sqlite3
import os
import logging

LOG_FILENAME = '/tmp/iv.log'
logging.basicConfig(filename=LOG_FILENAME,
                    level=logging.DEBUG,
                    )

class IvDB():
    def __init__(self,filename):
        self.dbfilename = filename

        db = sqlite3.connect(self.dbfilename)
        c = db.cursor()
        script = ""
        with open('sql/schema.sql', 'r') as content_file:
            script = content_file.read()
        c.executescript(script)
        db.commit()
        c.close()

    def listDistributors(self, filter = ''):
        db = sqlite3.connect(self.dbfilename)
        c = db.cursor()
        c.execute("""
                    SELECT id, name
                    FROM distributor %s""" % filter)
        dist = c.fetchall()
        db.close()
        return dist

    def listProducts(self, filter = ''):
        db = sqlite3.connect(self.dbfilename)
        c = db.cursor()
        c.execute("""
                    SELECT id, name, price, stock, description,
                    distributor, distributor_price, UPC, physical_product
                    FROM products %s""" % filter)
        products = c.fetchall()
        products = [list(l) for l in products]
        db.close()
        return products

    def listOrderProducts(self, order_id):
        db = sqlite3.connect(self.dbfilename)
        c = db.cursor()
        c.execute("""
                    SELECT op.id, op.productId, p.name, op.price, op.count, description,
                    distributor, distributor_price, UPC, physical_product,
                    comment
                    FROM order_products op
                    INNER JOIN products p ON p.id = op.productId
                    WHERE op.orderId = ?""", (order_id,))
        products = c.fetchall()
        products = [list(l) for l in products]
        db.close()
        return products

    def setOrderProducts(self, order_id, products):
        db = sqlite3.connect(self.dbfilename)
        c = db.cursor()
        for p in products:
            if p[0] == -1:
                c.execute("""
                    INSERT INTO order_products
                    (orderId, productId, comment, price, count)
                    VALUES (?, ?, ?, ?,?)
                    """, (order_id, p[1], p[10], p[3], p[4],))
                p[0] = c.lastrowid
            else:
                c.execute("""
                    UPDATE order_products
                    SET comment = ?, price = ?, count = ?
                    WHERE id = ?
                    """, (p[10], p[3], p[4],p[0],))
        db.commit()
        c.close()

    def getProduct(self, id):
        return self.listProducts('WHERE id = %d' % id)[0]

    def saveProduct(self, product):
        db = sqlite3.connect(self.dbfilename)
        c = db.cursor()

        if product[0] == -1:
            logging.debug("""
                INSERT INTO products (name, price, stock, description,
                    distributor, distributor_price, UPC, physical_product)
                    VALUES (?,?,?,?,?,?,?,?)""")
            logging.debug(tuple(product[1:]))
            c.execute("""
                INSERT INTO products (name, price, stock, description,
                    distributor, distributor_price, UPC, physical_product)
                    VALUES (?,?,?,?,?,?,?,?)""",
                    tuple(product[1:]))
            id = c.lastrowid
        else:
            c.execute("""
                UPDATE products SET
                    name = ?, price = ?, stock = ?, description = ?,
                    distributor = ?, distributor_price = ?,
                    UPC = ?, physical_product = ?
                    WHERE id = ?""",
                    tuple(product[1:] + product[:1]))
            id = product[0]
        db.commit()
        c.close()
        return id


    def listOrders(self, filter = ''):
        db = sqlite3.connect(self.dbfilename)
        c = db.cursor()
        c.execute("""
                    SELECT id, description, customerId, status,
                    invoiceFile, created
                    FROM orders %s""" % filter)
        orders = c.fetchall()
        orders = [list(l) for l in orders]
        db.close()
        return orders

    def getOrder(self, id):
        return self.listOrders('WHERE id = %d' % id)[0]

    def saveOrder(self, order, products):
        db = sqlite3.connect(self.dbfilename)
        c = db.cursor()
        if order[0] == -1:
            c.execute("""
                INSERT INTO orders
                (description, customerId, status, invoiceFile, created)
                VALUES (?, ?, ?, ? ?) """, tuple(order[1:]))
            order[0] = c.lastrowid
        else:
            c.execute("""
                UPDATE orders SET
                description = ?,
                customerId = ?,
                status = ?,
                invoiceFile = ?,
                created = ?
                WHERE  id = ?""", tuple(order[1:] + order[:1]))
        db.commit()
        c.close()
        self.setOrderProducts(order[0], products)

    def listCustomers(self, filter = ''):
        db = sqlite3.connect(self.dbfilename)
        c = db.cursor()
        c.execute("""
                    SELECT id, name, reference,
                    address1, address2,
                    postcode, city
                    FROM customer %s""" % filter)
        customers = c.fetchall()
        customers = [list(l) for l in customers]
        db.close()
        return customers

    def getCustomer(self, id):
        return self.listCustomers('WHERE id = %d' % id)[0]

    def saveCustomer(self, customer):
        db = sqlite3.connect(self.dbfilename)
        c = db.cursor()
        if customer[0] == -1:
            c.execute("""
                INSERT INTO customer
                (name, reference, address1, address2, postcode, city)
                VALUES (?, ?, ?, ?, ?, ?) """, tuple(customer[1:]))
            customer[0] = c.lastrowid
        else:
            c.execute("""
                UPDATE customer SET
                name = ?,
                reference = ?,
                address1 = ?,
                address2 = ?,
                postcode = ?,
                city = ?
                WHERE  id = ?""", tuple(customer[1:] + customer[:1]))
        db.commit()
        c.close()

App = None

class IvApp(npyscreen.NPSAppManaged):
    def onStart(self):
        npyscreen.setTheme(npyscreen.Themes.TransparentThemeLightText)

        self.db = IvDB('invoice.db')

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
            self.parent.parentApp.getForm(self.selectForm).value = selected[0]
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
            "^E": self.edit_post,
        })
    def increase_amount(self, *args, **keywords):
        self.parent.added_products[self.entry_widget.cursor_line][4] += 1
        self.parent.update_list()
#        self.values[self.entry_widget.cursor_line][3] += 1
#        self.update()

    def decrease_amount(self, *args, **keywords):
        self.parent.added_products[self.entry_widget.cursor_line][4] -= 1
        self.parent.update_list()
#        self.values[self.entry_widget.cursor_line][3] -= 1
#        self.update()

    def edit_post(self, *args, **keywords):
            self.parent.parentApp.getForm('ORDEREDITPRODUCTFORM').productIdx = self.entry_widget.cursor_line
            self.parent.parentApp.switchForm('ORDEREDITPRODUCTFORM')

    def delete_record(self, *args, **keywords):
        pass
        """
       self.parent.parentApp.myDatabase.delete_record(self.values[self.cursor_line][0])"""

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
        self.parent.added_products += [ [
             -1, # Order_Product-id
             self.values[self.entry_widget.cursor_line][0],
             self.values[self.entry_widget.cursor_line][1],
             self.values[self.entry_widget.cursor_line][2],
             1, # Count
             self.values[self.entry_widget.cursor_line][4],
             self.values[self.entry_widget.cursor_line][5],
             self.values[self.entry_widget.cursor_line][6],
             self.values[self.entry_widget.cursor_line][7],
             self.values[self.entry_widget.cursor_line][8],
             '', # Comment
             ] ]
        logging.debug("added products: %s" % (self.parent.added_products))
        self.parent.update_list()

        # Deduct one from this list
        self.values[self.entry_widget.cursor_line][3] -= 1
        self.update()

    def actionHighlighted(self, selected, keypress):
        """ Add this product to list of added products """
        self.parent.added_products += [ [
                selected[0:3] +
                     [ 1 ] + # Count
                selected[4:] ] ]
        self.parent.update_list()


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

def product_fmt_func(current_widget,vl):
        last_columns = "%7.2f kr %7.2f st" % (vl[2], vl[3])
        # 6 extra chars from npyscreen
        width =  current_widget.width - len(last_columns) - 6
        return '{0:{width}}{1}'.format(vl[1].encode('utf-8'), last_columns, width=width)

def order_product_fmt_func(current_widget,product):
        last_columns = "%7.2f kr %7.2f st" % (product[3], product[4])
        # 6 extra chars from npyscreen
        width =  current_widget.width - len(last_columns) - 6
        width /= 2
        s = '{0:{width}}'.format(product[2].encode('utf-8'),width=width)
        s += '{0:{width}}'.format(product[10].encode('utf-8'),width=width)
        s += last_columns
        return s

class SubForm(npyscreen.ActionForm):
    def on_ok(self):
        self.parentApp.switchFormPrevious()

    def on_cancel(self):
        self.parentApp.switchFormPrevious()

class ProductEditForm(SubForm):
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
        if self.value:
            product = self.parentApp.db.getProduct(self.value)
            self.productId = product[0]
            self.wName.value = product[1]
            self.wPrice.value = str(product[2])
            self.wStock.value = str(product[3])
            self.wDescription.value = product[4]
            try:
                self.wDistributor.value = [x[0] for x in
                        self.wDistributor.values].index(product[5])
            except:
                self.wDistributor.value = 0
            self.wDistributorPrice.value = str(product[6])
            self.wUPC.value = product[7]
            self.wPhysicalProduct.value = product[8]
        else:
            self.productId = -1
            self.wName.value = ''
            self.wDescription.value = ''
            self.wUPC.value = ''
            self.wPrice.value = ''
            self.wDistributor.value = 0
            self.wDistributorPrice.value = 1

    def on_ok(self):
        product = [
         self.productId,
         self.wName.value,
         self.wPrice.value,
         self.wStock.value,
         self.wDescription.value,
         self.wDistributor.values[self.wDistributor.value[0]][0],
         self.wDistributorPrice.value,
         self.wUPC.value,
         self.wPhysicalProduct.value[0]
        ]
        self.parentApp.db.saveProduct(product)
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

        self.wComment.value = form.added_products[self.productIdx][10].encode('utf-8')
        self.wPrice.value = str(form.added_products[self.productIdx][3])
        self.wAmount.value = str(form.added_products[self.productIdx][4])

    def on_ok(self):

        form = self.parentApp.getForm('ORDEREDITFORM')
        form.added_products[self.productIdx][10] = self.wComment.value
        form.added_products[self.productIdx][3] = int(self.wPrice.value)
        form.added_products[self.productIdx][4] = int(self.wAmount.value)
        form.from_popup = True
        self.parentApp.switchFormPrevious()

    def on_cancel(self):
        self.parentApp.switchFormPrevious()


class OrderEditForm(SubForm):
    def create(self):
        self.value = None
        self.orderId = -1
        self.from_popup = False
        self.added_products = []

        self.wDescription = self.add(npyscreen.TitleText, name="Description:",value="")
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
                max_height = 15,
                scroll_exit=True,
                values = self.added_products)

        self.wTotalSum = self.add(npyscreen.TitleFixedText,
                name = "Total sum:",
                value = "0 kr")

        self.wProducts = self.add(IvListOrderProductsAvailable,
                name = "Available products",
                display_value = product_fmt_func,
                max_height = 15,
                scroll_exit=True, values =
                self.parentApp.db.listProducts()
                )

    def beforeEditing(self):
        if self.from_popup:
            self.from_popup = False
            self.update_list()
            return

        logging.debug("added products = %s" % self.wAddedProducts.values)
        if self.value is not None:
            order = self.parentApp.db.getOrder(self.value)
            self.orderId = order[0]
            self.added_products = self.parentApp.db.listOrderProducts(self.value)

            total = 0
            for p in self.added_products:
                total += p[3] * p[4]
            self.wTotalSum.value = str(total) + " kr"

            self.wDescription.value = order[1]
            try:
                self.wCustomer.value = [x[0] for x in
                        self.wCustomer.values].index(order[2])
            except:
                self.wCustomer.value = 0
        else:
            self.orderId = -1
            self.added_products = []
            self.wDescription = ''
            self.wCustomer.value = 0

        self.update_list()

    def update_list(self):
        self.wAddedProducts.values = self.added_products

        # Recalculate total
        total = 0
        for p in self.added_products:
            total = total + (p[3] * p[4])
        self.wTotalSum.value = str(total) + " kr"

        self.wAddedProducts.display()

    def on_ok(self):
        order = [
         self.orderId,
         self.wDescription.value, # Description
         self.wCustomer.values[self.wCustomer.value[0]][0], # CustomerId
         0, # Status
         '', # Invoicefile
         0, # Created
        ]
        self.parentApp.db.saveOrder(order, self.added_products)
        self.parentApp.switchFormPrevious()

class OrderForm(SubForm):
    def create(self):
        self.value = None

        self.wOrderList = self.add(IvListOrders,
                selectForm = 'ORDEREDITFORM',
                fmt = '{0:5d} {1:}',
                scroll_exit=True, values =
                self.parentApp.db.listOrders()
                )

    def beforeEditing(self):
        self.update_list()

    def update_list(self):
        self.wOrderList.values = self.parentApp.db.listOrders()


        self.wOrderList.display()

class CustomerEditForm(SubForm):
    def create(self):
        self.value = None

        self.wName = self.add(npyscreen.TitleText, name="Name:",value="")
        self.wReference = self.add(npyscreen.TitleText, name="Reference:",value="")
        self.wAddress1 = self.add(npyscreen.TitleText, name="Address 1:",value="")
        self.wAddress2 = self.add(npyscreen.TitleText, name="Address 2:",value="")
        self.wPostcode = self.add(npyscreen.TitleText, name="Postcode:",value="")
        self.wCity = self.add(npyscreen.TitleText, name="City:",value="")

    def beforeEditing(self):
        if self.value is not None:
            self.customer_id = self.value
            customer = self.parentApp.db.getCustomer(self.customer_id)
            self.wName.value = customer[1]
            self.wReference.value = customer[2]
            self.wAddress1.value = customer[3]
            self.wAddress2.value = customer[3]
            self.wPostcode.value = customer[4]
            self.wCity.value = customer[5]
        else:
            self.customer_id = -1
            self.wName.value = ''
            self.wReference.value = ''
            self.wAddress1.value = ''
            self.wAddress2.value = ''
            self.wPostcode.value = ''
            self.wCity.value = ''

    def on_ok(self):
        customer = [
         self.customer_id,
         self.wName.value,
         self.wReference.value,
         self.wAddress1.value,
         self.wAddress2.value,
         self.wPostcode.value,
         self.wCity.value,
        ]
        self.parentApp.db.saveCustomer(customer)
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

    def update_list(self):
        self.wCustomerList.values = self.parentApp.db.listCustomers()
        self.wCustomerList.display()

class MainMenuList(npyscreen.MultiLineAction):
    def display_value(self, vl):
        return "%s" % (vl[0],)

    def actionHighlighted(self, selected, keypress):
        self.parent.parentApp.getForm(selected[1]).value = selected[2]
        self.parent.parentApp.switchForm(selected[1])


class MainMenuForm(npyscreen.Form):
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

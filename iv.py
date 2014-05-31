#!/usr/bin/env python
# encoding: utf-8
import npyscreen
import sqlite3
import os

class IvDB():
    def __init__(self,filename):
        self.dbfilename = filename

        if not os.path.exists(filename):
            db = sqlite3.connect(self.dbfilename)
            c = db.cursor()
            c.executescript('sql/schema.sql')
            db.commit()
            c.close()

    def listProducts(self, filter):
        db = sqlite3.connect(self.dbfilename)
        c = db.cursor()
        c.execute("""
                    SELECT id, name, price, stock, description,
                    distributor, distributor_price, UPC, physical_product
                    FROM products %s""" % filter)
        products = c.fetchall()
        db.close()
        return products

    def getProduct(self, id):
        return self.listProducts('WHERE id = %d' % id)

    def listOrders(self, filter):
        db = sqlite3.connect(self.dbfilename)
        c = db.cursor()
        c.execute("""
                    SELECT id, description, customerId, status,
                    invoiceFile, created
                    FROM orders %s""" % filter)
        orders = c.fetchall()
        db.close()
        return orders

    def getOrder(self, id):
        return self.listOrders('WHERE id = %d' % id)

    def listCustomers(self, filter):
        db = sqlite3.connect(self.dbfilename)
        c = db.cursor()
        c.execute("""
                    SELECT id, name, reference,
                    address1, address2,
                    postcode, city
                    FROM customer %s""" % filter)
        customers = c.fetchall()
        db.close()
        return customers

    def getCustomer(self, id):
        return self.listCustomers('WHERE id = %d' % id)

App = None

class IvApp(npyscreen.NPSAppManaged):
    def onStart(self):
        npyscreen.setTheme(npyscreen.Themes.TransparentThemeLightText)

        self.addForm("MAIN", MainMenuForm)
        self.addForm("PRODUCTFORM", ProductForm)
        self.addForm("PRODUCTEDITFORM", ProductEditForm)
        self.addForm("ORDERFORM", OrderForm)
        self.addForm("ORDEREDITFORM", OrderEditForm)
        self.addForm("CUSTOMERFORM", CustomerForm)
        self.addForm("CUSTOMEREDITFORM", CustomerEditForm)

        self.db = IvDB()

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
            "-": self.decrease_amount
        })
    def increase_amount(self, *args, **keywords):
        self.values[self.entry_widget.cursor_line][3] += 1
        self.update()

    def decrease_amount(self, *args, **keywords):
        self.values[self.entry_widget.cursor_line][3] -= 1
        self.update()

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
        pass

    def actionHighlighted(self, selected, keypress):
        """ Add this product to list of added products """
        pass


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

def product_fmt_func(current_widget,vl):
        last_columns = "%7.2f kr %7.2f st" % (vl[2], vl[3])


        # 6 extra chars from npyscreen
        width =  current_widget.width - len(last_columns) - 6
        return '{0:{width}}{1}'.format(vl[1], last_columns, width=width)

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

        self.wDistributor = self.add(npyscreen.TitleSelectOne,
                name="Distributor:",
                scroll_exit=True, max_height=3, values =
                ['Department 1', 'Department 2', 'Department 3'])
        # Select first entry
        self.wDistributor.entry_widget.h_select('')
        self.wDistributorPrice = self.add(npyscreen.TitleText,
                name="Purchase price:",value="",
                use_two_lines=False)

    def beforeEditing(self):
        pass
    """
        if self.value:
            record = self.parentApp.myDatabase.get_record(self.value)
            self.name = "Record id : %s" % record[0]
            self.record_id          = record[0]
            self.wgLastName.value   = record[1]
            self.wgOtherNames.value = record[2]
            self.wgEmail.value      = record[3]
        else:
            self.name = "New Record"
            self.record_id          = ''
            self.wgLastName.value   = ''
            self.wgOtherNames.value = ''
            self.wgEmail.value      = ''
        """

class ProductForm(SubForm):
    def create(self):
        self.value = None

        self.wa = self.add(IvListProducts,
                selectForm = 'PRODUCTEDITFORM',
                display_value = product_fmt_func,
                name="Products list",
                scroll_exit=True, values =
                [
                    [1,'Produkt 1',50.50,1],
                    [2,'Produkt 2 xjxj',50.50,1],
                    [3,'Produkt 3',2500.50,19],
                    [4,'Produkt 4',202.50,75],
                ])

class OrderEditForm(SubForm):
    def create(self):
        self.value = None

        self.wDescription = self.add(npyscreen.TitleText, name="Description:",value="")
        self.wCustomer = self.add(npyscreen.TitleSelectOne,
                name="Customer:",
                scroll_exit=True, max_height=3, values =
                ['Customer 1', 'Customer 2', 'Customer 3'])
        # Select first entry
        self.wCustomer.entry_widget.h_select('')
        self.wAddedProducts = self.add(IvListOrderProducts,
                name = "Currently added products:",
                display_value = product_fmt_func,
                max_height = 15,
                scroll_exit=True, values =
                [
                    [1,'Produkt 1',50.50,1],
                    [2,'Produkt 2 xjxj',50.50,1],
                    [3,'Produkt 3',2500.50,1],
                    [4,'Produkt 4',202.50,1],
                ])
        self.wTotalSum = self.add(npyscreen.TitleFixedText,
                name = "Total sum:",
                value = "1002 kr")
        self.wProducts = self.add(IvListOrderProductsAvailable,
                name = "Available products",
                display_value = product_fmt_func,
                max_height = 15,
                scroll_exit=True, values =
                [
                    [1,'Produkt 1',50.50,1],
                    [2,'Produkt 2 xjxj',50.50,1],
                    [3,'Produkt 3',2500.50,1],
                    [4,'Produkt 4',202.50,1],
                ])

class OrderForm(SubForm):
    def create(self):
        self.value = None

        self.wa = self.add(IvListOrders,
                selectForm = 'ORDEREDITFORM',
                fmt = '{0:5d} {1:}',
                scroll_exit=True, values =
                [
                    [1,'Order 1 Description'],
                    [2,'Order 2 Description'],
                    [3,'Order 3 Description'],
                    [4,'Order 4 Description'],
                ])

class CustomerEditForm(SubForm):
    def create(self):
        self.value = None

        self.wName = self.add(npyscreen.TitleText, name="Name:",value="")
        self.wReference = self.add(npyscreen.TitleText, name="Reference:",value="")
        self.wAddress1 = self.add(npyscreen.TitleText, name="Address 1:",value="")
        self.wAddress2 = self.add(npyscreen.TitleText, name="Address 2:",value="")
        self.wPostcode = self.add(npyscreen.TitleText, name="Postcode:",value="")
        self.wCity = self.add(npyscreen.TitleText, name="City:",value="")


class CustomerForm(SubForm):
    def create(self):
        self.value = None

        self.wa = self.add(IvListCustomers,
                selectForm = 'CUSTOMEREDITFORM',
                fmt = '{1:s}',
                scroll_exit=True, values =
                [
                    [1,'Customer 1'],
                    [2,'Customer 2'],
                    [3,'Customer 3'],
                    [4,'Customer 4'],
                ])

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

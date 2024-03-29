import json
import re

import bcrypt
from django.shortcuts import render, redirect

# Create your views here.
from pytz import unicode
from urllib.parse import unquote
from .models import Supplier, Product, SKU, Stored
from user.models import Order, Order_Detail

# *********************** views ******************************** #
def sindex(request):
    return render(request, 'supplier_index.html')

def become_partner(request):
    if request.POST:
        warning_list = []

        id = request.POST['company_id']
        if check_id(id) or check_exist(id):
            warning_list.append("統編有誤")
            print(check_id(id))
            print(check_exist(id))

        c_name = request.POST['company_name']  # 公司名稱****************
        if check_name(c_name):
            warning_list.append("公司名稱有誤")

        principal = request.POST['supplier_name']  # 負責人姓名
        if check_name(principal):
            warning_list.append("姓名有誤")

        phone = request.POST['supplier_phone']
        if check_phone(phone):
            warning_list.append("電話號碼有誤")

        mail = request.POST['supplier_email']
        if check_email(mail):
            warning_list.append("電子郵件有誤")

        pwd = request.POST['supplier_password']
        if check_password(pwd):
            warning_list.append("密碼有誤")

        check_pwd = request.POST['password_check']
        if check_pwd_match(pwd,check_pwd):
            warning_list.append("確認密碼有誤")

        address = request.POST['company_address']
        if check_name(address):
            warning_list.append("通訊地有誤")
        #Picture = request.POST['']

        if len(warning_list) > 0:
            context = {'warning': warning_list}
            return render(request, 'supplier_become_partner.html', context)
        else:
            salt,pwd = hashpwd(pwd)
            supplier = Supplier(S_ID=id,C_Name=c_name,Principal=principal,Phone=phone,Mail=mail,PWD=pwd,Salt=salt,Active=False,Address=address)
            supplier.save()
            #return render(request, 'register_succeed.html')
            context = {'identification': 'supplier'}
            return render(request, 'register_succeed.html', context)
    return render(request, 'supplier_become_partner.html')

def slogin(request):
    if request.POST:
        try:
            c_name = request.POST['company_name']
            c_id = request.POST['company_id']
            pwd = request.POST['supplier_password']

            supplier = Supplier.objects.get(S_ID=c_id)

            if bcrypt.checkpw(bytes(pwd, 'utf-8'), bytes(supplier.PWD)) and supplier.C_Name == c_name:
                request.session['supplier_id'] = supplier.S_ID
                return redirect('sprofile')
            else:
                context = {'failed': "登入資訊或密碼錯誤"}
                return render(request, 'supplier_login.html', context)
        except:
            context = {'failed': "登入資訊或密碼錯誤"}
            return render(request, 'supplier_login.html', context)
    elif 'supplier_id' in request.session:
        return redirect('sprofile')

    return render(request, 'supplier_login.html')

def slogout(request):
    del request.session['supplier_id']
    return redirect('sindex')

def sprofile(request):
    if 'supplier_id' not in request.session:
        return redirect('slogin')
    c_id = request.session['supplier_id']
    supplier = Supplier.objects.get(S_ID=c_id)
    products = Product.objects.filter(Brand=supplier)
    orders = Order.objects.filter(Supplier=supplier)

    context = {'supplier': supplier, 'products': products, 'orders': orders}
    return render(request, 'supplier_profile.html', context)

def changesprofile(request):
    if 'supplier_id' not in request.session:
        return redirect('slogin')
    elif request.POST:
        warning_list = {}

        principal = request.POST['supplier_name']
        if check_name(principal):
            warning_list.append("姓名有誤")

        phone = request.POST['supplier_phone']
        if check_phone(phone):
            warning_list.append("電話號碼有誤")

        mail = request.POST['supplier_email']
        if check_email(mail):
            warning_list.append("電子郵件有誤")

        address = request.POST['company_address']
        if check_name(address):
            warning_list.append("通訊地有誤")



        c_id = request.session['supplier_id']
        supplier = Supplier.objects.get(S_ID=c_id)

        if len(warning_list) > 0:
            context = {'warn1':warning_list}
            return render(request, 'supplier_profile.html',context)
        else:
            supplier.Principal = principal
            supplier.Mail = mail
            supplier.Address =address
            supplier.Phone = phone
            print("成功!!!")
            return redirect('sprofile')
    return redirect('sprofile')

def profileimg(request):
    if request.POST:
        c_id = request.session['supplier_id']
        supplier = Supplier.objects.get(S_ID=c_id)
        if 'image' in (request.FILES):
            img = request.FILES['image']
            filename = supplier.S_ID + '.' + splitext(img.name)
            img.name = filename
            supplier.Picture = img
            supplier.save()
            return redirect('sprofile')

    elif 'supplier_id' not in request.session:
        return redirect('slogin')
    return redirect('sprofile')

def changespwd(request):
    if request.POST:
        old = request.POST['supplier_password']
        new = request.POST['new_supplier_password']
        check_new = request.POST['new_password_check']

        c_id = request.session['supplier_id']

        supplier = Supplier.objects.get(S_ID=c_id)

        if bcrypt.checkpw(bytes(old, 'utf-8'), bytes(supplier.PWD))\
                and (not check_password(new))\
                and (not check_pwd_match(new,check_new)) :
            new_salt,new_hashed = hashpwd(new)
            supplier.Salt = new_salt
            supplier.PWD = new_hashed
            supplier.save()
            print('修改成功')
            return redirect('slogout')
        else:
            warning_list = []
            # 密碼格式檢查
            if check_password(old):
                warning_list.append("密碼格式不符")
            if check_pwd_match(new, check_new):
                warning_list.append("密碼與確認密碼不符")
            if not bcrypt.checkpw(bytes(old, 'utf-8'),bytes(supplier.PWD)):
                warning_list.append("舊密碼輸入錯誤")
            context = {'warn_2':warning_list, 'supplier':supplier}
            return render(request, 'supplier_profile.html',context)
    elif 'supplier_id' not in request.session:
        return redirect('slogin')
    return redirect('sprofile')

colors_id = {"red":"01", "orange":"02", "yellow":"03", "pink":"04",
          "cyan":"05", "blue":"06", "purple":"07", "green":"08",
          "gray":"09", "black":"10", "white":"11", "brown":"12"}

def addproduct(request):
    if 'supplier_id' not in request.session:
        return redirect('slogin')
    elif request.POST:
        c_id = request.session['supplier_id']
        supplier = Supplier.objects.get(S_ID=c_id)
        product_name = request.POST['product_name']
        product_price = request.POST['product_price']
        genre = request.POST['genre']
        category = request.POST['category']
        sales_category = request.POST['product_sales_category']
        product_description = request.POST['product_description']

        product_id = c_id + create_product_id(supplier)

        product = Product(ID=product_id, Name=product_name, Brand=supplier, Price=int(product_price),
                          Genre=genre, Category=category, Sale_Category=sales_category, Description=product_description)

        product.save()
        sizes = request.POST.getlist('size')
        style_num = int(request.POST['product_style_number'])
        for index in range(style_num):
            index_str = str(index)
            sku_id = product.ID + request.POST['Id_'+index_str]
            sku_name = request.POST['Color_'+index_str]
            img = request.FILES['Picture_'+index_str]
            filename = sku_id + '.' + splitext(img.name)
            img.name = filename
            Sku = SKU(SKU_ID=sku_id, Product=product, Color=sku_name, Picture=img)
            Sku.save()
            for s in sizes:
                stored = request.POST[s+"_"+index_str]
                store = Stored(sku=Sku, Size=s, stored=stored)
                store.save()


    """
        if request.POST:
        c_id = request.session['supplier_id']
        supplier = Supplier.objects.get(S_ID=c_id)

        product_id = c_id + create_product_id(supplier)
        product_name = request.POST['product_name']
        product_price = request.POST['product_price']
        genre = request.POST['genre']
        category = request.POST['category']
        sales_category = request.POST['product_sales_category']
        sizes = request.POST.getlist('size')
        product_description = request.POST['product_description']

        product = Product(ID=product_id, Name=product_name, Brand=supplier, Price=int(product_price),
                          Genre=genre, Category=category, Sale_Category=sales_category, Description=product_description)
        product.save()

        color = request.POST.getlist('color')
        for c in color:
            sku_id = product_id + colors_id[c]
            str = 'image'+c
            img = request.FILES[str]
            filename = sku_id + '.' + splitext(img.name)
            img.name = filename
            Sku = SKU(SKU_ID=sku_id, Product=product, Color=c, Picture=img)
            Sku.save()
            for s in sizes:
                size_stored = Sku.Color + "_" + s +"_stored"
                print(size_stored)
                stored = request.POST[size_stored]
                print(stored)
                Store = Stored(sku=Sku, Size=s, stored=stored)
                Store.save()

        genre_choices = Product.GENRE_CHOICES
        category_choices = Product.CATEGORY_CHOICES
        color_chioces = SKU.COLOR_CHOICES
        size_choices = Stored.SIZE_CHOICES
        context = {'genre': genre_choices, 'category': category_choices, 'color': color_chioces, 'size': size_choices}


        return render(request, 'supplier_addproduct.html',context)
    :param request: 
    :return: 
    """


    genre_choices = Product.GENRE_CHOICES
    category_choices = Product.CATEGORY_CHOICES
    color_chioces = SKU.COLOR_CHOICES
    size_choices = Stored.SIZE_CHOICES
    context = {'genre':genre_choices, 'category':category_choices, 'color':color_chioces, 'size':size_choices}
    return render(request, 'supplier_addproduct.html',context)

def editproduct(request, product_ID):
    if request.POST:
        num = int(request.POST['product_style_number'])
        product = Product.objects.get(ID=product_ID)
        product.Name = request.POST['product_name']
        product.Price = int(request.POST['product_price'])
        product.Genre = request.POST['genre']
        product.Category = request.POST['category']
        product.Sale_Category = request.POST['product_sales_category']
        product.Description = request.POST['product_description']
        product.save()
        sizes = request.POST.getlist('size')

        skus = SKU.objects.filter(Product=product)
        for i in range(num):
            sku_id = product.ID + request.POST['Id_'+str(i)]
            color = request.POST['Color_'+str(i)]
            image_id = 'Picture_'+str(i)
            img = None
            if image_id in request.FILES:
                img = request.FILES[image_id]
                filename = sku_id + '.' + splitext(img.name)
                img.name = filename
            else:
                img = None

            try:
                sku = skus.objects.get(SKU_ID=sku_id)
                sku.Color = color
                if img is not None:
                    sku.Picture = img
                print(img)
                sku.save()
                storeds = Stored.objects.filter(sku=sku)
                for size in sizes:
                    try:
                        stored = storeds.get(Size=size)
                        stored.stored = int(request.POST[size+"_"+str(i)])
                        stored.save()
                        storeds.exclude(Size=size)
                    except:
                        stored = Stored(sku=sku, Size=size, stored=int(request.POST[size+"_"+str(i)]))
                        stored.save()
                storeds.delete()

            except:
                sku = SKU(SKU_ID=sku_id, Color=color, Picture=img, Product=product)
                sku.save()
                for size in sizes:
                    stored = Stored(sku=sku, Size=size, stored=int(request.POST[size + "_" + str(i)]))
                    stored.save()
            skus = skus.exclude(SKU_ID=sku_id)
        skus.delete()

        return redirect('sprofile')
        '''
        for i in range(num):
            sku_id = product.ID + request.POST["id_"+str(i)]
            str = 'image_' + str(i)
            if str in request.FILES:
                img = request.FILES[str]
                filename = sku_id + '.' + splitext(img.name)
                img.name = filename
            else:
                img = None

            try:
                old = sku.get(SKU_ID=sku_id)
                if img is not None:
                    old.Picture = img
                    old.save()
            except:
                new = SKU(SKU_ID=sku_id, Product=product, Color=c, Picture=img)
                new.save()
                for s in sizes:
                    stored = Stored(sku=new, Size=s, stored=0)
                    stored.save()
            sku = sku.exclude(SKU_ID=sku_id)
        sku.delete()

        sku = SKU.objects.filter(Product=product)
        for Sku in sku:
            stored = Stored.objects.filter(sku=Sku)
            for size in sizes:
                num_id = Sku.Color + "_" + size + "_stored"
                num = request.POST[num_id]
                try:
                    s = stored.get(Size=size)
                    s.stored = num
                except:
                    s = Stored(sku=Sku, Size=size, stored=num)
                s.save()
        return redirect('sprofile')
        '''

    product = Product.objects.get(ID=product_ID)
    skus = SKU.objects.filter(Product=product)
    stored = Stored.objects.filter(sku=skus[0])

    size_selected = []
    for s in stored:
        size_selected.append(s.Size)

    style_list = []
    for sku in skus:
        style = Style(sku)
        style_list.append(style.dict)

    style_json = json.dumps(style_list)
    print(style_json)
    genre_choices = Product.GENRE_CHOICES
    category_choices = Product.CATEGORY_CHOICES
    color_choices = SKU.COLOR_CHOICES
    size_choices = Stored.SIZE_CHOICES

    context = {'product': product,  'size_selected': size_selected, 'genre': genre_choices, 'json_style': style_json,
               'category': category_choices, 'color': color_choices, 'size': size_choices, 'style_list': style_list}
    return render(request, 'supplier_editproduct.html', context)

class Style():
    def __init__(self, sku):
        self.stores = Stored.objects.filter(sku=sku)
        self.sku = sku
        self.image_url = self.get_image_url(self.sku.Picture.url)
        self.dict = self.to_dict()

    def get_image_url(self,url):
        url = unquote(url, encoding='UTF-8')
        return url

    def sku_id_process(self):
        spu_id = self.sku.Product.ID
        sku_id = self.sku.SKU_ID
        return sku_id.replace(spu_id, "")


    def to_dict(self):
        style = dict()
        style["sku_id"] = self.sku_id_process()
        style["color"] = self.sku.Color
        style["image_url"] = self.image_url
        for s in Stored.SIZE_CHOICES:

            for stored in self.stores:
                if stored.Size == s[0]:
                    style[s[0]] = stored.stored

                    break
                else:
                    style[s[0]] = 0
        return style

def sordertrace(request, order_ID):
    if 'supplier_id' not in request.session:
        return redirect('slogin')
    else:
        order = Order.objects.get(ID=order_ID)
        details = Order_Detail.objects.filter(ID=order_ID)
        choices = ['準備中', '已出貨', '已到貨', '取消', '完成']
        context = {'order': order, 'details': details, 'choices': choices}
        return render(request, 'supplier_order_trace.html', context)

def supdateorder(request):
    if 'supplier_id' not in request.session:
        return redirect('slogin')
    elif request.POST:
        #print(request.POST)
        order_ID = request.POST['order_ID']
        order = Order.objects.get(ID=order_ID)
        if 'agree' in request.POST:
            #print("agree")
            order.State = "取消"
            order.Remark = order.Remark + "\n" + "申請取消獲准"
        elif 'disagree' in request.POST:
            #print("disagree")
            order.State = "準備中"
            order.Remark = "申請取消遭拒"
        elif 'save' in request.POST:
            #print("save")
            new_state = request.POST['STATE_CHOICES']
            if new_state == "取消":
                print("取消")
                cancel_description = request.POST['cancel_description']
                order.Remark = cancel_description
            order.State = new_state
            order.save()

    return redirect('sprofile')

# ************************* Functions ***************************** #
def splitext(file):
    filename = file.split('.')
    return filename[-1]
def create_product_id(supplier):
    num = 0
    try:
        num = len(Product.objects.filter(Brand=supplier))
        num += 1
    except:
        num += 1
    return '{0:012d}'.format(num)
def hashpwd(pwd):
    salt = bcrypt.gensalt()
    hashed_pwd = bcrypt.hashpw(pwd.encode('utf-8'), salt)
    return salt,hashed_pwd

#有問題rerturn True
def check_id(str):
    list = [1, 2, 1, 2, 1, 2, 4, 1]
    serial_list = []
    new_list = []

    for c in str:
        serial_list.append(int(c))
        if not c.isnumeric():
            return True
            break

    if len(serial_list) != 8:
        return True

    for i in range(8):
        temp = serial_list[i] * list[i]
        new_list.append(int(temp / 10) + int(temp % 10))

    s = sum(new_list)
    if s % 10 != 0 or (serial_list[6] == 7 and (s - new_list[6] % 10 == 0 or s - new_list[6] % 10 == 9)):
        return True

    return False
def check_name(str):
    if str == "":
        return True
    return False
def check_email(str):
    mail = re.compile(r"[^@]+@[^@]+\.[^@]+")
    return not mail.match(str)
def check_exist(str):
    try:
        if len(Supplier.objects.filter(S_ID=str)) > 0:
            return True
        else:
            return False
    except:
        return False
def check_password(str):
    eight_char = False
    has_Num = False
    has_Char = False
    for c in str:
        if c.isnumeric():
            has_Num = True
            break

    for c in str:
        if c.isalpha():
            has_Char = True
            break

    if len(str) >= 8:
        eight_char = True

    return not(eight_char and has_Char and has_Num)
def check_pwd_match(pwd, c_pwd):
    if pwd != c_pwd:
        return True
    return False
def check_phone(str):
    phone = re.compile(r"^09+\d{8}")
    return not phone.match(str)




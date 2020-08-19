from django.shortcuts import render, redirect
from django.http import HttpResponse
import re
from user.models import User, Address
from goods.models import GoodsSKU
from django.urls import reverse
from django.views.generic import View
from django.conf import settings
from itsdangerous import SignatureExpired
from itsdangerous import TimedJSONWebSignatureSerializer as Serialize
from django.core.mail import send_mail
from celery_tasks.tasks import send_register_active_email
from django.contrib.auth import authenticate, login, logout
from utils.mixin import LoginRequiredMixin
from django_redis import get_redis_connection
from order.models import OrderInfo, OrderGoods
from django.core.paginator import Paginator


# Create your views here.
class RegistView(View):
    def get(self, request):
        return render(request, 'register.html')

    def post(self, request):
        # 1. 接收数据
        username = request.POST.get('user_name')
        password = request.POST.get('pwd')
        repassword = request.POST.get('cpwd')
        email = request.POST.get('email')
        allow = request.POST.get('allow')

        # 2. 数据校验
        if not all([username, password, repassword, email]):
            return render(request, 'regsister.html', {'errmsg': '数据不完整'})

        if password != repassword:
            return render(request, 'register.html', {'errmsg': '两次密码不一致'})

        if not re.match(r'^[a-z0-9][\w.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$',
                        email):
            return render(request, 'register.html', {'errmsg': '邮箱格式错误'})

        if allow != 'on':
            return render(request, 'register.html', {'errmsg': '请同意协议'})

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            user = None

        if user:
            return render(request, 'register.html', {'errmsg': '用户名已存在'})

        # 3. 业务处理
        user = User.objects.create_user(username, email, password)
        # 取消默认的账户激活
        user.is_active = 0
        user.save()
        # 加密激活信息
        serialize = Serialize(settings.SECRET_KEY, 3600)
        info = {'confirm': user.id}
        token = serialize.dumps(info)
        token = token.decode('utf8')
        # 发送邮件
        send_register_active_email.delay(email, username, token)

        # 4. 返回应答
        url = reverse('goods:index')
        return redirect(url)


class ActiveView(View):
    def get(self, request, token):
        serialize = Serialize(settings.SECRET_KEY, 3600)
        try:
            info = serialize.loads(token)
            user_id = info['confirm']
            user = User.objects.get(id=user_id)
            user.is_active = 1
            user.save()
        except SignatureExpired as e:
            return HttpResponse('链接已过期')

        return redirect(reverse('user:login'))


class LoginView(View):
    def get(self, request):
        # 判断是否有记住用户名
        if 'username' in request.COOKIES:
            username = request.COOKIES.get('username')
            checked = 'checked'
        else:
            username = ''
            checked = ''
        return render(request, 'login.html', {
            'username': username,
            'checker': checked
        })

    def post(self, request):
        # 1. 接收数据
        username = request.POST.get('username')
        password = request.POST.get('pwd')

        # 2. 数据校验
        if not all([username, password]):
            return render(request, 'login.html', {'errmsg': '数据不完整'})

        user = authenticate(username=username, password=password)
        if user is not None:
            # 如果用户密码匹配
            if user.is_active:
                # 如果用户已激活，登陆
                login(request, user)
                # 修改跳转地址,第二个参数为默认值
                # 第一个参数next为login_require传递的参数，为登陆前的那个页面
                next_url = request.GET.get('next', reverse('goods:index'))
                response = redirect(next_url)
                remember = request.POST.get('remember')
                if remember == 'on':
                    # 如果记住账号，传cookies
                    response.set_cookie('username',
                                        username,
                                        max_age=7 * 24 * 3600)
                else:
                    response.delete_cookie('username')

                return response
            else:
                # 如果未激活
                return render(request, 'login.html', {'errmsg': '账户未激活'})
        else:
            # 账户密码不匹配
            return render(request, 'login.html', {'errmsg': '账户密码不匹配'})


class LogoutView(View):
    def get(self, request):
        logout(request)
        return redirect(reverse('goods:index'))


class UserInfoView(LoginRequiredMixin, View):
    def get(self, request):
        # 1. 获取用户的个人信息
        user = request.user
        address = Address.objects.get_default_address(user)
        # 2. 获取用户的浏览记录
        # 2.1get_redis_connection 方法是django自带地链接redis数据库地方法。 其参数为settings.py中定义的redis数据库名
        con = get_redis_connection('default')
        history_key = 'history_%d' % user.id
        # 2.2 获取最新浏览的5个商品地信息
        sku_ids = con.lrange(history_key, 0, 4)
        # 2.3 从数据库查询用户浏览的具体商品信息
        goods_li = []
        for id in sku_ids:
            goods = GoodsSKU.objects.get(id=id)
            goods_li.append(goods)

        content = {'page': 'user', 'address': address, 'goods_li': goods_li}
        return render(request, 'user_center_info.html', content)


class UserOrderView(LoginRequiredMixin, View):
    def get(self, request, page):
        # 获取用户的订单信息
        user = request.user
        orders = OrderInfo.objects.filter(user=user).order_by('-create_time')
        for order in orders:
            order_skus = OrderGoods.objects.filter(order_id=order.order_id)
            for order_sku in order_skus:
                # 计算小计
                amount = order_sku.count*order_sku.price
                order_sku.amount = amount
            order.status_name = OrderInfo.ORDER_STATUS[order.order_status]
            # 动态添加属性
            order.order_skus = order_skus

        # 分页
        paginator = Paginator(orders, 1)
        # 获取对应页码的内容
        # 判断页码
        try:
            page = int(page)
        except Exception:
            page = 1
        if page > paginator.num_pages:
            page = 1
        order_page = paginator.page(page)
        # 3.3 编辑页码
        # ① 页码总数小于5，显示全部页码
        # ② 当前页小于3，显示1-5
        # ③ 当前页是最后三页，显示最后五页
        # ④ 其他情况，显示当前页和前后两页
        num_pages = paginator.num_pages
        if num_pages < 5:
            pages = range(1, num_pages+1)
        elif page < 3:
            pages = range(1, 6)
        elif num_pages - page <= 2:
            pages = range(num_pages-4, num_pages+1)
        else:
            pages = range(page-2, page+3)
            
        # 组织上下文
        context = {
            'order_page': order_page,
            'pages': pages,
            'page': 'order',

        }

        return render(request, 'user_center_order.html', context)


class UserAddressView(LoginRequiredMixin, View):
    def get(self, request):
        # 获取用户的默认收货地址
        user = request.user
        address = Address.objects.get_default_address(user)
        # try:
        #     address = Address.objects.get(user=user, is_default=True)
        # except Address.DoesNotExist:
        #     address = None

        return render(request, 'user_center_site.html', {
            'page': 'address',
            'address': address
        })

    # 添加地址
    def post(self, request):
        # 1. 接收数据
        receiver = request.POST.get('receiver')
        addr = request.POST.get('addr')
        zip_code = request.POST.get('zip_code')
        phone = request.POST.get('phone')

        # 2. 校验数据
        if not all([receiver, addr, phone]):
            return render(request, 'user_center_site.html', {
                'page': 'address',
                'errmsg': '数据不完整'
            })

        if not re.match(r'^1[3|4|5|7|8][0-9]{9}$', phone):
            return render(request, 'user_center_site.html', {
                'page': 'address',
                'errmsg': '电话号码不正确'
            })

        # 3. 业务处理：添加地址
        # 如果已存在默认地址，新添的地址不作为默认地址
        user = request.user
        address = Address.objects.get_default_address(user)
        # try:
        #     address = Address.objects.get(user=user, is_default=True)
        # except Address.DoesNotExist:
        #     address = None

        if address:
            is_default = False
        else:
            is_default = True

        Address.objects.create(user=user,
                               receiver=receiver,
                               addr=addr,
                               zip_code=zip_code,
                               phone=phone,
                               is_default=is_default)
        # 4. 返回应答
        return redirect(reverse('user:address'))
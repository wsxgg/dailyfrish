from django.shortcuts import render, redirect
from django.views.generic import View
from django.urls import reverse
from django_redis import get_redis_connection
from django.http import JsonResponse

from user.models import Address
from goods.models import GoodsSKU
from order.models import OrderInfo, OrderGoods

from utils.mixin import LoginRequiredMixin
from datetime import datetime
from django.db import transaction

from alipay import AliPay
from django.conf import settings
import os

# Create your views here.
"""提交订单页面 /order/place"""
class OrderPlaceView(LoginRequiredMixin, View):
    # 提交订单页面
    def post(self, request):
        user = request.user
        # 1. 获取参数
        sku_ids = request.POST.getlist('sku_ids')
        # 2. 校验参数
        if not sku_ids:
            # 如果没有商品传递，跳转至购物车主页
            return redirect(reverse('cart:show'))
        conn = get_redis_connection('default')
        cart_key = 'cart_%d' % user.id
        # 3. 遍历sku_ids，获取用户需要购买的商品信息
        skus = []
        total_count = 0
        total_price = 0
        for sku_id in sku_ids:
            # 获取商品信息
            sku = GoodsSKU.objects.get(id=sku_id)
            # 获取用户索要购买的商品数量
            count = conn.hget(cart_key, sku_id)
            # 计算商品小计
            amount = sku.price*int(count)
            # 动态给sku增加属性
            sku.count = int(count)
            sku.amount = amount
            # 追加到列表
            skus.append(sku)
            # 递加商品总件数和总价格
            total_count += int(count)
            total_price += amount

        # 实际开发运费有一个子系统，单独有一张运费表，这里写死运费10元
        transit_price = 10

        # 实际付款
        total_pay = total_price + transit_price

        # 获取用户的收件地址
        addrs = Address.objects.filter(user=user)

        # 拼接所有sku_id的字符串
        sku_ids = ','.join(sku_ids)

        # 组织上下文
        context = {
            'skus': skus,
            'total_count': total_count,
            'total_price': total_price,
            'transit_price': transit_price,
            'total_pay': total_pay,
            'addrs': addrs,
            'sku_ids': sku_ids,
        }

        # 返回页面
        return render(request, 'place_order.html', context)

"""订单创建 /order/commit """
# 前端传递的参数：地址id， 支付方式， 用户购买的商评id字符串
class OrderCommitView(View):
    # 订单创建
    @transaction.atomic
    def post(self, request):
        user = request.user
        # 判断用户是否登陆
        if not user.is_authenticated:
            return JsonResponse({'res': 0, 'errmsg': '请登录'})

        # 1. 接收参数
        addr_id = request.POST.get('addr_id')
        pay_method = request.POST.get('pay_method')
        sku_ids = request.POST.get('sku_ids')

        # 2. 校验参数
        # 2.1 校验完整性
        if not all([addr_id, pay_method, sku_ids]):
            return JsonResponse({'res': 1, 'errmsg': '数据不完整'})
        # 2.2 校验支付方式
        if pay_method not in OrderInfo.PAY_METHODS.keys():
            return JsonResponse({'res': 2, 'errmsg': '支付方式错误'})
        # 2.3 校验地址
        try:
            addr = Address.objects.get(id=addr_id)
        except Address.DoesNotExist:
            return JsonResponse({'res': 3, 'errmsg': '地址非法'})



        # TODO: 3. 创建订单核心业务
        #  TODO: 向df_order_info表中添加一条记录. 此时需要该数据表的所有数据
        #  组织缺少的参数
        #  ① 订单id： 2020421231800+用户id
        order_id = datetime.now().strftime('%Y%m%d%H%M%S')+str(user.id)
        #  ② 运费
        transit_price = 10
        #  ③ 总数目和总金额
        total_count = 0
        total_price = 0

        """ 设置事务保存点 """
        save_id = transaction.savepoint()

        try:
            #  添加订单记录
            order = OrderInfo.objects.create(
                order_id=order_id,
                user=user,
                addr=addr,
                pay_method=pay_method,
                total_count=total_count,
                total_price=total_price,
                transit_price=transit_price,
            )

            # TODO: 用户订单中有多少商品就向df_order_goods表中加入几条数据
            sku_ids = sku_ids.split(',')  # 拆分商品id字符串
            # 遍历商评id
            for sku_id in sku_ids:
                for i in range(2):
                    try:
                        sku = GoodsSKU.objects.get(id=sku_id)
                    except:
                        # 如果sku_id不存在，数据库回滚并退出
                        transaction.savepoint_rollback(save_id)
                        return JsonResponse({'res': 4, 'errmsg': '商品不存在'})
                    # 添加至订单商品表，需要该表的所有数据
                    # 组织缺少的参数
                    # ① 商品数目
                    conn = get_redis_connection('default')
                    cart_key = 'cart_%d' % user.id
                    count = conn.hget(cart_key, sku.id)

                    # TODO: 在向数据库添加数据时，先判断商品库存
                    if int(count) > sku.stock:
                        # 如果商品数量超出库存，数据库回滚并退出
                        transaction.savepoint_rollback(save_id)
                        return JsonResponse({'res': 6, 'errmsg': '商品库存不足'})

                    # 更新商品的库存和销量
                    # 这是原本的
                    # sku.stock -= int(count)
                    # sku.sales += int(count)
                    # sku.save()
                    # 这是添加乐观锁的
                    orgin_stock = sku.stock
                    new_stock = orgin_stock - int(count)
                    new_sales = sku.sales + int(count)
                    res = GoodsSKU.objects.filter(id=sku_id, stock=orgin_stock).update(stock=new_stock, sales=new_sales)
                    if res == 0:
                        if i == 2:
                            # 如果是尝试的第三次，还是失败，回滚并退出
                            transaction.savepoint_rollback(save_id)
                            return JsonResponse({'res': 7, 'errmsg': '下单失败'})
                        continue
                
                    # 向数据表添加记录
                    OrderGoods.objects.create(
                        order=order,
                        sku=sku,
                        count=count,
                        price=sku.price,
                    )

                    # 累加计算订单商品的总数目和总价格
                    amount = sku.price*int(count)
                    total_count += int(count)
                    total_price += amount

                    # 跳出循环
                    break
            
            
            # 更新订单信息表中的商品总数目和总价格
            order.total_count = total_count
            order.total_price = total_price
            order.save()
        except Exception:
            transaction.savepoint_rollback(save_id)
            return JsonResponse({'res': 7, 'errmsg': '添加订单失败'})

        # 删除购物车里对应的记录
        conn.hdel(cart_key, *sku_ids)

        # 返回应答
        return JsonResponse({'res': 5, 'message': '添加成功'})


"""订单支付 """
# 前端传递的参数： 订单id
class OrderPayView(View):
    def post(self, request):
        # 1. 用户是否登陆
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'res': 0, 'errmsg': '用户未登陆'})

        # 2. 接收参数
        order_id = request.POST.get('order_id')

        # 3. 校验参数
        if not order_id:
            return JsonResponse({'res': 1, 'errmsg': '无效订单id'})
        
        try:
            order = OrderInfo.objects.get(order_id=order_id, user=user, pay_method=3, order_status=1)
        except OrderInfo.DoesNotExist:
            return JsonResponse({'res': 2, 'errmsg': '订单错误'})

        # 4. 业务处理：使用python sdk调用支付宝的支付接口
        # 4.1 初始化
        app_private_key_string = open(os.path.join(settings.BASE_DIR, 'apps/order/app_private_key.pem')).read()
        alipay_public_key_string = open(os.path.join(settings.BASE_DIR, 'apps/order/alipay_public_key.pem')).read()
        alipay = AliPay(
            appid="2016102400748506",
            app_notify_url=None,  # 默认回调url
            app_private_key_string=app_private_key_string,
            alipay_public_key_string=alipay_public_key_string,   # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
            sign_type="RSA2",  # RSA 或者 RSA2
            debug=True,  # 默认False  True为沙箱测试
        )
        # 4.2 调用支付接口
        total_amount = order.total_price + order.transit_price
        # 电脑网站支付，需要跳转到https://openapi.alipay.com/gateway.do? + order_string
        # 电脑网站(沙箱测试)支付，需要跳转到https://openapi.alipaydev.com/gateway.do? + order_string
        order_string = alipay.api_alipay_trade_page_pay(
            out_trade_no=order_id,
            total_amount=str(total_amount),    # 支付总金额
            subject='天天生鲜%s' % order_id,
            return_url=None,
            notify_url=None,  # 可选, 不填则使用默认notify url
        )

        # 5. 返回应答
        pay_url = 'https://openapi.alipaydev.com/gateway.do?' + order_string
        return JsonResponse({'res': 3, 'pay_url': pay_url})


"""查看订单支付结果"""
# 前端传递参数： 订单id
class OrderCheckView(View):
    def post(self, request):
        # 1. 用户是否登陆
        user = request.user
        if not user.is_authenticated:
            print('0')
            return JsonResponse({'res': 0, 'errmsg': '用户未登陆'})

        # 2. 接收参数
        order_id = request.POST.get('order_id')

        # 3. 校验参数
        if not order_id:
            print('1')
            return JsonResponse({'res': 1, 'errmsg': '无效订单id'})
        
        try:
            order = OrderInfo.objects.get(order_id=order_id, user=user, pay_method=3, order_status=1)
        except OrderInfo.DoesNotExist:
            print('2')
            return JsonResponse({'res': 2, 'errmsg': '订单错误'})

        # 4. 业务处理：使用python sdk调用支付宝的支付接口
        # 4.1 初始化
        app_private_key_string = open(os.path.join(settings.BASE_DIR, 'apps/order/app_private_key.pem')).read()
        alipay_public_key_string = open(os.path.join(settings.BASE_DIR, 'apps/order/alipay_public_key.pem')).read()
        alipay = AliPay(
            appid="2016102400748506",
            app_notify_url=None,  # 默认回调url
            app_private_key_string=app_private_key_string,
            alipay_public_key_string=alipay_public_key_string,   # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
            sign_type="RSA2",  # RSA 或者 RSA2
            debug=True,  # 默认False  True为沙箱测试
        )
        # 4.2 调用支付宝查询接口
        while True:
            response = alipay.api_alipay_trade_query(order_id)
            print(response)
            # response = {
            #     "trade_no": "2017032121001004070200176844",       # 支付宝交易号
            #     "code": "10000",          # 接口调用是否成功的编码
            #     "invoice_amount": "20.00",
            #     "open_id": "20880072506750308812798160715407",
            #     "fund_bill_list": [
            #       {
            #         "amount": "20.00",
            #         "fund_channel": "ALIPAYACCOUNT"
            #       }
            #     ],
            #     "buyer_logon_id": "csq***@sandbox.com",
            #     "send_pay_date": "2017-03-21 13:29:17",
            #     "receipt_amount": "20.00",
            #     "out_trade_no": "out_trade_no15",
            #     "buyer_pay_amount": "20.00",
            #     "buyer_user_id": "2088102169481075",
            #     "msg": "Success",
            #     "point_amount": "0.00",
            #     "trade_status": "TRADE_SUCCESS",      # 订单状态 
            #     "total_amount": "20.00"
            # }
            code = response.get('code')

            if code == '10000' and response.get('trade_status') == 'TRADE_SUCCESS':
                # 支付成功
                # 获取支付宝交易号
                trade_no = response.get('trade_no')
                # 更新订单的状态
                order.trade_no = trade_no
                order.order_status = 4  # 修改成待评价状态
                order.save()
                # 返回结果
                return JsonResponse({'res': 3, 'message': '支付成功'})
            elif code == '40004' or (code == '10000' and response.get('trade_status') == 'WAIT_BUYER_PAY'):
                # 业务处理失败，一会就会成功
                # 等待买家付款
                import time
                time.sleep(5)
                continue
            else:
                # 订单错误
                print('4')
                return JsonResponse({'res': 4, 'errmsg': '支付失败'})


'''评价'''
# 前端传递参数：
class CommentView(View):
    # 获取评论页面
    def get(self, request, order_id):
        user = request.user
        
        # 校验数据
        if not order_id:
            return redirect(reverse('user:order'))
        
        try:
            order = OrderInfo.objects.get(order_id=order_id, user=user)
        except OrderInfo.DoesNotExist:
            return redirect(reverse('user:order'))
        
        # 获取订单的状态标题,并且动态添加属性
        order.status_name = OrderInfo.ORDER_STATUS[order.order_status]

        # 获取商品的信息
        order_skus = OrderGoods.objects.filter(order_id=order_id)
        for order_sku in order_skus:
            # 计算商品小计，并动态添加属性
            amount = order_sku.price*order_sku.count
            order_sku.amount = amount
        order.order_skus = order_skus

        # 返回模板文件
        return render(request, 'order_comment.html', {'order': order})



    # 处理评论内容
    def post(self, request, order_id):
        user = request.user
        # 校验数据
        if not order_id:
            return redirect(reverse('user:order'))
        
        try:
            order = OrderInfo.objects.get(order_id=order_id, user=user)
        except OrderInfo.DoesNotExist:
            return redirect(reverse('user:order'))

        # 获取评论条数
        total_count = request.POST.get('total_count')
        total_count = int(total_count)

        for i in range(1, total_count+1):
            # 获取评论商品的ID
            sku_id = request.POST.get('sku_%d' % i)
            # 获取评论商品的内容
            content = request.POST.get('content_%d' % i, '')        # 第二个参数指默认为空

            try:
                order_goods = OrderGoods.objects.get(order=order, sku_id=sku_id)
            except OrderGoods.DoesNotExist:
                continue

            # 保存对应评论
            order_goods.comment = content
            order_goods.save()
        
        # 保存订单状态为已完成
        order.order_status = 5
        order.save()

        return redirect(reverse('user:order', kwargs={'page': 1}))


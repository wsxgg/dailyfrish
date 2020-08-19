from django.shortcuts import render
from django.http import JsonResponse
from goods.models import GoodsSKU
from django_redis import get_redis_connection
from django.views.generic import View
from utils.mixin import LoginRequiredMixin
from goods.models import GoodsSKU


# Create your views here.
class CartAddView(View):
    def post(self, request):
        user = request.user
        # 判断用户是否哦登陆
        if not user.is_authenticated:
            return JsonResponse({'err': 0, 'errmsg': '请登录'})
        # 1.1 获取当前商品的sku_id和count
        sku_id = request.POST.get('sku_id')
        count = request.POST.get('count')

        # 2. 校验获取值
        # 2.1 校验数据是否完整
        if not all([sku_id, count]):
            return JsonResponse({'res': 1, 'errmsg': '数据不完整'})
        # 2.2 校验count是否输入正确
        try:
            count = int(count)
        except Exception:
            return JsonResponse({'res': 2, 'errnsg': '商品数目出错'})
        # 2.3 校验商品是否存在
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except Exception:
            return JsonResponse({'res': 3, 'errmsg': '商品不存在'})

        # 3. 业务处理，添加购物车
        conn = get_redis_connection('default')
        cart_key = 'cart_%d' % user.id
        # 3.1 获取该商评的键，判断是否已经存在于购物车,分别计算商品总数
        cart_count = conn.hget(cart_key, sku_id)
        #  如果不存在，返回None
        if cart_count:
            count += int(cart_count)
        else:
            count = count
        # 3.2 判断商品库存
        if count > sku.stock:
            return JsonResponse({'res': 4, 'errmsg': '商品库存不足'})

        # 3.3 修改购物车数据库对应商品的值
        conn.hset(cart_key, sku_id, count)

        # 3.4 返回页面显示数据库的条目数
        total_count = conn.hlen(cart_key)


        # 4. 返回应答
        return JsonResponse({'res': 5, 'message': '添加成功', 'total_count': total_count})

class CartInfoView(LoginRequiredMixin, View):
    # 购物车页面显示
    def get(self, request):
        # 获取用户购物车页面所需信息
        # 获取登陆用户
        user = request.user
        # 获取用户购物车商品的信息
        conn = get_redis_connection('default')
        cart_key = 'cart_%d' % user.id
        cart_dict = conn.hgetall(cart_key)  # 返回值是一个字典{'商品id1'：商品数量1, '商品id2':商品数量2, 。。。}

        skus = []
        total_count = 0
        total_price = 0
        for sku_id, count in cart_dict.items():
            sku = GoodsSKU.objects.get(id=sku_id)
            # 计算商品小计
            amount = sku.price*int(count)   # 单个商品小计
            total_count += int(count)        # 所有商品的个数
            total_price += amount       # 所有商品总价
            # 动态给sku增加属性
            sku.amount = amount
            sku.count = int(count)
            skus.append(sku)
        
        # 组织上下文
        context = {
            'total_count': total_count,
            'total_price': total_price,
            'skus': skus,
        }

        return render(request, 'cart.html', context)

'''/cart/update'''
class CartUpdateView(View):
    # 购物车记录跟新
    def post(self, request):
        # 判断用户登陆
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'res': 0, 'errmsg': '用户未登录'})
        # 1. 接收数据
        sku_id = request.POST.get('sku_id')
        count = request.POST.get('count')

        # 2. 校验获取值
        # 2.1 校验数据是否完整
        if not all([sku_id, count]):
            return JsonResponse({'res': 1, 'errmsg': '数据不完整'})
        # 2.2 校验count是否输入正确
        try:
            count = int(count)
        except Exception:
            return JsonResponse({'res': 2, 'errnsg': '商品数目出错'})
        # 2.3 校验商品是否存在
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except Exception:
            return JsonResponse({'res': 3, 'errmsg': '商品不存在'})

        # 3. 业务处理：更新购物车记录
        # 3.1 连接redis数据库，拼接出cart_id
        conn = get_redis_connection('default')
        cart_key = 'cart_%d' % user.id  
        # 3.2 判断是否超出库存
        if count > sku.stock:
            return JsonResponse({'res': 4, 'errmsg': '超出库存'})
        # 3.3 更新购物车
        conn.hset(cart_key, sku_id, count)
        # 3.4 计算购物车商品的总件数
        total_count = 0
        vals = conn.hvals(cart_key)
        for val in vals:
            total_count += int(val)


        # 4. 返回应答
        return JsonResponse({'res': 5, 'message': '更新成功', 'total_count': total_count})

'''/cart/delete'''
class CartDeleteView(View):
    def post(self, request):
        user = request.user
        # 判断用户是否登陆
        if not user.is_authenticated:
            return JsonResponse({'res': 0, 'errmsg': '请登录'})
        
        # 获取前端换来的数据
        sku_id = request.POST.get('sku_id')

        # 校验数据
        if not sku_id:
            return JsonResponse({'res': 1, 'errmsg': '无效的商品id'})
        
        # 校验商品是否存在
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except Exception:
            return JsonResponse({'res': 2, 'errmsg': '商品不存在'})

        # 业务处理，删除购物车
        conn = get_redis_connection('default')
        cart_key = 'cart_%d' % user.id

        conn.hdel(cart_key, sku_id)

        # 计算商品总数
        total_count = 0
        for val in conn.hvals(cart_key):
            total_count += int(val)

        # 返回应答
        return JsonResponse({'res': 3, 'message': '删除成功', 'total_count': total_count})

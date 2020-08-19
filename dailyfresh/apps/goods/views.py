from django.shortcuts import render, redirect
from django.views.generic import View
from goods.models import GoodsType, GoodsSKU, IndexGoodsBanner, IndexPromotionBanner, IndexTypeBanner
from django_redis import get_redis_connection
from django.core.cache import cache
from django.urls import reverse
from order.models import OrderGoods
from django.core.paginator import Paginator

# Create your views here.
class IndexView(View):
    def get(self, request):
        # 显示首页
        # 尝试获取缓存
        context = cache.get('index_page_data')
        if context is None:
            print('设置cache')
            # 1. 获取商品种类信息
            types = GoodsType.objects.all()
            # 2. 获取首页轮播图信息
            goods_banners = IndexGoodsBanner.objects.all().order_by('index')
            # 3. 获取首页促销活动信息
            promotion_banners = IndexPromotionBanner.objects.all().order_by('index')
            # 4. 获取首页分类商品展示信息
            for type in types:
                image_banner = IndexTypeBanner.objects.filter(type=type, display_type=1).order_by('index')
                title_banner = IndexTypeBanner.objects.filter(type=type, display_type=0).order_by('index')
                type.image_banner = image_banner
                type.title_banner = title_banner

            context = {
                'types': types,
                'goods_banners': goods_banners,
                'promotion_banners': promotion_banners,
            }
            cache.set('index_page_data', context, timeout=3600)
        # 5. 获取用户购物车中商品的数目
        user = request.user
        cart_count = 0
        if user.is_authenticated:
            conn = get_redis_connection('default')
            cart_key = 'cart_%d' % user.id
            cart_count = conn.hlen(cart_key)

        # 组织模板上下文
        context.update(cart_count=cart_count)

        return render(request, 'index.html', context)

class DetailView(View):
    def get(self, request, goods_id):
        # 详细页
        # 1. 检查货物id是否存在, 获取商品SKU
        try:
            sku = GoodsSKU.objects.get(id=goods_id)
        except GoodsSKU.DoesNotExist:
            return redirect(reverse('goods:index'))

        # 2. 获取商品分类信息
        types = GoodsType.objects.all()
        # 3. 获取商品的评论信息
        sku_orders = OrderGoods.objects.filter(sku=sku).exclude(comment='')
        # 4. 获取新品推荐
        new_skus = GoodsSKU.objects.filter(type=sku.type).order_by('-create_time')[:2]
        # 5. 获取同一SPU的其他商品规格
        same_spu_sku = GoodsSKU.objects.filter(goods=sku.goods).exclude(id=goods_id)
        # 5. 获取用户购物车中商品的数目
        user = request.user
        cart_count = 0
        if user.is_authenticated:
            conn = get_redis_connection('default')
            cart_key = 'cart_%d' % user.id
            cart_count = conn.hlen(cart_key)

            # 添加用户的历史浏览记录 redis-list
            # 1.先移除原有的此条记录
            # conn = get_redis_connection('default')
            history_key = 'history_%d' % user.id
            conn.lrem(history_key, 0, goods_id)
            # 2.在左侧插入此条记录
            conn.lpush(history_key, goods_id)
            # 3.只保存五条历史纪录
            conn.ltrim(history_key, 0, 4)

        # 组织模板上下文
        context = {
            'sku': sku,
            'types': types,
            'sku_orders': sku_orders,
            'new_skus': new_skus,
            'same_spu_sku': same_spu_sku,
            'cart_count': cart_count,
        }

        return render(request, 'detail.html', context)


class ListView(View):
     # 种类id， 页码， 排序方式
    #  /list/种类id/页码？sort=排序方式
    def get(self, request, type_id, page):
        # 1. 获取该商品种类
        try:
            type = GoodsType.objects.get(id=type_id)
        except Exception:
            # 商品不存在
            return render(request, reverse('goods:index'))
        # 2. 获取所有商品分类
        types = GoodsType.objects.all()
        # 3. 获取当前页码的商品sku
        # 3.1 获取对应排序的sku
        sort = request.GET.get('sort')
        if sort == 'price':
            skus = GoodsSKU.objects.filter(type=type).order_by('price')
        elif sort == 'hot':
            skus = GoodsSKU.objects.filter(type=type).order_by('-sales')
        else:
            sort = 'default'
            skus = GoodsSKU.objects.filter(type=type).order_by('-id')
        # 3.2 对sku进行分页
        paginator = Paginator(skus, 1)
        try:
            page = int(page)
        except Exception:
            page = 1
        if page > paginator.num_pages:
            page = 1
        skus_page = paginator.page(page)
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
        # 4. 获取最新商品
        new_skus = GoodsSKU.objects.filter(type=type).order_by('-create_time')[:2]
        # 5. 获取购物车
        user = request.user
        cart_count = 0
        if user.is_authenticated:
            conn = get_redis_connection('default')
            cart_key = 'cart_%d' % user.id
            cart_count = conn.hlen(cart_key)

        # 组织模板上下文
        context = {
            'type': type,
            'types': types,
            'skus_page': skus_page,
            'new_skus': new_skus,
            'cart_count': cart_count,
            'sort': sort,
            'pages': pages,
        } 

        return render(request, 'list.html', context)
from django.urls import re_path, include
from cart.views import CartAddView, CartInfoView, CartUpdateView, CartDeleteView

urlpatterns = [
    re_path(r'^add$', CartAddView.as_view(), name='add'),       # 添加购物车
    re_path(r'^update$', CartUpdateView.as_view(), name='update'),  # 购物车记录更新
    re_path(r'^delete$', CartDeleteView.as_view(), name='delete'),
    re_path(r'^$', CartInfoView.as_view(), name='show'),    # 购物车界面
    
]

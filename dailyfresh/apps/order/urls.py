
from django.urls import re_path, include
from order.views import OrderPlaceView, OrderCommitView, OrderPayView, OrderCheckView, CommentView

urlpatterns = [
    re_path(r'^place$', OrderPlaceView.as_view(), name='place'),  # 付款页面
    re_path(r'^commit$', OrderCommitView.as_view(), name='commit'),  # 订单创建
    re_path(r'^pay$', OrderPayView.as_view(), name='pay'),      # 订单支付
    re_path(r'^check$', OrderCheckView.as_view(), name='check'),       # 订单支付结果
    re_path(r'^comment/(?P<order_id>.+)$', CommentView.as_view(), name='comment'),      # 订单评论

]

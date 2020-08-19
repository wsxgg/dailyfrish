
from django.urls import re_path, include
from user import views
from user.views import RegistView, ActiveView, LoginView, LogoutView, UserInfoView, UserOrderView, UserAddressView

urlpatterns = [

    re_path(r'^register$', RegistView.as_view(), name='register'),
    re_path(r'^active/(?P<token>.*)$', ActiveView.as_view(), name='active'),
    re_path(r'^login$', LoginView.as_view(), name='login'),
    re_path(r'^logout$', LogoutView.as_view(), name='logout'),
    re_path(r'^$', UserInfoView.as_view(), name='user'),
    re_path(r'^order/(?P<page>\d+)$', UserOrderView.as_view(), name='order'),
    re_path(r'^address$', UserAddressView.as_view(), name='address'),


]

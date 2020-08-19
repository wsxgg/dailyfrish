"""dailyfresh URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, re_path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    re_path(r'^search', include('haystack.urls')),
    re_path(r'^tinymce/', include('tinymce.urls')),
    re_path(r'^cart/', include(('cart.urls', "cart"), namespace='cart')),
    re_path(r'^order/', include(('order.urls', "order"), namespace='order')),
    re_path(r'^user/', include(('user.urls', "user"),  namespace='user')),
    re_path(r'^', include(('goods.urls', "goods"), namespace='goods')),


]

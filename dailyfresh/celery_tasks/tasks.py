# 使用方法：celery -A celery_tasks.tasks worker -l info -P eventlet 

from celery import Celery
from django.conf import settings
from django.core.mail import send_mail
from django.template import loader, RequestContext


import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dailyfresh.settings')
django.setup()

from goods.models import GoodsType, IndexGoodsBanner, IndexPromotionBanner, IndexTypeBanner

# 1. 定义一个Celery的实例对象
app = Celery('celery_tasks.tasks', broker='redis://192.168.152.156:6379/0')

# 2. 定义对应的处理函数
@app.task
def send_register_active_email(email, username, token):
    subject = '邮件主题'
    message = ''
    sender = settings.EMAIL_FROM
    receiver = [email]
    html_message = '<h1>%s,欢迎加入天天生鲜会员，请点击一下按钮激活用户</h1><a href="http://127.0.0.1:8000/user/active/%s">激活</a>' % (username, token)
    send_mail(subject, message, sender, receiver, html_message=html_message)

@app.task
def generate_static_index_html():
    # 产生首页静态页面
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

    # 组织模板上下文
    context = {
        'types': types,
        'goods_banners': goods_banners,
        'promotion_banners': promotion_banners,
    }

    # return render(request, 'index.html', context)
    # 1.加载模板文件
    temp = loader.get_template('static_index.html')
    # 2.模板渲染
    static_index_html = temp.render(context)
    # 3.生成静态页面
    save_path = os.path.join(settings.BASE_DIR, 'static/index.html')
    with open(save_path, 'w', encoding='utf-8') as f:
        f.write(static_index_html)



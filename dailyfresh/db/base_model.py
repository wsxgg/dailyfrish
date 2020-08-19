from django.db import models

class BaseModel(models.Model):
    # 定义抽象基类
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    update_time= models.DateTimeField(auto_now=True, verbose_name='修改时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记')

    class Meta:
        abstract = True
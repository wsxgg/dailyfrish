from django.db import models
from django.contrib.auth.models import AbstractUser
from db.base_model import BaseModel
# Create your models here.

class User(AbstractUser, BaseModel):
    # 用户表，继承AbstractUser的认证类
    class Meta:
        db_table = 'df_user'
        verbose_name = '用户'
        verbose_name_plural = verbose_name

class AddressManager(models.Manager):
    # 地址模型管理器类
    # 1. 改变原有的查询集结果

    # 2. 分装方法：
    def get_default_address(self, user):
        # 获取默认的用户收货地址，没有则返回None
        try:
            address = self.get(user=user, is_default=True)
        except self.model.DoesNotExist:
            address = None
        
        return address

class Address(BaseModel):
    # 收获地址类
    user = models.ForeignKey('User', verbose_name='所属用户', on_delete=models.CASCADE)
    receiver = models.CharField(max_length=20, verbose_name='收件人')
    addr = models.CharField(max_length=256, verbose_name='收货地址')
    zip_code = models.CharField(max_length=6, null=True, verbose_name='邮编')
    phone = models.CharField(max_length=11, verbose_name='联系方式')
    is_default = models.BooleanField(default=False, verbose_name='是否默认')

    objects = AddressManager()

    class Meta:
        db_table = 'df_address'
        verbose_name = '地址'
        verbose_name_plural = verbose_name



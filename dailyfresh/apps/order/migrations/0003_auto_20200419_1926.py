# Generated by Django 2.1 on 2020-04-19 11:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('order', '0002_auto_20200409_1223'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ordergoods',
            name='comment',
            field=models.CharField(default='', max_length=156, verbose_name='评论'),
        ),
    ]
# Generated by Django 2.1 on 2020-04-19 11:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('goods', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='goodssku',
            old_name='ctock',
            new_name='stock',
        ),
        migrations.AlterField(
            model_name='indexpromotionbanner',
            name='url',
            field=models.CharField(max_length=256, verbose_name='活动链接'),
        ),
    ]

from django.contrib import admin
from goods.models import GoodsType, IndexGoodsBanner, IndexTypeBanner, IndexPromotionBanner, GoodsSKU
from django.core.cache import cache

# Register your models here.
class BaseModelAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

        from celery_tasks.tasks import generate_static_index_html
        generate_static_index_html.delay()

        cache.delete('index_page_data')
    
    def delete_model(self, request, obj):
        super().delete_model(self, request, obj)

        from celery_tasks.tasks import generate_static_index_html
        generate_static_index_html.delay()

        cache.delete('index_page_data')


class IndexPromotionBannerAdmin(BaseModelAdmin):
    pass 
class IndexGoodsBannerAdmin(BaseModelAdmin):
    pass
class IndexTypeBannerAdmin(BaseModelAdmin):
    pass
class GoodsTypeAdmin(BaseModelAdmin):
    pass
class GoodsSKUAdmin(BaseModelAdmin):
    pass
admin.site.register(GoodsType, GoodsTypeAdmin)
admin.site.register(IndexTypeBanner, IndexTypeBannerAdmin)
admin.site.register(IndexGoodsBanner, IndexGoodsBannerAdmin)
admin.site.register(IndexPromotionBanner, IndexPromotionBannerAdmin)
admin.site.register(GoodsSKU, GoodsSKUAdmin)


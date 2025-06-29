from django.contrib import admin
from . models import Category,Product,Profile,Cart,Order,OrderItem
from django.utils.html import format_html

# Register your models here.
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'slug']
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'category', 'price', 'created_at']
    list_filter = ['category']
    prepopulated_fields = {'slug': ('title',)}

# @admin.register(Contact)
# class ContactAdmin(admin.ModelAdmin):
#     list_display = ['name', 'email', 'subject', 'sent_at']

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone']
    
@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'quantity', 'subtotal', 'added_at']
    


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id','user','phone','address','quantity','ordered_at')
    
    
# The `OrderItemInline` class is a TabularInline model in Django admin for managing order items with
# zero extra items.
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'product', 'quantity', 'total_price']
    list_filter = ['product']
    search_fields = ['product__title', 'order__confirmation_code']




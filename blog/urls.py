from django.urls import path
from . import views
from django.contrib.auth.views import PasswordChangeView, PasswordChangeDoneView
# from .views import contact_view
from .views import profile_view
from .views import add_selected_to_cart


urlpatterns = [
    path('register/',views.register, name="register"),
    path('login/',views.login, name="login"),
    path('home/', views.home, name="home"),
    path('logout/', views.logout, name='logout'),
    path('', views.shop, name="shop"),
    # path('contact/', contact_view, name='contact'),
    # path('about/',views.about,name="about"),
    
    path('shop/<int:id>', views.base_shop_detail, name="base_shop_detail"),
    path('search/', views.search_products, name='search_products'),
    
    #change password
    path('change-password/', views.change_password, name='change_password'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    
    #Forgot password
    path('reset-password/<str:token>/', views.reset_password, name='reset_password'),
    path('profile/', profile_view, name='profile'),
    
    #payment
    path('base_shop/', views.base_shop, name="base_shop"),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/<int:product_id>/', views.update_cart_quantity, name='update_cart_quantity'),
    path('cart/remove/<int:product_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/', views.view_cart, name='view_cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('process-checkout/', views.process_checkout, name='process_checkout'),
  
    path('esewa/payment/', views.esewa_payment, name='esewa_payment'),
    
    path('order/', views.place_order, name='place_order'),
    path('orders/', views.order_history, name='order_history'),
    path('order/confirm/<int:order_id>/', views.order_confirm, name='order_confirm'),  # ✅ certified confirmation URL
    
    path('download/invoice/<int:order_id>/', views.download_invoice, name='download-invoice'),

    
    path('order/remove/<int:order_id>/', views.remove_order, name='remove_order'),
    
    path('add-selected-to-cart/', add_selected_to_cart, name='add_selected_to_cart'),



    
]



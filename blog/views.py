from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpRequest, HttpResponse,JsonResponse
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.hashers import make_password
from django.contrib.auth import authenticate, login as auth_login, logout as django_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.utils.crypto import get_random_string
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from django.core.mail import send_mail
from django.conf import settings
from .models import Category,Product,Profile,Cart,Order,OrderItem
from .forms import (
    ForgotPasswordForm, ResetPasswordForm,
    UserUpdateForm, ProfileUpdateForm
)
from .utils import generate_token, verify_token
from django.utils import timezone
from django.views.decorators.csrf import csrf_protect
from django.core.paginator import Paginator
from django.db.models import Sum, F, FloatField
from .utils import verify_token
from django.contrib.auth import update_session_auth_hash
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
import logging
from django.views.decorators.http import require_POST
from django.utils.timezone import now
from django.db.models import Prefetch
# from xhtml2pdf import pisa
from django.template.loader import get_template
from io import BytesIO
from xhtml2pdf import pisa




# ----------------------- Auth Views -----------------------



logger = logging.getLogger(__name__)
def register(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip().lower()
        password1 = request.POST.get("password1", "").strip()
        password2 = request.POST.get("password2", "").strip()

        # === Validation ===
        if not all([username, email, password1, password2]):
            messages.error(request, "⚠️ All fields are required.")
            return redirect("register")

        try:
            validate_email(email)
        except ValidationError:
            messages.error(request, "📭 Invalid email format.")
            return redirect("register")

        if password1 != password2:
            messages.error(request, "❌ Passwords do not match.")
            return redirect("register")

        if len(password1) < 8:
            messages.error(request, "🔒 Password must be at least 8 characters.")
            return redirect("register")

        if User.objects.filter(username=username).exists():
            messages.error(request, "⚠️ Username already exists.")
            return redirect("register")

        if User.objects.filter(email=email).exists():
            messages.error(request, "⚠️ Email already in use.")
            return redirect("register")

        # === Create User ===
        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password1
            )
            Profile.objects.get_or_create(user=user)
        except Exception as e:
            logger.error(f"❌ Error creating user: {e}")
            messages.error(request, "An error occurred while creating your account.")
            return redirect("register")

        # === Prepare Welcome Email ===
        subject = "🎉 Welcome to MyShop!"
        login_url = "http://127.0.0.1:8000/login/"
        plain_message = f"""Hi {username},

Thanks for signing up with MyShop!

You can now log in and start exploring:
👉 {login_url}

Need help? Contact us at support@myshop.com.

Cheers,  
The MyShop Team
"""
        html_message = f"""
        <div style="font-family:'Segoe UI',sans-serif; color:#333;">
          <h2>👋 Hello {username},</h2>
          <p>Thanks for creating an account at <strong>MyShop</strong>!</p>
          <p>You can now log in and start shopping:</p>
          <p><a href="{login_url}" style="background:#4CAF50;color:white;padding:10px 20px;text-decoration:none;border-radius:5px;">Login Now</a></p>
          <br>
          <p>Need help? <a href="mailto:support@myshop.com">support@myshop.com</a></p>
          <p>– The MyShop Team</p>
        </div>
        """

        try:
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
                html_message=html_message
            )
            messages.success(request, "✅ Registration successful! A welcome email has been sent.")
        except Exception as e:
            logger.warning(f"📧 Email sending failed: {e}")
            messages.warning(request, "Registered successfully, but welcome email failed to send.")

        return redirect("login")

    return render(request, "register.html")



@csrf_protect
def login(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "").strip()

        # Field validation
        if not username or not password:
            messages.warning(request, "⚠️ Both fields are required.")
            return redirect("login")

        # Authenticate user
        user = authenticate(request, username=username, password=password)
        if user is not None:
            if user.is_active:
                auth_login(request, user)
                messages.success(request, f"✅ Welcome back, {user.username}!")
                return redirect("home")
            else:
                messages.error(request, "❌ This account is inactive. Please contact support.")
        else:
            messages.error(request, "❌ Invalid credentials. Please try again.")

        return redirect("login")

    # If GET request, render login page
    return render(request, "login.html")

@login_required(login_url='login')
def logout(request: HttpRequest) -> HttpResponse:
    """
    Securely logs out the authenticated user, logs the action,
    and redirects to the login page with a success message.
    """
    username = request.user.username
    django_logout(request)

    # Notify and log
    messages.success(request, "👋 You have been logged out successfully.")
    logger.info(f"🔒 User '{username}' logged out successfully.")

    return redirect("login")
# ----------------------- Home / Shop -----------------------


@login_required(login_url='login')
def home(request: HttpRequest) -> HttpResponse:
    """
    Display the home/dashboard page for authenticated users.

    Returns:
        HttpResponse: Rendered home page with user context.
    """
    context = {
        "user": request.user,
        "page_title": "Dashboard | MyShop"
    }
    return render(request, "home.html", context)



# @login_required(login_url='login')
def shop(request: HttpRequest) -> HttpResponse:
    """
    Display the list of all available products on the shop page,
    with optional pagination support.
    """
    product_queryset = Product.objects.all().order_by('-id')  # Most recent first
    paginator = Paginator(product_queryset, 12)  # Show 12 products per page

    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "product_count": paginator.count,
    }
    return render(request, "shop.html", context)




@login_required(login_url='login')
def base_shop_detail(request: HttpRequest, id: int) -> HttpResponse:
    """
    Display detailed view of a single product.

    Args:
        request (HttpRequest): The incoming HTTP request.
        id (int): The ID of the product to display.

    Returns:
        HttpResponse: The rendered product detail page.
    """
    product = get_object_or_404(Product, id=id)
    
    context = {
        "product": product,
        "page_title": f"{product.title} | Product Detail"
    }
    return render(request, "base_shop_detail.html", context)



@login_required(login_url='login')
def search_products(request):
    query = request.GET.get('query', '').strip()
    results = []

    if query:
        results = Product.objects.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(category__name__icontains=query)
        ).distinct()
        if not results.exists():
            messages.info(request, f"No results found for '{query}'.")
    else:
        messages.warning(request, "Please enter a search query.")

    context = {
        "query": query,
        "results": results
    }
    return render(request, "search_results.html", context)



# ----------------------- Profile -----------------------
@login_required(login_url='login')
def profile_view(request: HttpRequest) -> HttpResponse:
    """
    Allow authenticated users to view and update their profile details.

    Handles both GET and POST requests for profile update form.
    """
    user = request.user
    profile = getattr(user, 'profile', None)

    if request.method == "POST":
        u_form = UserUpdateForm(request.POST, instance=user)
        p_form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)

        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, "✅ Your profile has been updated successfully.")
            return redirect("profile")
        else:
            messages.error(request, "❌ Please correct the errors below.")
    else:
        u_form = UserUpdateForm(instance=user)
        p_form = ProfileUpdateForm(instance=profile)

    context = {
        "u_form": u_form,
        "p_form": p_form,
        "page_title": "Your Profile"
    }

    return render(request, "profile.html", context)





# ----------------------- Password Reset -----------------------@login_required(login_url='login')
def change_password(request: HttpRequest) -> HttpResponse:
    """
    Allow logged-in users to change their password with validation and email notification.
    """
    if request.method == "POST":
        current_password = request.POST.get("current_password", "").strip()
        new_password = request.POST.get("new_password", "").strip()
        confirm_password = request.POST.get("confirm_password", "").strip()

        # === Validation ===
        if not request.user.check_password(current_password):
            messages.error(request, "❌ Current password is incorrect.")
            return redirect("change_password")

        if new_password != confirm_password:
            messages.error(request, "⚠️ New passwords do not match.")
            return redirect("change_password")

        if len(new_password) < 8:
            messages.error(request, "🔒 Password must be at least 8 characters long.")
            return redirect("change_password")

        # === Update Password ===
        user = request.user
        user.set_password(new_password)
        user.save()
        update_session_auth_hash(request, user)  # Prevents logout

        # === Send Email Notification ===
        subject = "🔐 Your MyShop password has been changed"
        plain_message = f"""
Hi {user.username},

This is to inform you that your password was successfully changed.

If you did not initiate this change, please contact support immediately.

Best regards,  
MyShop Team
"""
        html_message = f"""
<div style="font-family:Arial,sans-serif; color:#333;">
  <h2>🔐 Password Change Confirmation</h2>
  <p>Hello <strong>{user.username}</strong>,</p>
  <p>Your password has been <strong>successfully changed</strong> on <strong>MyShop</strong>.</p>
  <p>If this wasn't you, please <a href="mailto:support@myshop.com">contact support</a> immediately.</p>
  <br>
  <p>Thanks,<br>The MyShop Team</p>
</div>
"""
        try:
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False
            )
        except Exception as e:
            messages.warning(request, f"Password changed, but failed to send email: {str(e)}")

        messages.success(request, "✅ Password changed successfully. A confirmation email has been sent.")
        return redirect("profile")

    return render(request, "change_password.html")






# @login_required(login_url='login')
def forgot_password(request):
    if request.method == 'POST':
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                user = User.objects.get(email=email)
                token = generate_token(email)
                reset_link = request.build_absolute_uri(f'/reset-password/{token}/')
                send_mail(
                    'Password Reset Request',
                    f'Click the link to reset your password: {reset_link}',
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                )
                messages.success(request, 'Reset link sent to your email.')
                return redirect('login')
            except User.DoesNotExist:
                messages.error(request, 'No user found with that email.')
    else:
        form = ForgotPasswordForm()
    return render(request, 'forgot_password.html', {'form': form})






# @login_required(login_url='login')
def reset_password(request: HttpRequest, token: str) -> HttpResponse:
    """
    Allow users to reset password using a valid token (from email).
    """
    email = verify_token(token)
    if not email:
        messages.error(request, "❌ Invalid or expired reset token.")
        return redirect("forgot_password")

    user = get_object_or_404(User, email=email)

    if request.method == "POST":
        form = ResetPasswordForm(request.POST)
        if form.is_valid():
            new_password = form.cleaned_data["new_password"]

            # Optional: Check if the new password is strong
            if len(new_password) < 8:
                messages.error(request, "🔒 Password must be at least 8 characters.")
                return render(request, "reset_password.html", {'form': form, 'token': token})

            user.set_password(new_password)
            user.save()

            # Optionally send confirmation email
            try:
                send_mail(
                    subject="🔐 Your MyShop password has been reset",
                    message=f"Hello {user.username},\n\nYour password has been successfully reset.\n\nIf you did not perform this, contact us immediately.\n\n– MyShop Team",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    html_message=f"""
                    <div style="font-family:Arial,sans-serif;color:#333;">
                      <h3>Hello {user.username},</h3>
                      <p>Your password has been <strong>successfully reset</strong>.</p>
                      <p>If this wasn't you, <a href="mailto:support@myshop.com">contact support</a> immediately.</p>
                      <p>– MyShop Team</p>
                    </div>
                    """,
                    fail_silently=True
                )
            except Exception as e:
                messages.warning(request, f"Password reset but email not sent: {str(e)}")

            messages.success(request, "✅ Password reset successful. You can now log in.")
            return redirect("login")
        else:
            messages.error(request, "⚠️ Please correct the errors below.")
    else:
        form = ResetPasswordForm()

    return render(request, "reset_password.html", {'form': form, 'token': token})





# ----------------------- Contact / About -----------------------
# @login_required(login_url='login')
# def contact_view(request):
#     if request.method == "POST":
#         form = ContactForm(request.POST)
#         if form.is_valid():
#             form.save()
#             messages.success(request, "Your message has been sent!")
#             return redirect('contact')
#     else:
#         form = ContactForm()
#     return render(request, 'contact.html', {'form': form})

# @login_required(login_url='login')
# def about(request):
#     return render(request, "about.html")

# ----------------------- Cart & Orders -----------------------




@login_required(login_url='login')
def base_shop(request: HttpRequest) -> HttpResponse:
    """
    Displays a paginated list of products on the shop page.
    Accessible only to logged-in users.
    """
    products = Product.objects.all().order_by('-id')
    paginator = Paginator(products, 9)  # 9 products per page

    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "base_shop.html", {
        "page_obj": page_obj,
        "title": "🛍 Shop"
    })

# logger = logging.getLogger(__name__)





logger = logging.getLogger(__name__)

@login_required(login_url='login')
@require_POST
def add_to_cart(request: HttpRequest, product_id: int) -> HttpResponse:
    """
    Adds a product to the user's cart or increments its quantity if already present.
    Supports AJAX and limits max quantity per product.
    """
    product = get_object_or_404(Product, id=product_id)

    try:
        quantity_to_add = int(request.POST.get('quantity', 1))
        quantity_to_add = max(quantity_to_add, 1)
    except (ValueError, TypeError):
        quantity_to_add = 1

    MAX_QUANTITY = 10

    cart_item, created = Cart.objects.get_or_create(user=request.user, product=product)

    if created:
        cart_item.quantity = min(quantity_to_add, MAX_QUANTITY)
    else:
        new_quantity = cart_item.quantity + quantity_to_add
        if new_quantity > MAX_QUANTITY:
            cart_item.quantity = MAX_QUANTITY
            messages.warning(request, f"⚠️ Max quantity ({MAX_QUANTITY}) reached for '{product.title}'.")
        else:
            cart_item.quantity = new_quantity

    cart_item.save()
    logger.info(f"🛒 User '{request.user.username}' added {quantity_to_add} x '{product.title}' to cart.")

    # Handle AJAX request
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            "success": True,
            "message": f"'{product.title}' added to cart (Qty: {cart_item.quantity}).",
            "cartQuantity": cart_item.quantity,
        })

    messages.success(request, f"✅ '{product.title}' added to cart (Qty: {cart_item.quantity}).")

    # Handle proper redirection
    next_url = (
        request.POST.get('next') or
        request.META.get('HTTP_REFERER') or
        reverse('view_cart')  # fallback
    )
    return redirect('view_cart')

@login_required(login_url='login')
@require_POST
def update_cart_quantity(request: HttpRequest, product_id: int) -> HttpResponse:
    """
    Update the quantity of a product in the user's cart.
    Supports 'increase' and 'decrease' actions via POST.
    Enforces min quantity of 1 and optional max quantity.
    """
    cart_item = get_object_or_404(Cart, user=request.user, product_id=product_id)

    action = request.POST.get('action')
    MAX_QUANTITY = 10  # Define max quantity per product if needed

    if action == 'increase':
        if cart_item.quantity < MAX_QUANTITY:
            cart_item.quantity += 1
            cart_item.save()
            messages.success(request, f"✅ Increased quantity of '{cart_item.product.title}' to {cart_item.quantity}.")
            logger.info(f"User '{request.user.username}' increased quantity of '{cart_item.product.title}' to {cart_item.quantity}.")
        else:
            messages.warning(request, f"⚠️ Maximum quantity of {MAX_QUANTITY} reached for this product.")
    elif action == 'decrease':
        if cart_item.quantity > 1:
            cart_item.quantity -= 1
            cart_item.save()
            messages.success(request, f"✅ Decreased quantity of '{cart_item.product.title}' to {cart_item.quantity}.")
            logger.info(f"User '{request.user.username}' decreased quantity of '{cart_item.product.title}' to {cart_item.quantity}.")
        else:
            messages.warning(request, "⚠️ Quantity cannot be less than 1.")
    else:
        messages.error(request, "❌ Invalid action specified.")
        logger.warning(f"User '{request.user.username}' attempted invalid cart action: '{action}'.")

    # Optional: Handle AJAX requests gracefully
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            "success": action in ['increase', 'decrease'],
            "quantity": cart_item.quantity,
            "message": messages.get_messages(request),
        })

    # Redirect to previous page or cart view
    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or 'view_cart'
    return redirect(next_url)


@login_required(login_url='login')
@require_POST
def remove_from_cart(request: HttpRequest, product_id: int) -> HttpResponse:
    """
    Remove a product from the authenticated user's cart.
    Only accepts POST requests to prevent accidental removals.
    """
    cart_item = get_object_or_404(Cart, user=request.user, product_id=product_id)
    product_title = cart_item.product.title

    cart_item.delete()
    messages.success(request, f"🗑️ '{product_title}' removed from your cart.")
    logger.info(f"User '{request.user.username}' removed '{product_title}' from cart.")

    # Handle AJAX request gracefully
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({"success": True, "message": f"'{product_title}' removed from cart."})

    # Redirect to referrer or fallback to cart view
    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or 'view_cart'
    return redirect(next_url)

@login_required(login_url='login')
def view_cart(request):
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        action = request.POST.get('action')
        product = get_object_or_404(Product, id=product_id)

        try:
            cart_item = Cart.objects.get(user=request.user, product=product)
        except Cart.DoesNotExist:
            messages.error(request, "Item not found in your cart.")
            return redirect('view_cart')

        if action == 'increase':
            cart_item.quantity += 1
            cart_item.save()
            messages.success(request, f"✅ Increased quantity of '{product.title}'")
        elif action == 'decrease':
            if cart_item.quantity > 1:
                cart_item.quantity -= 1
                cart_item.save()
                messages.info(request, f"🔽 Decreased quantity of '{product.title}'")
            else:
                cart_item.delete()
                messages.warning(request, f"🗑️ Removed '{product.title}' from cart")
        elif action == 'remove':
            cart_item.delete()
            messages.error(request, f"❌ '{product.title}' removed from your cart.")

        return redirect('view_cart')

    # GET: Display cart
    cart_items_qs = Cart.objects.filter(user=request.user).select_related('product')
    paginator = Paginator(cart_items_qs, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    total = sum(item.product.price * item.quantity for item in page_obj.object_list)
    item_count = cart_items_qs.count()

    context = {
        'cart_items': page_obj,
        'total': total,
        'item_count': item_count,
        'paginator': paginator,
        'page_obj': page_obj,
    }
    return render(request, 'cart.html', context)


@login_required(login_url='login')
def checkout(request: HttpRequest) -> HttpResponse:
    """
    Render the checkout page displaying user's cart items and total amount.
    Redirects to cart page if the cart is empty.
    """
    cart_items = Cart.objects.filter(user=request.user).select_related('product')
    if not cart_items.exists():
        messages.warning(request, "Your cart is empty. Please add items before checking out.")
        return redirect('view_cart')

    total = sum(item.subtotal() for item in cart_items)
    item_count = cart_items.count()

    context = {
        'cart_items': cart_items,
        'total': total,
        'item_count': item_count,
        'user': request.user,
    }
    return render(request, 'checkout.html', context)


@login_required(login_url='login')
def process_checkout(request: HttpRequest) -> HttpResponse:
    """
    Process checkout form submission, validate inputs, store checkout info in session,
    and redirect to the payment processing page.
    """
    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        phone = request.POST.get('phone', '').strip()
        address = request.POST.get('address', '').strip()

        # Basic validation
        if not all([full_name, phone, address]):
            messages.error(request, "⚠️ Please fill in all required fields.")
            return redirect('checkout')

        # Save data to session securely
        request.session['checkout_info'] = {
            'full_name': full_name,
            'phone': phone,
            'address': address
        }

        return redirect('payment_redirect')  # Redirect to payment gateway step

    # For non-POST requests, redirect back to checkout
    return redirect('checkout')


@login_required(login_url='login')
def payment_redirect(request: HttpRequest) -> HttpResponse:
    """
    Prepare and render the payment page for the authenticated user.
    Calculates the total amount from the user's cart.
    Redirects to the cart page if the cart is empty with an informational message.
    """
    cart_items = Cart.objects.filter(user=request.user)

    if not cart_items.exists():
        messages.info(request, "Your cart is empty. Please add items before proceeding to payment.")
        return redirect('view_cart')

    total_aggregate = cart_items.aggregate(
        total=Sum(F('quantity') * F('product__price'), output_field=FloatField())
    )
    total = total_aggregate.get('total') or 0.0

    context = {
        'total': total,
        'user': request.user,
        'cart_items': cart_items,
    }

    return render(request, 'payment_redirect.html', context)


@login_required(login_url='login')
def esewa_payment(request: HttpRequest) -> HttpResponse:
    """
    View to prepare data for Esewa payment page.
    Calculates total cart amount for the logged-in user.

    If cart is empty, redirect to shop or cart page with a message.
    """
    cart_items = Cart.objects.filter(user=request.user)

    if not cart_items.exists():
        # Optionally add a message to inform cart is empty
        # messages.info(request, "Your cart is empty. Add items to proceed to payment.")
        return redirect('shop')  # or 'view_cart'

    # Calculate total using database aggregation for better performance
    total_data = cart_items.aggregate(
        total=Sum(F('quantity') * F('product__price'), output_field=FloatField())
    )
    total = total_data.get('total') or 0.0

    context = {
        'total': total,
        'user': request.user,
        'cart_items': cart_items,  # optional, in case template needs it
    }
    return render(request, 'esewa_payment.html', context)





@login_required(login_url='login')
def place_order(request):
    if request.method == 'POST':
        phone = request.POST.get('phone', '').strip()
        address = request.POST.get('address', '').strip()

        # Validate phone
        if not phone or not phone.isdigit() or len(phone) < 7:
            messages.error(request, "📱 Please enter a valid phone number.")
            return redirect('place_order')

        # Validate address
        if not address:
            messages.error(request, "📍 Please provide an address.")
            return redirect('place_order')

        # Fetch cart items
        cart_items = Cart.objects.filter(user=request.user).select_related('product')
        if not cart_items.exists():
            messages.warning(request, "🛒 Your cart is empty.")
            return redirect('view_cart')

        # Create order
        order = Order.objects.create(
            user=request.user,
            phone=phone,
            address=address,
            ordered_at=timezone.now()
        )

        # Add items to OrderItem and prepare email
        order_summary = ""
        total_cost = 0
        for item in cart_items:
            OrderItem.objects.create(order=order, product=item.product, quantity=item.quantity)
            subtotal = item.product.price * item.quantity
            order_summary += f"{item.product.title} (x{item.quantity}) - Rs. {subtotal}\n"
            total_cost += subtotal

        # Clear cart after order
        cart_items.delete()

        # Send confirmation email
        subject = f"🧾 Order Confirmation - Order #{order.id}"
        message = f"""
Dear {request.user.username},

Thank you for placing your order! Here are your order details:

Order ID: {order.id}
Phone: {phone}
Address: {address}

Items:
{order_summary}

Total: Rs. {total_cost}

Your order will be delivered soon.

Regards,  
MyShop Team
""".strip()

        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [request.user.email],
            fail_silently=False
        )

        messages.success(request, f"✅ Order #{order.id} placed successfully! A confirmation email has been sent.")
        return redirect('order_history')

    # GET method: show the form with cart items
    cart_items = Cart.objects.filter(user=request.user).select_related('product')
    total = sum(item.product.price * item.quantity for item in cart_items)

    return render(request, 'order.html', {
        'cart_items': cart_items,
        'total': total,
    })


@login_required
def order_history(request):
    """
    Display the user's order history with pagination.
    Shows most recent orders first.
    """
    orders_qs = (
        Order.objects
        .filter(user=request.user)
        .prefetch_related(
            Prefetch('items', queryset=OrderItem.objects.select_related('product'))
        )
        .order_by('-ordered_at')
    )

    paginator = Paginator(orders_qs, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'orders': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
    }
    return render(request, 'order_history.html', context)



@login_required
def order_confirm(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'order_confirm.html', {'order': order})



def download_invoice(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    total = sum(item.product.price * item.quantity for item in order.items.all())

    template_path = 'invoice.html'
    context = {'order': order, 'total': total}

    response = HttpResponse(content_type='pdf')
    response['Content-Disposition'] = f'attachment; filename="Invoice_Order_{order.id}.pdf"'

    # Render template to HTML and then to PDF
    template = get_template(template_path)
    html = template.render(context)

    pisa_status = pisa.CreatePDF(html, dest=response)

    if pisa_status.err:
        return HttpResponse("❌ Error generating PDF invoice")
    return response

@login_required
def remove_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    if request.method == 'POST':
        order.delete()
        messages.success(request, f"Order #{order_id} has been removed.")
        return redirect('order_history')  # Adjust this to your order list view name
    messages.error(request, "Invalid request method.")
    return redirect('order_history')



def add_selected_to_cart(request):
    if request.method == "POST":
        product_ids = request.POST.getlist('product_ids')
        if product_ids:
            for product_id in product_ids:
                product = get_object_or_404(Product, id=product_id)
                cart_item, created = Cart.objects.get_or_create(
                    user=request.user,
                    product=product,
                )
                if not created:
                    cart_item.quantity += 1
                    cart_item.save()
            messages.success(request, "Selected products added to cart!")
        else:
            messages.warning(request, "Please select at least one product.")
    return redirect('base_shop')  # or wherever your product list lives

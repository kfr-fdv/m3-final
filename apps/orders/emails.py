from django.conf import settings
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.template.loader import render_to_string

from .models import Order


def send_order_created_emails(order: Order) -> None:
    """Надсилає підтвердження покупцю (text+html) та сповіщення адміністратору.

    У dev використовується консольний backend — листи друкуються в лог, нікуди не йдуть.
    """
    context = {"order": order, "shop_name": settings.SHOP_NAME}

    if order.email:
        subject = f"Ваше замовлення #{order.pk} у {settings.SHOP_NAME}"
        text_body = render_to_string("emails/order_created_customer.txt", context)
        html_body = render_to_string("emails/order_created_customer.html", context)
        message = EmailMultiAlternatives(
            subject, text_body, settings.DEFAULT_FROM_EMAIL, [order.email]
        )
        message.attach_alternative(html_body, "text/html")
        message.send()

    admin_subject = f"Нове замовлення #{order.pk}"
    admin_body = render_to_string("emails/order_created_admin.txt", context)
    EmailMessage(
        admin_subject, admin_body, settings.DEFAULT_FROM_EMAIL, [settings.ORDER_ADMIN_EMAIL]
    ).send()

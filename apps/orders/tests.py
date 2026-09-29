from decimal import Decimal

import pytest
from django.core import mail
from django.test import Client
from django.urls import reverse

from apps.accounts.models import User
from apps.catalog.models import Product
from apps.orders.cart import CART_SESSION_KEY
from apps.orders.forms import CheckoutForm
from apps.orders.models import Order

CHECKOUT_DATA = {
    "last_name": "Шевченко",
    "first_name": "Аліса",
    "middle_name": "",
    "phone": "+38 (099) 111-22-33",
    "city_name": "Київ (Київська обл.)",
    "city_ref": "city-kyiv",
    "delivery_type": "branch",
    "warehouse_name": "Відділення №1",
    "warehouse_ref": "wh-1",
    "payment_method": "card",
}


def cart_of(client: Client) -> dict[str, int]:
    return client.session.get(CART_SESSION_KEY, {})


def add_to_cart(client: Client, product: Product, quantity: int = 1):
    return client.post(reverse("orders:cart_add", args=[product.pk]), {"quantity": quantity})


# --- Cart ---------------------------------------------------------------------------


def test_add_to_cart_keeps_product_in_session(client: Client, product: Product) -> None:
    add_to_cart(client, product)
    add_to_cart(client, product, 2)

    assert cart_of(client) == {str(product.pk): 3}


def test_cannot_add_more_than_in_stock(client: Client, product: Product) -> None:
    response = add_to_cart(client, product, product.stock + 1)

    assert cart_of(client) == {}
    assert "лишилось лише" in str(list(response.wsgi_request._messages)[0])


def test_cart_page_counts_total(client: Client, product: Product) -> None:
    add_to_cart(client, product, 2)

    response = client.get(reverse("orders:cart"))

    assert response.context["total"] == Decimal("11.98")


def test_update_to_zero_removes_line(client: Client, product: Product) -> None:
    add_to_cart(client, product, 2)

    client.post(reverse("orders:cart_update", args=[product.pk]), {"quantity": 0})

    assert cart_of(client) == {}


def test_remove_from_cart(client: Client, product: Product) -> None:
    add_to_cart(client, product)

    client.post(reverse("orders:cart_remove", args=[product.pk]))

    assert cart_of(client) == {}


def test_hidden_product_disappears_from_cart(client: Client, product: Product) -> None:
    add_to_cart(client, product)
    Product.objects.filter(pk=product.pk).update(is_active=False)

    assert client.get(reverse("orders:cart")).context["is_empty"]


# --- Checkout form ------------------------------------------------------------------


@pytest.mark.parametrize("phone", ["0991112233", "380991112233", "+38 (099) 111-22-33"])
def test_phone_is_normalized(nova_poshta, phone: str) -> None:
    form = CheckoutForm(CHECKOUT_DATA | {"phone": phone})

    assert form.is_valid(), form.errors
    assert form.cleaned_data["phone"] == "+380991112233"


def test_phone_must_be_ukrainian(nova_poshta) -> None:
    form = CheckoutForm(CHECKOUT_DATA | {"phone": "12345"})

    assert "phone" in form.errors


def test_branch_must_belong_to_selected_city(nova_poshta) -> None:
    form = CheckoutForm(CHECKOUT_DATA | {"city_ref": "city-lviv"})

    assert "warehouse_name" in form.errors


def test_branch_must_match_delivery_method(nova_poshta) -> None:
    form = CheckoutForm(CHECKOUT_DATA | {"delivery_type": "postomat"})

    assert "warehouse_name" in form.errors


def test_city_must_be_picked_from_list(nova_poshta) -> None:
    form = CheckoutForm(CHECKOUT_DATA | {"city_ref": ""})

    assert form.errors["city_ref"] == ["Оберіть місто зі списку."]


def test_form_error_when_nova_poshta_is_down(nova_poshta) -> None:
    nova_poshta.down = True

    form = CheckoutForm(CHECKOUT_DATA)

    assert not form.is_valid()
    assert form.non_field_errors()


# --- Placing an order ---------------------------------------------------------------


@pytest.fixture
def buyer(client: Client, user: User, product: Product) -> Client:
    client.force_login(user)
    add_to_cart(client, product, 3)
    return client


def test_checkout_requires_login(client: Client) -> None:
    response = client.get(reverse("orders:checkout"))

    assert response.status_code == 302
    assert reverse("accounts:login") in response["Location"]


def test_checkout_with_empty_cart_goes_back_to_cart(client: Client, user: User) -> None:
    client.force_login(user)

    response = client.get(reverse("orders:checkout"))

    assert response["Location"] == reverse("orders:cart")


def test_checkout_creates_order(
    buyer: Client, user: User, product: Product, nova_poshta, django_capture_on_commit_callbacks
) -> None:
    with django_capture_on_commit_callbacks(execute=True):
        response = buyer.post(reverse("orders:checkout"), CHECKOUT_DATA)

    order = Order.objects.get(user=user)
    item = order.items.get()
    product.refresh_from_db()
    assert response["Location"] == reverse("accounts:profile")
    assert (item.quantity, item.price) == (3, Decimal("5.99"))
    assert order.total_price == Decimal("17.97")
    assert order.phone == "+380991112233"
    assert order.full_name == "Шевченко Аліса"
    assert order.shipping_address == "Київ, Відділення №1: вул. Пирогівський шлях, 135"
    assert order.np_warehouse_ref == "wh-1"
    assert order.status == Order.OrderStatus.PAID  # mock card payment
    assert product.stock == 7
    assert cart_of(buyer) == {}
    assert mail.outbox[0].to == ["alice@example.com"]


def test_cash_on_delivery_order_stays_pending(buyer: Client, user: User, nova_poshta) -> None:
    buyer.post(reverse("orders:checkout"), CHECKOUT_DATA | {"payment_method": "cod"})

    assert Order.objects.get(user=user).status == Order.OrderStatus.PENDING


def test_price_is_taken_at_purchase_time(
    buyer: Client, user: User, product: Product, nova_poshta
) -> None:
    buyer.post(reverse("orders:checkout"), CHECKOUT_DATA)
    Product.objects.filter(pk=product.pk).update(price=Decimal("100"))

    assert Order.objects.get(user=user).items.get().price == Decimal("5.99")


def test_no_order_when_stock_ran_out(
    buyer: Client, user: User, product: Product, nova_poshta
) -> None:
    Product.objects.filter(pk=product.pk).update(stock=2)  # someone bought it meanwhile

    response = buyer.post(reverse("orders:checkout"), CHECKOUT_DATA)

    assert response["Location"] == reverse("orders:cart")
    assert not Order.objects.exists()
    product.refresh_from_db()
    assert product.stock == 2


def test_invalid_form_shows_errors_and_keeps_cart(buyer: Client, product: Product) -> None:
    response = buyer.post(reverse("orders:checkout"), CHECKOUT_DATA | {"phone": "bad"})

    assert response.status_code == 200
    assert response.context["form"].errors
    assert cart_of(buyer) == {str(product.pk): 3}


def test_order_remembers_delivery_for_next_checkout(
    buyer: Client, user: User, product: Product, nova_poshta
) -> None:
    buyer.post(
        reverse("orders:checkout"),
        CHECKOUT_DATA | {"delivery_type": "postomat", "warehouse_ref": "wh-5"},
    )
    user.refresh_from_db()
    assert (user.np_warehouse_ref, user.np_delivery_type) == ("wh-5", "postomat")
    assert (user.last_name, user.phone) == ("Шевченко", "+380991112233")  # were empty

    add_to_cart(buyer, product)
    initial = buyer.get(reverse("orders:checkout")).context["form"].initial

    assert initial["warehouse_ref"] == "wh-5"
    assert initial["city_ref"] == "city-kyiv"
    assert initial["last_name"] == "Шевченко"

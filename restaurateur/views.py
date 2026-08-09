from django import forms
from django.db.models import Prefetch, F
from django.shortcuts import redirect, render
from django.views import View
from django.urls import reverse_lazy
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth import authenticate, login
from django.contrib.auth import views as auth_views
from geopy.distance import distance
from django.conf import settings


from foodcartapp.models import Product, Restaurant, Order, OrderItem
from geo.models import AddressCoordinates
from geo.utils import fetch_coordinates_from_api


class Login(forms.Form):
    username = forms.CharField(
        label='Логин', max_length=75, required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Укажите имя пользователя'
        })
    )
    password = forms.CharField(
        label='Пароль', max_length=75, required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите пароль'
        })
    )


class LoginView(View):
    def get(self, request, *args, **kwargs):
        form = Login()
        return render(request, "login.html", context={
            'form': form
        })

    def post(self, request):
        form = Login(request.POST)

        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            user = authenticate(request, username=username, password=password)
            if user:
                login(request, user)
                if user.is_staff:  # FIXME replace with specific permission
                    return redirect("restaurateur:RestaurantView")
                return redirect("start_page")

        return render(request, "login.html", context={
            'form': form,
            'ivalid': True,
        })


class LogoutView(auth_views.LogoutView):
    next_page = reverse_lazy('restaurateur:login')


def is_manager(user):
    return user.is_staff  # FIXME replace with specific permission


@user_passes_test(is_manager, login_url='restaurateur:login')
def view_products(request):
    restaurants = list(Restaurant.objects.order_by('name'))
    products = list(Product.objects.prefetch_related('menu_items'))

    products_with_restaurant_availability = []
    for product in products:
        availability = {item.restaurant_id: item.availability for item in product.menu_items.all()}
        ordered_availability = [availability.get(restaurant.id, False) for restaurant in restaurants]

        products_with_restaurant_availability.append(
            (product, ordered_availability)
        )

    return render(request, template_name="products_list.html", context={
        'products_with_restaurant_availability': products_with_restaurant_availability,
        'restaurants': restaurants,
    })


@user_passes_test(is_manager, login_url='restaurateur:login')
def view_restaurants(request):
    return render(request, template_name="restaurants_list.html", context={
        'restaurants': Restaurant.objects.all(),
    })


def get_addresses_coordinates(addresses):
    addresses = {address for address in addresses if address}

    if not addresses:
        return {}

    existing_coordinates = list(
        AddressCoordinates.objects.filter(
            address__in=addresses
        )
    )

    coordinates = {}
    for coordinate in existing_coordinates:
        if coordinate.latitude is not None and coordinate.longitude is not None:
            coordinates[coordinate.address] = (
                coordinate.latitude,
                coordinate.longitude,
            )

    existing_addresses = {coordinate.address for coordinate in existing_coordinates}
    missing_addresses = addresses - existing_addresses

    new_coordinates = []

    for address in missing_addresses:
        coords = fetch_coordinates_from_api(
            settings.YANDEX_GEOCODER_API_KEY,
            address,
        )

        if coords:
            longitude, latitude = coords

            latitude = float(latitude)
            longitude = float(longitude)

            coordinates[address] = (latitude, longitude)

            new_coordinates.append(
                AddressCoordinates(
                    address=address,
                    latitude=latitude,
                    longitude=longitude,
                )
            )
        else:
            new_coordinates.append(
                AddressCoordinates(
                    address=address,
                    latitude=None,
                    longitude=None,
                )
            )

    if new_coordinates:
        AddressCoordinates.objects.bulk_create(
            new_coordinates
        )

    return coordinates


@user_passes_test(is_manager, login_url='restaurateur:login')
def view_orders(request):
    orders = (
        Order.objects
        .exclude(status=Order.STATUS_DONE)
        .select_related('restaurant')
        .prefetch_related(
            Prefetch(
                'items',
                queryset=OrderItem.objects.select_related('product')
            )
        )
        .with_total_price()
        .order_by(
            F('restaurant').asc(nulls_first=True),
            '-id',
        )
        .with_available_restaurants()
    )

    restaurants = list(
        Restaurant.objects.all()
    )

    addresses = {restaurant.address for restaurant in restaurants if restaurant.address}

    addresses.update(order.address for order in orders if order.address)

    coordinates = get_addresses_coordinates(addresses)

    restaurant_coordinates = {}
    for restaurant in restaurants:
        address = restaurant.address
        coordinates_value = coordinates.get(address)
        restaurant_coordinates[restaurant.id] = coordinates_value

    for order in orders:
        order_coordinates = coordinates.get(order.address)

        order.address_not_found = not order_coordinates

        if not order_coordinates:
            for restaurant in order.available_restaurants:
                restaurant.distance = None
            continue

        for restaurant in order.available_restaurants:
            restaurant_coordinates_value = (
                restaurant_coordinates.get(
                    restaurant.id
                )
            )

            if restaurant_coordinates_value:
                restaurant.distance = round(
                    distance(
                        order_coordinates,
                        restaurant_coordinates_value,
                    ).kilometers,
                    1,
                )
            else:
                restaurant.distance = None

        order.available_restaurants.sort(
            key=lambda restaurant: (
                restaurant.distance is None,
                restaurant.distance
                if restaurant.distance is not None
                else 0,
            )
        )

    return render(request, template_name='order_items.html', context={
        'orders': orders,
    })

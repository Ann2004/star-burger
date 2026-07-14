import json


from django.http import JsonResponse
from django.templatetags.static import static
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from rest_framework.decorators import api_view
from rest_framework.response import Response
from phonenumber_field.validators import validate_international_phonenumber


from .models import Product
from .models import Order


def banners_list_api(request):
    # FIXME move data to db?
    return JsonResponse([
        {
            'title': 'Burger',
            'src': static('burger.jpg'),
            'text': 'Tasty Burger at your door step',
        },
        {
            'title': 'Spices',
            'src': static('food.jpg'),
            'text': 'All Cuisines',
        },
        {
            'title': 'New York',
            'src': static('tasty.jpg'),
            'text': 'Food is incomplete without a tasty dessert',
        }
    ], safe=False, json_dumps_params={
        'ensure_ascii': False,
        'indent': 4,
    })


def product_list_api(request):
    products = Product.objects.select_related('category').available()

    dumped_products = []
    for product in products:
        dumped_product = {
            'id': product.id,
            'name': product.name,
            'price': product.price,
            'special_status': product.special_status,
            'description': product.description,
            'category': {
                'id': product.category.id,
                'name': product.category.name,
            } if product.category else None,
            'image': product.image.url,
            'restaurant': {
                'id': product.id,
                'name': product.name,
            }
        }
        dumped_products.append(dumped_product)
    return JsonResponse(dumped_products, safe=False, json_dumps_params={
        'ensure_ascii': False,
        'indent': 4,
    })

@api_view(['GET', 'POST'])
def register_order(request):
    if request.method == 'GET':
        return Response({
            'message': 'Send POST request with order data'
        })
    
    order_data = request.data
    
    required_fields = ['products', 'firstname', 'lastname', 'phonenumber', 'address']
    missed_fields = []
    empty_fields = []
    for field in required_fields:
        if field not in order_data:
            missed_fields.append(field)
        elif order_data[field] in (None, ""):
            empty_fields.append(field)

    if missed_fields:
        return Response(
            {'error': f'{", ".join(missed_fields)}: Обязательное поле.'},
            status=400
        )
    
    if empty_fields:
        return Response(
            {'error': f'{", ".join(empty_fields)}: Это поле не может быть пустым.'},
            status=400
        )

    if len(order_data['products']) == 0:
        return Response(
            {'error': 'products: Этот список не может быть пустым.'},
            status=400
        )  

    if not isinstance (order_data['products'], list):
        return Response(
            {'error': 'products: Ожидался list со значениями'},
            status=400
        )
    
    str_fields = ['firstname', 'lastname', 'phonenumber', 'address']
    not_str_fields = []
    for field in str_fields:
        if not isinstance(order_data[field], str):
            not_str_fields.append(field)

    if not_str_fields:
        return Response(
            {'error': f'{", ".join(not_str_fields)}: Not a valid string.'},
            status=400
        )

    try:
        validate_international_phonenumber(order_data['phonenumber'])
    except ValidationError:
        return Response(
            {'error': 'phonenumber: Введен некорректный номер телефона.'},
            status=400
        )
    
    order_products = []
    for order_product in order_data['products']:
        product_id = order_product['product']
        try:
            product = Product.objects.get(id=product_id)
            order_products.append({
            'product': product,
            'quantity': order_product['quantity']
        })
        except Product.DoesNotExist:
            return Response(
            {'error': f'products: Недопустимый первичный ключ {product_id}'},
            status=400
        )

    order = Order.objects.create(
        firstname=order_data['firstname'],
        lastname=order_data['lastname'],
        phone_number=order_data['phonenumber'],
        address=order_data['address']
    )

    for item in order_products:
        order.items.create(
            product=item['product'],
            quantity=item['quantity']
        )

    return Response({
        'status': 'success',
        'order_id': order.id
    })

'''
Author: Jingwei Wu
Date: 2024-11-27 16:07:47
LastEditTime: 2024-11-29 21:01:40
description: 
'''

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from db.mongo import db
from typing import List
from pydantic import BaseModel
from utils.auth import get_current_user
from bson import ObjectId

class CartItem(BaseModel):
    product_id: str
    quantity: int

class CreateOrderRequest(BaseModel):
    cart_items: List[CartItem]

class OrderItemResponse(BaseModel):
    name: str
    description: str
    quantity: int
    image: str
    price: int

class OrderResponse(BaseModel):
    items: List[OrderItemResponse]


class AddressResponse(BaseModel):
    name: str
    phone: str
    address: str

class OrderDetailResponse(BaseModel):
    order_id: str
    address: AddressResponse
    items: List[OrderItemResponse]
    created_at: str


router = APIRouter()

@router.post("/api/v1/create_order")
async def create_order(request: Request, user: dict = Depends(get_current_user)):
    """创建订单并从购物车中删除已下单商品"""
    body = await request.json()
    order_products = body.get("order_products", [])
    from_cart = body.get("from_cart", False)
    address = body.get("address", {})
    user_id = user["user_id"]
    print("Received order_products:", order_products)
    print(from_cart)
    print(address)
    if not order_products:
        raise HTTPException(status_code=400, detail="Cart items are required")
    if not address:
        raise HTTPException(status_code=400, detail="Address is required")
    
    total_price = 0.0
    products = await db["products"].find(
        {"_id": {"$in": [ObjectId(item["product_id"]) for item in order_products]}}
    ).to_list(len(order_products))

    # 用 product_id 创建字典
    product_map = {str(product["_id"]): product for product in products}

    for item in order_products:
        print(item)
        product = product_map.get(item["product_id"])
        if not product:
            print("NOT FOUND")
            raise HTTPException(
                status_code=404, detail=f"Product {item['product_id']} not found"
            )
        total_price += product["price"] * item["quantity"]

    # 生成订单数据
    order_data = {
    "user_id": user_id,
    "items": order_products,
    "address": address,
    "status": "Paid",
    "created_at": datetime.utcnow().isoformat()
    }

    # 插入订单数据
    result = await db["orders"].insert_one(order_data)

    # 从购物车中删除商品
    # if from_cart:
    #     await remove_items_from_cart(user_id, order_products)

    return {
        "status": "OK",
        "data": {
            "message": "Order created successfully",
            "order_id": str(result.inserted_id),
            "created_at": order_data["created_at"],
        },
    }



async def remove_items_from_cart(user_id: str, cart_items: list):
    """从购物车中删除已下单的商品"""
    for item in cart_items:
        product_id = item["product_id"]
        result = await db["carts"].delete_one({"user_id": user_id, "product_id": product_id})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail=f"Item {product_id} not found in cart")



@router.get("/api/v1/orders", response_model=dict)
async def get_all_orders(user: dict = Depends(get_current_user)):
    """
    Get all orders for the current user
    """
    user_id = user["user_id"]

    orders = await db["orders"].find({"user_id": user_id}).to_list(100)  # 获取最多100个订单，可以根据需求调整

    if not orders:
        raise HTTPException(status_code=404, detail="No orders found")

    order_responses = []
    for order in orders:
        # get product details for each item in the order
        order_items = []
        for item in order.get("items", []):
            product = await db["products"].find_one({"_id": ObjectId(item["product_id"])})
            if product:
                order_items.append(OrderItemResponse(
                    name=product["name"],
                    description=product["description"],
                    quantity=item["quantity"],
                    image=product["images"][0] if product.get("images") else "",
                    price=product["price"]
                ))

        order_responses.append(OrderResponse(items=order_items))

    return {
        "status": "OK",
        "data": {
            "orders": order_responses
        }
    }



@router.get("/api/v1/orders/{order_id}/details", response_model=dict)
async def get_order_details(order_id: str, user: dict = Depends(get_current_user)):
    """
    Get order details by order_id
    """
    order = await db["orders"].find_one({"_id": order_id, "user_id": user["user_id"]})


    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order_items = []
    for item in order.get("items", []):
        product = await db["products"].find_one({"_id": item["product_id"]})
        if product:
            order_items.append(OrderItemResponse(
                name=product["name"],
                description=product["description"],
                price=product["price"],
                quantity=item["quantity"],
                image_url=product["image"]
            ))

    return {
        "status": "OK",
        "data": {
            "order_id": str(order["_id"]),
            "address": AddressResponse(
                name=order["address"]["name"],
                phone=order["address"]["phone"],
                address=order["address"]["address"]
            ),
            "items": order_items,
            "created_at": order["created_at"]
        }
    }
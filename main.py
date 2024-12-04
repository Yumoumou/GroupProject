'''
Author: Jingwei Wu
Date: 2024-11-27 16:06:36
LastEditTime: 2024-11-29 17:12:15
description: 
'''

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import carts, feedbacks
from routes import users, products, orders, chatrooms
from db.mongo import client


app = FastAPI(
    title="E-Commerce API",
    description="A simple e-commerce backend API with user authentication, product management, cart, orders, chatrooms, and feedback.",
    version="1.0.0"
)

# 配置跨域中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 如果需要指定域名，替换为 ["http://example.com"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(users.router, tags=["Users"])
app.include_router(products.router, tags=["Products"])
app.include_router(carts.router, tags=["Cart"])
app.include_router(orders.router, tags=["Orders"])
app.include_router(feedbacks.router, tags=["Feedback"])
app.include_router(chatrooms.router, tags=["Feedback"])

# 健康检查端点
@app.get("/")
async def root():
    return {"message": "Welcome to the E-Commerce API"}

# 关闭数据库连接
@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()

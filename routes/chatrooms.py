from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from datetime import datetime
from db.mongo import db
from typing import List
from utils.auth import get_current_user
from bson import ObjectId
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

router = APIRouter()






# Response Model (可以根据需求修改)
class CreateChatRoomResponse(BaseModel):
    status: str
    data: dict

@router.post("/api/v1/new_chatroom/")
async def create_chatroom(request: Request, user: dict = Depends(get_current_user)):
    """
    Create a new chatroom between user and seller.
    """
    body = await request.json()
    seller_id = body["seller_id"]
    # Check if a chatroom already exists between the user and the seller
    existing_chatroom = await db["chatrooms"].find_one({"user_id": user["user_id"], "seller_id": seller_id})
    if existing_chatroom:
        # Fetch the seller's name from the `sellers` collection
        seller = await db["sellers"].find_one({"_id": ObjectId(seller_id)})
        seller_name = seller.get("name", "Unknown") if seller else "Unknown"

        # Return the existing chatroom's _id and seller name
        return {
            "status": "OK",
            "data": {
                "chatroom_id": str(existing_chatroom["_id"]),
                "seller_name": seller_name,
            }
        }
    
    seller = await db["sellers"].find_one({"_id": ObjectId(seller_id)})
    if not seller:
        raise HTTPException(status_code=404, detail="Seller not found")

    seller_name = seller.get("name", "Unknown")

    # Create the new chatroom data
    # Create the new chatroom data
    chatroom_data = {
        "user_id": user["user_id"],
        "seller_id": seller_id,
        "messages": [],  # Initialize messages as an empty array
    }

    # Insert the chatroom into the database
    result = await db["chatrooms"].insert_one(chatroom_data)

    # Return the generated chatroom_id (MongoDB's _id as chatroom_id)
    return {
        "status": "OK",
        "data": {
            "chatroom_id": str(result.inserted_id),
            "seller_name": seller_name,
        }
    }


class Message(BaseModel):
    sender: str
    content: str
    timestamp: str
class MessageResponse(BaseModel):
    status: str
    data: List[Message]

@router.get("/api/v1/chatrooms/{chatroom_id}/messages", response_model=List[Message])
async def get_messages(chatroom_id: str, user: dict = Depends(get_current_user)):
    """
    Get all messages in a specific chatroom.
    Ensure the user is part of the chatroom before retrieving messages.
    """
    # Check if the chatroom exists and if the user is part of it
    chatroom = await db["chatrooms"].find_one({"_id": ObjectId(chatroom_id)})

    if not chatroom:
        raise HTTPException(status_code=404, detail="Chatroom not found or you are not part of this chatroom")
    # Check if the user is part of the chatroom
    if user["user_id"] not in chatroom["user_id"]:  # 假设 user_ids 是存储用户ID的字段
        raise HTTPException(status_code=403, detail="You are not part of this chatroom")
    # Fetch messages from the chatroom
    messages = chatroom.get("messages", [])

    data = {
            "data": {
                "messages": [
                    {
                        "content": message["content"], 
                        "sender": message["sender"], 
                        "timestamp": message["timestamp"], 
                    } for message in messages
                ]
            }, 
            "status": "OK",
        }
    
    return JSONResponse(content=jsonable_encoder(data))


@router.post("/api/v1/chatrooms/{chatroom_id}/send_message")
async def send_message(chatroom_id: str,request: Request, user: dict = Depends(get_current_user)):
    """
    Send a message to a specific chatroom.
    Ensure the user is part of the chatroom before sending a message.
    """
    body = await request.json()
    # chatroom_id = body["chatroom_id"]
    content = body["content"]
    # Check if the chatroom exists and if the user is part of it
    chatroom = await db["chatrooms"].find_one(
        {"_id": ObjectId(chatroom_id), "$or": [{"user_id": user["user_id"]}, {"seller_id": user["user_id"]}]}
    )

    if not chatroom:
        raise HTTPException(status_code=404, detail="Chatroom not found or you are not part of this chatroom")

    # Store the user's message
    user_message = {
        "sender": "user",
        "content": content,
        "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    }

    # Insert user's message into the messages collection
    await db["chatrooms"].update_one(
        {"_id": ObjectId(chatroom_id)},
        {"$push": {"messages": user_message}}
    )

    # Automatically send a reply from the seller (hardcoded)
    seller_reply = {
        "sender": "Seller",  # Hardcoded seller username
        "content": "Thank you for your message. We will get back to you shortly.",
        "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    }

    # Insert seller's reply into the messages collection
    await db["chatrooms"].update_one(
        {"_id": ObjectId(chatroom_id)},
        {"$push": {"messages": seller_reply}}
    )

    return {"status": "OK"}

class ChatroomResponse(BaseModel):
    chatroom_id: str
    seller_name: str
    seller_avatar: str

@router.get("/api/v1/chatrooms", response_model=dict)
async def get_user_chatrooms(user: dict = Depends(get_current_user)):
    """
    Get all chatrooms for the current user
    """
    user_id = user["user_id"]
    print(user_id)

    chatrooms = await db["chatrooms"].find({"user_id": user_id}).to_list(100)

    if not chatrooms:
        raise HTTPException(status_code=404, detail="No chatrooms found for this user")

    chatroom_responses = []

    # 遍历每个聊天室，获取商家的头像和名称
    for chatroom in chatrooms:
        seller_id = chatroom["seller_id"]
        print(seller_id)
        
        # 查找商家信息
        seller = await db["sellers"].find_one({"_id": ObjectId(seller_id)})
        print(seller)
        if seller:
            chatroom_responses.append(ChatroomResponse(
                chatroom_id=str(chatroom["_id"]),
                seller_name=seller.get("name", "Unknown"),
                seller_avatar=seller.get("image", "")
            ))

    return {
        "status": "OK",
        "data": {
            "chatrooms": chatroom_responses
        }
    }
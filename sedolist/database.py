import os
from datetime import datetime
from typing import Any

# import pandas as pd
# import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import declarative_base, sessionmaker

# from sqlalchemy.exc import IntegrityError


load_dotenv()


#
# SQLAlchemyの設定(ORM)
#
# データベースURLの構築
DATABASE_URL = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASS')}@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"
# データベースエンジンの作成
engine = create_engine(DATABASE_URL, pool_size=10, max_overflow=20)
# セッションファクトリーの作成
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
# 親クラス
BASE: Any = declarative_base()


#
# モデル定義
#
class UserModel(BASE):
    """userテーブルのモデル"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    reset_token = Column(String, nullable=True)
    reset_token_expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now)


class ItemModel(BASE):
    """itemテーブルのモデル"""

    __tablename__ = "items"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    name = Column(String, nullable=False)
    price = Column(Integer)
    shop = Column(String)
    quantity = Column(Integer)
    memo = Column(Text)
    create_at = Column(DateTime, default=datetime.now)


class SessionModel(BASE):
    """sessionテーブルのモデル"""

    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True)
    session_hash = Column(String, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    expires_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now)

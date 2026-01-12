import hashlib
import os
import secrets
from datetime import datetime, timedelta

import bcrypt
import streamlit as st
from database import SessionLocal, UserModel, get_db
from mail_service import send_reset_email
from sqlalchemy.orm import Session


def cleanup_expired_tokens(db: Session) -> None:
    """期限切れのトークンを削除する"""
    try:
        now = datetime.now()
        # 期限切れのトークンを削除
        db.query(UserModel).filter(UserModel.reset_token_expires_at < now).update(
            {
                UserModel.reset_token: None,
                UserModel.reset_token_expires_at: None,
            },
            synchronize_session=False,
        )
        db.commit()
    except Exception:
        pass  # クリーンアップ失敗はメイン処理に影響させない


def cleanup_expired_guests(db: Session) -> None:
    """作成から24時間経過したゲストユーザーを削除する"""
    try:
        # 24時間前の時間を計算
        cutoff_time = datetime.now() - timedelta(hours=24)
        # 条件
        # guestユーザーかつ作成日時が24時間前以前
        deleted_count = (
            db.query(UserModel)
            .filter(
                UserModel.email.like("guest_%@example.com"),
                UserModel.created_at < cutoff_time,
            )
            .delete(synchronize_session=False)
        )

        db.commit()

        if deleted_count > 0:
            print(f"期限切れのゲストユーザーを{deleted_count}件削除しました")

    except Exception as e:
        print(f"ゲストユーザーのクリーンアップ中にエラーが発生しました: {e}")
        db.rollback()


def check_login(email: str, password: str) -> tuple[int, str] | tuple[None, None]:
    """
    メールアドレスとパスワードでログイン認証を行う
    成功すれば(user_id,username)を返し、失敗すれば(None,None)を返す
    """
    db = SessionLocal()
    try:
        user = db.query(UserModel).filter(UserModel.email == email).first()
        if user:
            # パスワードを検証
            if bcrypt.checkpw(
                password.encode("utf-8"), user.password_hash.encode("utf-8")
            ):
                cleanup_expired_tokens(db)
                cleanup_expired_guests(db)
                return int(user.id), str(user.username)
        return None, None
    except Exception as e:
        st.error(f"ログインエラー:{e}")
        return None, None
    finally:
        db.close()


def register_user(username: str, email: str, password: str) -> tuple[bool, str]:
    """
    新規ユーザーを登録する
    パスワードはハッシュ化して保存する
    戻り値:成功したかどうかのboolと、メッセージのstr
    """
    db = SessionLocal()

    try:
        if db.query(UserModel).filter(UserModel.email == email).first():
            return False, "そのメールアドレスは既に登録されています"

        # パスワードをハッシュ化
        salt = bcrypt.gensalt()
        password_hash = bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

        # ユーザーを登録
        new_user = UserModel(
            username=username,
            email=email,
            password_hash=password_hash,
        )
        db.add(new_user)
        db.commit()
        return True, "登録しました！"
    except Exception as e:
        db.rollback()
        return False, f"ユーザー登録エラー: {e}"
    finally:
        db.close()


def login_as_guest() -> tuple[int, str] | tuple[None, None]:
    """
    ゲストユーザーとしてログインする
    """
    # ランダムなゲストIDを生成
    guest_id = secrets.token_hex(4)
    username = f"Guest_{guest_id}"
    email = f"guest_{guest_id}@example.com"
    password = secrets.token_urlsafe(10)

    # 既存の登録関数を使って登録
    success, msg = register_user(username, email, password)

    if success:
        # 登録成功したら、ログインする
        user_id, user_name = check_login(email, password)
        if user_id:
            db = get_db()
            db.create_sample_items(user_id)
            return user_id, str(user_name)

    # 登録失敗
    return None, None


def change_password(
    user_id: int, current_password: str, new_password: str
) -> tuple[bool, str]:
    """
    現在のパスワードを確認し、合っていれば新しいパスワード(ハッシュ化済み)に更新する
    """
    db = SessionLocal()

    try:
        user = db.query(UserModel).filter(UserModel.id == user_id).first()
        if not user:
            return False, "ユーザーが見つかりません"

        # 現在のパスワードを検証
        if not bcrypt.checkpw(
            current_password.encode("utf-8"), user.password_hash.encode("utf-8")
        ):
            return False, "現在のパスワードが正しくありません"

        # 新しいパスワードをハッシュ化
        salt = bcrypt.gensalt()
        new_hash = bcrypt.hashpw(new_password.encode("utf-8"), salt).decode("utf-8")

        # パスワードを更新
        user.password_hash = str(new_hash)  # type: ignore
        db.commit()
        return True, "パスワードを変更しました！"
    except Exception as e:
        return False, f"エラーが発生しました:{e}"
    finally:
        db.close()


def issue_reset_token(email: str) -> bool:
    """
    リセットトークンを発行し、メールを送信する
    """
    db = SessionLocal()

    try:
        # ユーザーを検索
        user = db.query(UserModel).filter(UserModel.email == email).first()
        if not user:
            return False

        # リセットトークンを生成
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(hours=1)

        user.reset_token = str(token)  # type: ignore
        user.reset_token_expires_at = expires_at  # type: ignore
        db.commit()

        # URLを生成
        base_url = os.getenv("APP_URL", "http://localhost:8501")
        reset_url = f"{base_url}/?token={token}"

        # メールを送信
        if send_reset_email(email, reset_url):
            return True
        else:
            st.error("メールの送信に失敗しました。再度お試しください。")
            return False

    except Exception as e:
        st.error(f"リセットトークンの発行に失敗しました: {e}")
        return False
    finally:
        db.close()


def verify_reset_token(token: str) -> tuple[int, str] | None:
    """
    URLに含まれるトークンが有効(期限内かつDBに存在する)かどうかを検証する
    """
    db = SessionLocal()
    try:
        user = (
            db.query(UserModel)
            .filter(
                UserModel.reset_token == token,
                UserModel.reset_token_expires_at > datetime.now(),
            )
            .first()
        )

        if user:
            return (int(user.id), str(user.email))
        return None
    finally:
        db.close()


def reset_password(user_id: int, new_password: str) -> bool:
    """
    パスワードリセット用:新しいパスワードを設定し、リセットトークンを削除する
    """
    db = SessionLocal()
    try:
        user = db.query(UserModel).filter(UserModel.id == user_id).first()
        if user:
            salt = bcrypt.gensalt()
            user.password_hash = bcrypt.hashpw(
                new_password.encode("utf-8"), salt
            ).decode("utf-8")  # type: ignore
            user.reset_token = None  # type: ignore
            user.reset_token_expires_at = None  # type: ignore
            db.commit()
            return True
        return False
    except Exception as e:
        st.error(f"パスワードリセットに失敗しました: {e}")
        return False
    finally:
        db.close()


#
# セッション管理(永続ログイン)
#
def create_session_token(user_id: int) -> str:
    """
    セッションを作成し、クッキー用のトークンを返す。
    DBにはハッシュ化したトークンを保存する。
    """
    db = get_db()

    # トークンを生成
    raw_token = secrets.token_urlsafe(32)

    # ハッシュ化
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

    # DBに保存(有効期限は30日)
    expires_at = datetime.now() + timedelta(days=30)
    db.create_session(user_id, token_hash, expires_at)

    return raw_token


def validate_session_token(raw_token: str) -> tuple[int, str] | tuple[None, None]:
    """
    トークンを検証し、有効な場合はユーザーIDとメールアドレスを返す
    """
    if not raw_token:
        return None, None

    db = get_db()

    # ハッシュ化
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

    # 検証
    user_info = db.get_user_by_session(token_hash)

    if user_info:
        return user_info
    return None, None


def revoke_session_token(raw_token: str) -> None:
    """
    セッションを破棄する
    """
    if not raw_token:
        return

    db = get_db()

    # ハッシュ化
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

    # 破棄
    db.delete_session(token_hash)

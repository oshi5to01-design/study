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
        # UserModelテーブルの中から、
        # 有効期限(expires_at)が、今(now)より前の時間になっている人だけ絞り込む
        # 見つかった人たちのデータを、次のように一括更新する
        db.query(UserModel).filter(UserModel.reset_token_expires_at < now).update(
            {
                # リセットトークンを空(None)にする
                UserModel.reset_token: None,
                # リセットトークンの期限も空(None)にする
                UserModel.reset_token_expires_at: None,
            },
            # Python側のメモリとの同期はサボってもいいから、DB側で爆速で処理する
            synchronize_session=False,
        )
        # 変更をデータベースに正式に反映して、保存を完了
        db.commit()
    except Exception:
        pass  # クリーンアップ失敗はメイン処理に影響させない


def cleanup_expired_guests(db: Session) -> None:
    """作成から24時間経過したゲストユーザーを削除する"""
    try:
        # 今の瞬間の時間から24時間前の時間を計算
        cutoff_time = datetime.now() - timedelta(hours=24)
        # 条件
        # guestユーザーかつ作成日時が24時間前以前
        deleted_count = (
            # UserModelテーブルの中から、
            db.query(UserModel)
            .filter(
                # emailの中から、ゲストアドレスっぽいデータかつ、
                UserModel.email.like("guest_%@example.com"),
                # 作成してから24時間以上経過しているデータを絞り込む
                UserModel.created_at < cutoff_time,
            )
            # Python側のメモリとの同期はサボってもいいから、DB側で爆速で処理する
            .delete(synchronize_session=False)
        )

        # 変更をデータベースに正式に反映して、保存を完了
        db.commit()

        # 対象のデータがあれば
        if deleted_count > 0:
            print(f"期限切れのゲストユーザーを{deleted_count}件削除しました")

    # ここまででなにかエラーが起きたら
    except Exception as e:
        # コンソールにどこでどんなエラーを起きたのか表示
        print(f"ゲストユーザーのクリーンアップ中にエラーが発生しました: {e}")
        # DBに「今の途中までの変更は全部キャンセルして、直前の状態に戻して」という指示
        db.rollback()


def check_login(email: str, password: str) -> tuple[int, str] | tuple[None, None]:
    """
    メールアドレスとパスワードでログイン認証を行う
    成功すれば(user_id,username)を返し、失敗すれば(None,None)を返す
    ついでに、期限切れのトークンとゲストユーザーを一斉に削除する
    """
    db = SessionLocal()
    try:
        # UserModelテーブルを開いて、
        # その中から,メールアドレスが今探しているemailと一致する人を絞り込む
        # 条件に合う最初の一人だけを持ってきて、userに代入
        # emailはunique=Trueなはずだから、一人見つかればそれ以上探す必要がないから、
        # 見つかった瞬間検索を終えることで、データベースの負荷(無駄なスキャン)を最低限に抑える
        user = db.query(UserModel).filter(UserModel.email == email).first()
        # もし、指定されたメールアドレスを持つユーザーがDBに見つかったら
        if user:
            # パスワードを検証
            # 入力された生のパスワードと、DBに保存されているハッシュを、
            # Bcryptで照合し、正しいか確認する
            if bcrypt.checkpw(
                # 人間の文字(str)をコンピュータ用の生データ(bytes)に変換
                password.encode("utf-8"),
                user.password_hash.encode("utf-8"),
            ):
                # ログインのついでに、
                # 期限切れのトークンとゲストユーザーを一斉に削除する
                cleanup_expired_tokens(db)
                cleanup_expired_guests(db)

                # ログインに成功したので、ユーザーのIDと名前をセットにして、呼び出し元に返す
                return int(user.id), str(user.username)
        # もし、ユーザーが見つからなかった、あるいはパスワードが違っていたら、
        # 空っぽの箱(None,None)を返して終了する
        return None, None
    # ここまででなにかエラーが起きたら
    except Exception as e:
        # ユーザーの画面上にエラーが起きたことと、その詳細を表示する
        st.error(f"ログインエラー:{e}")
        # トラブルが発生したので、IDも名前もなしという空のセットを返して、処理を中断する
        return None, None
    # 何があっても、最後にデータベースとの接続を終了して、リソースを解放する
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
        # もし、UserModelテーブルの中に、登録しようとしているメールアドレスと同じ人がいたら
        # emailはunique=Trueなはずだから、一人見つかればそれ以上探す必要がないから、
        # 見つかった瞬間検索を終えることで、データベースの負荷(無駄なスキャン)を最低限に抑える
        if db.query(UserModel).filter(UserModel.email == email).first():
            # 登録失敗として、処理を終了する
            return False, "そのメールアドレスは既に登録されています"

        # パスワードをハッシュ化
        # bcryptに世界に一つだけの隠し味(ソルト)を作ってもらう
        salt = bcrypt.gensalt()
        # 人間用の文字列をコンピュータ用の生データ(バイト列)に変換する
        # 生データとソルトをかき混ぜて(ハッシュ化)、戻せない暗号のかたまりを作る
        # 出来上がった暗号のかたまりを、DBに保存しやすい普通の文字列に直す
        password_hash = bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

        # ユーザーを登録
        # UserModelクラスを使い、新しいユーザーというインスタンスを組み立てる(まだメモリ上)
        new_user = UserModel(
            username=username,
            email=email,
            password_hash=password_hash,
        )
        # dbセッションに、この新しい人を加えたいから覚えておいてと予約する
        db.add(new_user)
        # データベースに正式に反映して、保存を完了
        db.commit()
        # すべて完了したので、成功のフラグとメッセージを返す
        return True, "登録しました！"

    # ここまででなにかエラーが起きたら
    except Exception as e:
        # DBに「今の途中までの変更は全部キャンセルして、直前の状態に戻して」という指示
        db.rollback()
        # 登録失敗のメッセージとエラーの内容を通知する
        return False, f"ユーザー登録エラー: {e}"
    # 何があっても、最後にデータベースとの接続を終了して、リソースを解放する
    finally:
        db.close()


def login_as_guest() -> tuple[int, str] | tuple[None, None]:
    """
    ゲストユーザーとしてログインする
    """
    # ランダムなゲストIDを生成
    # secretsで4バイト分(16進数で8文字)のランダムな識別番号を作る
    guest_id = secrets.token_hex(4)
    # 「Guest_」の後ろにさっきの識別番号をくっつけ、ユーザー名にする
    username = f"Guest_{guest_id}"
    # メールアドレス必須のルールを守るために、識別番号を使って、偽のメールアドレスを作成
    email = f"guest_{guest_id}@example.com"
    # その場限りの、安全でランダムなパスワードを自動生成する
    password = secrets.token_urlsafe(10)

    # 既存の登録関数を使って登録
    # 作成したランダムなユーザー名、メールアドレス、パスワードを登録する
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
        # UserModelテーブルを開いて、
        # その中から,メールアドレスが今探しているemailと一致する人を絞り込む
        # 条件に合う最初の一人だけを持ってきて、userに代入
        # emailはunique=Trueなはずだから、一人見つかればそれ以上探す必要がないから、
        # 見つかった瞬間検索を終えることで、データベースの負荷(無駄なスキャン)を最低限に抑える
        user = db.query(UserModel).filter(UserModel.email == email).first()

        # もしuserが空(None)なら(名簿になかったら)、切り上げる
        if not user:
            return False

        # リセットトークンを生成
        # secrets(予測不可能な乱数生成)に頼んで、32バイト分の長さを持つ、
        # ランダムで安全な合言葉(トークン)を作ってもらう
        # urlsafe:URLに使っても壊れない( / や + などの記号が含まれない)文字列にする
        token = secrets.token_urlsafe(32)

        # 今この瞬間から、ちょうど1時間足した時間を有効期限(寿命)として計算する
        expires_at = datetime.now() + timedelta(hours=1)

        # 見つかったユーザー情報にさっき作った合言葉と有効期限を書き込む
        user.reset_token = str(token)  # type: ignore
        user.reset_token_expires_at = expires_at  # type: ignore

        # 変更をデータベースに正式に反映して、保存を完了
        db.commit()

        # URLを生成
        # OSにAPP_URL(アプリの住所)という名前のデータが入っているかどうか
        # 入っていたらその住所を使う
        # 入っていなかったらとりあえず自分の開発環境("http://localhost:8501")を仮住所として使用
        # os.getenvの第2引数(デフォルト値)にローカルのURLをいれることで、
        # 本番環境ではAPP_URL、開発環境ではローカルのURLがコードを書き換えることなく切替可能
        base_url = os.getenv("APP_URL", "http://localhost:8501")

        # 特定した住所のあとに、『/?token=』という印を付け、生成した合言葉(token)を合体させる
        # クエリパラメータ：Webサイトを開くと同時にサーバーに本人確認ができるデータを手渡す
        reset_url = f"{base_url}/?token={token}"

        # メールを送信
        if send_reset_email(email, reset_url):
            return True
        else:
            # 外部との通信はネットワークトラブルなどで失敗する可能性があるため、
            # 必ず戻り値による成否判定を行う
            # 失敗をユーザーに知らせるため必ずユーザーに表示する
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

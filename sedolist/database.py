import os
from datetime import datetime
from typing import Any

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
    inspect,
    text,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()


#
# SQLAlchemyの設定(ORM)
#
# データベースURLの構築
DATABASE_URL = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASS')}@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"
# データベースエンジンの作成
# データベース接続センターを作る
# 常設の回線が10本、混雑時には追加で20本繋げていいよ
engine = create_engine(DATABASE_URL, pool_size=10, max_overflow=20)
# セッションファクトリーの作成
# autocommit=False：db.commitをするまで変更の確定はさせない、ロールバックができる
# autoflush=False：準備ができたら自分からデータを送るから勝手に送らないで
# autoflush=Trueだとquery(検索)のたびにSQLAlchemyが下書きを送ってしまう
# bind=engine：接続先の指定、engineに繋ぐ
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
# 親クラス
# SQLAlchemyの機能でこのクラスを継承すれば自動的にデータベースのテーブルになれるというクラスを作る
BASE: Any = declarative_base()


#
# モデル定義
#
class UserModel(BASE):
    """userテーブルのモデル"""

    __tablename__ = "users"

    # idの列(カラム)、数値型、プライマリーキー
    id = Column(Integer, primary_key=True)
    # 文字列型、空欄は認めない
    username = Column(String, nullable=False)
    # 文字列型、重複は認めない、空欄も認めない
    email = Column(String, unique=True, nullable=False)
    # パスワードはハッシュしてわからなくしてから保存
    # 文字列型、空欄は認めない
    password_hash = Column(String, nullable=False)
    # パスワードリセット用のトークン
    # 文字列型、空欄でもいい
    reset_token = Column(String, nullable=True)
    # リセットトークンの有効期限
    # デートタイム型、空欄でもいい
    reset_token_expires_at = Column(DateTime, nullable=True)
    # アカウントの作成日時、デートタイム、作成した時間
    # ゲストユーザーは24時間以上経過していたら削除対象
    created_at = Column(DateTime, default=datetime.now)


class ItemModel(BASE):
    """itemテーブルのモデル"""

    __tablename__ = "items"

    id = Column(Integer, primary_key=True)
    # usersテーブルのidとつながっている
    # CASCADE：usersのidに紐づいて消された場合こちらも連動してデータ削除
    # index=Trueを設定すると検索早くなっていいかも
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
    # セッションをハッシュ化、重複不可
    # インデックス書き込みがちょい遅くなるけど読み込みが早くなる
    session_hash = Column(String, unique=True, index=True)
    # usersテーブルのidとつながっている
    # CASCADE：usersのidに紐づいて消された場合こちらも連動してデータ削除
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    expires_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now)


#
# DatabaseManagerクラス
#
class DatabaseManager:
    """データベース接続と操作を管理するクラス"""

    def __init__(self):
        """初期化:コネクションプールの作成とマイグレーション"""

        # sessionテーブルのスキーマ確認
        # データベースの接続センター(engine)に対して、調査員(inspector)が構造を調査する
        inspector = inspect(engine)

        # sessionsという名前のテーブルが、
        # 実際にデータベースの中に存在するかどうかinspectorに確認させる
        if inspector.has_table("sessions"):
            # sessionsテーブルにあるすべてのカラムの情報を取ってきて、
            # その中からnameだけを抜き出してリストにまとめる
            columns = [c["name"] for c in inspector.get_columns("sessions")]

            # 旧カラム(session_id)があり、新カラム(session_hash)がない場合は再作成
            # データベースの構造をチェックして、古い項目のままで、
            # 新しい項目がまだ作られていないという状態だったら
            # 自動的にテーブルのリフォーム(マイグレーション)をすることにする
            if "session_id" in columns and "session_hash" not in columns:
                print("sessionテーブルのマイグレーションを実行します")
                # ワンチャンミスるかも
                try:
                    # ORMを通さず、データベース接続センター(engine)から直接生の回線を１本借りてくる
                    # 終わったら勝手にリソース解放(with)
                    with engine.connect() as conn:
                        # sessionsテーブルを中身もろとも消せという命令
                        # ここはSQLAlchemy使わず生のSQL
                        conn.execute(text("DROP TABLE sessions CASCADE"))
                        # 削除を確定
                        conn.commit()
                except Exception as e:
                    print(f"マイグレーション中にエラーが発生しました: {e}")

        # テーブルの作成
        # BASE(設計図)に登録されているすべてのテーブルを、
        # engine(指定の場所)に作成する指示
        # 実行するたびデータベースの中身を確認し、存在しないテーブルだけ作成してくれる
        # 作るテーブルが既に作られている場合はなにもしない
        # 何度実行しても、最終的にはすべてのテーブルが揃っている状態になる(べき等性)
        BASE.metadata.create_all(bind=engine)

    # データベースの窓口をgetする関数
    def get_db(self):
        """セッションを作成して返す"""
        # 前に作ったSessionLocal(窓口の設計図)を実行して、窓口を一つ作って呼び出し元に渡す
        # あちこちにSessionLocal()と書かなくてよくなる(カプセル化)
        return SessionLocal()

    #
    # セッション管理関連
    #
    def create_session(
        self, user_id: int, session_hash: str, expires_at: datetime
    ) -> None:
        """新しいセッションを登録する"""
        # get_dbを呼び出して窓口を一つ確保する
        db = self.get_db()
        try:
            # SessionModelテーブルに、誰の(useer_id)、合言葉は(session_hash)、
            # 有効期限は(expires_at)という情報を仮記入し、ew_sessionに代入
            new_session = SessionModel(
                user_id=user_id,
                session_hash=session_hash,
                expires_at=expires_at,
            )
            # その情報をDBに保存するよう予約
            db.add(new_session)
            # DBの保存を確定させる
            db.commit()
        # もし、失敗したら
        except Exception as e:
            # 変更を破棄し、元の状態に戻す
            db.rollback()
            # エラーの報告とエラー内容の表示
            print(f"セッションの作成中にエラーが発生しました: {e}")
        finally:
            db.close()

    def get_user_by_session(self, session_hash: str) -> tuple[int, str] | None:
        """セッションからユーザーIDとユーザー名を取得する"""

        # get_dbを呼び出して通信の窓口を一つ確保する
        db = self.get_db()

        # データベースに問い合わせ(外への通信)をするから
        # ワンチャンネットが切れてたりDBが眠ってるかもしれないというときの備え
        try:
            # セッションを検索
            session = (
                # SessionModelテーブルを調べておくれ
                db.query(SessionModel)
                # 条件にマッチするか調べる
                .filter(
                    # 記録されている合言葉(hash)と、今ユーザーが提示してきた合言葉が一致するか
                    SessionModel.session_hash == session_hash,
                    # かつ、合言葉の有効期限(expires_at)が、今現在の時刻より未来になっているか
                    # 今より前なら期限切れ
                    SessionModel.expires_at > datetime.now(),
                )
                # 条件にマッチするデータを見つけたら最初の1件だけ取り出してsessionという変数に入れてね
                .first()
            )

            # もしさっきのセッション（合言葉の一致と有効期限の確認）がTrueなら
            if session:
                user = (
                    # UserModelテーブルを調べる
                    # UserModelテーブルのidと今入ってきたユーザーのidが一致するか確認
                    # マッチする最初の一人を見つけて、userに代入
                    db.query(UserModel).filter(UserModel.id == session.user_id).first()
                )
                # 二度手間で入ってきたユーザーの確認をしている
                # SessionModelテーブルにはデータはあるがUserModelテーブルにはいない
                # みたいな幽霊データを対策するための処理
                # joinして1回でもできるちゃできる
                # 一応二度手間のままにしておく、そのうち直してもいい

                # もしユーザーのidが一致するなら
                if user:
                    # ユーザーIDとユーザー名を返す
                    return int(user.id), str(user.username)
            # セッションが一致しなかったらNoneを返す
            return None

        # 成功しようが失敗しようが、
        finally:
            # 最終的にデータベースとの通信を閉じる
            db.close()

    def delete_session(self, session_hash: str) -> None:
        """セッションを削除する"""
        # ログアウト時、パスワード変更時、アカウント削除時に呼び出して
        # 通行許可証を削除する
        # DBに不要なゴミデータを貯めないため

        # get_dbを呼び出して通信の窓口を一つ確保する
        db = self.get_db()
        # DBとの通信失敗するかもだけどよろしく
        try:
            # SessionModelテーブルを調べてみて
            # 合言葉が一致するデータを消去して
            db.query(SessionModel).filter(
                SessionModel.session_hash == session_hash
            ).delete()
            # 変更を確定させる
            db.commit()
        # もし、失敗したら
        except Exception:
            # 変更を破棄して、なかったことにする
            db.rollback()
        # 成功しようが、失敗しようが、
        finally:
            # 最終的にデータベースとの通信を閉じる
            db.close()

    def cleanup_expired_sessions(self) -> None:
        """期限切れのセッションを削除する"""
        # get_dbを呼び出して通信の窓口を一つ確保する
        db = self.get_db()
        # ワンチャンミスるかもだけど落ち着いて
        try:
            # SessionModelテーブルを調べてみて
            # 有効期限が切れているセッションを探して削除する
            # expires>_atが現在時刻より前なら期限切れ
            db.query(SessionModel).filter(
                SessionModel.expires_at < datetime.now()
            ).delete()
            # 変更を確定して保存
            db.commit()
        # 失敗したときは、
        except Exception:
            # 何事もなかったかのように終了する
            pass
        # 成功しようが、失敗しようが、
        finally:
            # 最後はデータベースとの通信を閉じる
            db.close()

    #
    # 在庫データ関連
    #
    def load_items(self, user_id: int) -> pd.DataFrame:
        """指定されたユーザーの在庫データをDataFrameで取得する"""

        # itemsテーブルの中から、user_idがこの人と一致する
        # すべての列の情報を探してきて降順で並べてね
        query = "SELECT * FROM items WHERE user_id = %s ORDER BY id DESC"

        # データベース接続センターに繋げて、とりあえずconnって呼ぶ
        # 最後には、自動的に閉じてね
        with engine.connect() as conn:
            # 取ってきたアイテム情報と、接続の情報と、ユーザーIDを
            # pandasのread_sqlで読み取って、dfに代入
            # タプルやリストとしてparamsの引数に入れる必要があるから,が必要
            df = pd.read_sql(query, conn, params=(user_id,))

        # 出来上がったdfを返す
        return df

    def register_item(
        self,
        user_id: int,
        name: str,
        price: int,
        quantity: int,
        shop: str | None,
        memo: str | None,
    ) -> None:
        """新しい在庫データを登録する"""
        # get_dbを呼び出して通信の窓口を一つ確保する
        db = self.get_db()
        # ワンチャンミスるかもだけど
        try:
            # 追加したいアイテムの情報たち
            new_item = ItemModel(
                user_id=user_id,
                name=name,
                price=price,
                shop=shop,
                quantity=quantity,
                memo=memo,
            )
            # データベースに加えたいと仮記入
            db.add(new_item)
            # 変更を確定し、データベースに保存
            db.commit()
            # ユーザーへ向けて登録成功のメッセージを表示
            st.success(f"{name}を登録しました")
        # もし、失敗したら
        except Exception as e:
            # ここまでの変更はなかったことにして、元に戻して
            db.rollback()
            # ユーザーに失敗したとメッセージを表示
            st.error(f"登録エラー: {e}")
        # 成功しても、失敗しても、
        finally:
            # 最終的にはデータベースとの通信を閉じる
            db.close()

    #
    # サンプルデータ作成（ゲスト用）
    #
    def create_sample_items(self, user_id: int) -> None:
        """ゲストユーザー用のサンプルデータを登録する"""
        # get_dbを呼び出して通信の窓口を一つ確保する
        db = self.get_db()

        # サンプルデータのリスト
        # いくつかのサンプルデータをsamplesに代入
        samples = [
            {
                "name": "ゲーミングマウス G502",
                "price": 5800,
                "shop": "Amazon",
                "quantity": 3,
                "memo": "人気商品。セール時に確保。",
            },
            {
                "name": "メカニカルキーボード 赤軸",
                "price": 12000,
                "shop": "楽天",
                "quantity": 1,
                "memo": "箱に少し傷あり。",
            },
            {
                "name": "USB-C ハブ 7-in-1",
                "price": 3500,
                "shop": "家電量販店A",
                "quantity": 5,
                "memo": "",
            },
            {
                "name": "ノイズキャンセリングヘッドホン",
                "price": 24000,
                "shop": "Amazon",
                "quantity": 2,
                "memo": "ブラックフライデー仕入れ",
            },
            {
                "name": "スマホスタンド (アルミ)",
                "price": 1500,
                "shop": "100均一(高額枠)",
                "quantity": 10,
                "memo": "回転率よし",
            },
            {
                "name": "4Kモニター 27インチ",
                "price": 32000,
                "shop": "中古PCショップ",
                "quantity": 1,
                "memo": "ドット抜けなし確認済み",
            },
            {
                "name": "HDMIケーブル 2m",
                "price": 800,
                "shop": "Amazon",
                "quantity": 20,
                "memo": "ついで買い狙い",
            },
            {
                "name": "Webカメラ 1080p",
                "price": 4500,
                "shop": "メルカリ",
                "quantity": 0,
                "memo": "売り切れ。再入荷待ち。",
            },
            {
                "name": "デスクマット (大型)",
                "price": 2200,
                "shop": "AliExpress",
                "quantity": 4,
                "memo": "到着まで2週間かかった",
            },
            {
                "name": "LEDデスクライト",
                "price": 3800,
                "shop": "IKEA",
                "quantity": 2,
                "memo": "",
            },
        ]

        try:
            # samplesのデータたちをitemsテーブルに登録していく
            for item in samples:
                new_item = ItemModel(
                    user_id=user_id,
                    name=item["name"],
                    price=item["price"],
                    shop=item["shop"],
                    quantity=item["quantity"],
                    memo=item["memo"],
                )
                # データベースに加えようと仮記入
                db.add(new_item)
            # 変更を確定し、データベースに保存
            db.commit()
        # もし、失敗したら、
        except Exception as e:
            # 変更をなかったことにして、元に戻す
            db.rollback()
            # エラーメッセージとエラーの内容をコンソールに表示
            print(f"サンプルデータ登録エラー: {e}")
        # 成功しようが、失敗しようが、
        finally:
            # 最終的に、データベースとの通信を閉じる
            db.close()

    def update_item(self, item_id: int, col_name: str, new_value: Any) -> None:
        """指定された在庫データを更新する"""
        # get_dbを呼び出して通信の窓口を一つ確保する
        db = self.get_db()
        try:
            # numpyの型変更対策
            # hasattr：こういうデータ持ってる？
            # streamlitやpandasからくる数値は
            # int64とかのnumpyの型になってたりするから
            # item()を使ってPython標準のint型へ変換し、エラーを防ぐ
            # item()：中にある数字をPython標準の型に変換する
            if hasattr(new_value, "item"):
                new_value = new_value.item()
            if hasattr(item_id, "item"):
                item_id = item_id.item()

            # itemsテーブルを調べて、
            # そのitem_idと一致する最初の一つを見つけてきてitemに代入
            item = db.query(ItemModel).filter(ItemModel.id == item_id).first()
            # もし、あったら、
            if item:
                # そのitemの変更したいカラムに新しい値をセット
                # 指定されたカラムに基づいて、オブジェクトの値を動的に更新
                # よって、どのカラムを変更するにしても、この1行で処理が可能
                # setattrすごいね
                # setsttrがdb.add()みたいな仮記入も行ってくれてる
                setattr(item, col_name, new_value)
                # 変更を確定し、データベースに保存
                db.commit()
        # もし、失敗したら、
        except Exception as e:
            # 変更をなかったことにして、元に戻す
            db.rollback()
            # ユーザーにエラーメッセージとエラー内容を表示
            st.error(f"更新エラー: {e}")
        # 成功しようが、失敗しようが、
        finally:
            # 最終的に、データベースとの通信を閉じる
            db.close()

    def delete_item(self, item_id: int) -> None:
        """指定された在庫データを削除する"""
        # get_dbを呼び出して通信の窓口を一つ確保する
        db = self.get_db()
        try:
            # numpyの型変更対策
            # numpyの型形式(int64とか)をPython標準のint型に変換
            if hasattr(item_id, "item"):
                item_id = item_id.item()
            # itemsテーブルを調べて、
            # item_idが一致するデータを見つけたら削除しようとする
            db.query(ItemModel).filter(ItemModel.id == item_id).delete()
            # 変更を確定し、データベースに保存
            db.commit()

        # もし、失敗したら、
        except Exception as e:
            # 変更をなかったことにして、元に戻す
            db.rollback()
            # エラーメッセージとエラー内容をユーザーに表示
            st.error(f"削除エラー: {e}")
        # 成功しようが、失敗しようが、
        finally:
            # 最終的に、データベースとの通信を閉じる
            db.close()

    #
    # ユーザー情報更新関連
    #
    def delete_user_account(self, user_id: int) -> bool:
        """指定されたユーザーのアカウントを削除する"""
        # get_dbを呼び出して、通信の窓口を一つ確保する
        db = self.get_db()
        try:
            # usersテーブルを調べて、ユーザーIDが一致する人を探して、消してね
            db.query(UserModel).filter(UserModel.id == user_id).delete()
            # 変更を確定し、データベースに保存
            db.commit()
            # 処理が成功したら、Trueを返す
            return True
        # もし、失敗したら、
        except Exception as e:
            # エラーメッセージとエラー内容をユーザーに表示
            st.error(f"退会処理エラー: {e}")
            # Falseを返す
            return False
        # 成功しようが、失敗しようが、
        finally:
            # 最終的に、データベースとの通信を閉じる
            db.close()

    def update_username(self, user_id: int, new_username: str) -> bool:
        """指定されたユーザーの名前を更新する"""
        # get_dbを呼び出して、通信の窓口を一つ確保する
        db = self.get_db()
        try:
            # usersテーブルを調べて、user_idが一致する最初の一人を見つける
            user = db.query(UserModel).filter(UserModel.id == user_id).first()
            # もし、いたら、
            if user:
                # DBのユーザーネームを新しいユーザーネームと差し替え
                user.username = new_username
                # 変更を確定し、DBに保存
                db.commit()
                # 問題なく完了したら、Trueを返す
                return True
            # いなかったら、Falseを返す
            return False
        # もし、失敗したら、
        except Exception as e:
            # エラーメッセージとエラー内容をユーザーに表示
            st.error(f"更新エラー: {e}")
            # Falseを返す
            return False
        # 成功しようが、失敗しようが、
        finally:
            # 最終的に、DBとの通信を閉じる
            db.close()

    def get_user_email(self, user_id: int) -> str:
        """指定されたユーザーのメールアドレスを取得する"""
        # get_dbを呼び出して、通信の窓口を一つ確保する
        db = self.get_db()
        try:
            # usersテーブルを調べて、user_idが一致する最初の一人を見つける
            user = db.query(UserModel).filter(UserModel.id == user_id).first()
            # そのユーザーのメールアドレスを返す
            # if user:
            # return user.email
            # else:
            # return ""  の短縮した書き方
            return user.email if user else ""
        # 成功しようが、失敗しようが、
        finally:
            # 最終的に、DBとの通信を閉じる
            db.close()

    def update_email(self, user_id: int, new_email: str) -> tuple[bool, str]:
        """指定されたユーザーのメールアドレスを更新する"""
        # get_dbを呼び出して、通信の窓口を一つ確保する
        db = self.get_db()
        try:
            # usersテーブルを調べて、user_idが一致する最初の一人を見つける
            user = db.query(UserModel).filter(UserModel.id == user_id).first()
            # もし、いたら、
            if user:
                # DBのメールアドレスを新しいメールアドレスに変更しよう
                user.email = new_email
                # 変更を確定し、DBに保存
                db.commit()
                # 成功したら、Trueを返して、メッセージを表示
                return True, "メールアドレスを更新しました。"
            # いなかったら、Falseを返して、メッセージを表示
            return False, "ユーザーが見つかりませんでした。"

        # 登録しようとしたメールアドレスに重複があったら、
        except IntegrityError:
            # 変更をなかったことにして、元に戻す
            db.rollback()
            # Falseを返して、メッセージを表示
            return False, "そのメールアドレスは既に使用されています。"

        # もし、失敗したら、
        except Exception as e:
            # なかったことにして、元に戻す
            db.rollback()
            # Falseを返して、エラーメッセージとエラー内容を表示
            return False, f"更新エラー: {e}"
        # 成功しようが、失敗しようが、
        finally:
            # 最終的に、DBとの通信を閉じる
            db.close()


#
# シングルトン(一つだけ作る)管理用関数
#
@st.cache_resource
def get_db():
    """アプリ全体で一つだけのDatabaseManagerインスタンスを返す"""
    return DatabaseManager()
    # 最初にDBとの接続を作って、それを使いまわす
    # Streamlitはボタンを押す度コードが実行されて繋ぎなおしてしまうから
    # これをしないと逐一DBとの接続を作ってパンクする

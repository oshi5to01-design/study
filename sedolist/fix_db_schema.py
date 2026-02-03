import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

# データベースURLの構築
DATABASE_URL = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASS')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"


# 設計図(schema)を正しい状態に直す(fix)
def fix_schema():
    # DATABASE_URL(DBの住所)の情報を使って、データベース接続センター(engine)を作る
    engine = create_engine(DATABASE_URL)

    # engineから作業用の直通回線を１本借りてくる
    with engine.connect() as conn:
        # コンソールに今からsessionsテーブルを解体すると表示
        print("sessionsテーブルを削除しています..")

        # DROP TABLE：テーブルを中身のデータもろとも削除する
        # IF EXISTS：テーブルがあるなら消す、ないならなにもしない
        # CASCADE：関連するすべてを芋づる式に消し去る
        conn.execute(text("DROP TABLE IF EXISTS sessions CASCADE"))

        # 消すけど、次アプリ起動時新しく作り直すと表示
        print("次回のアプリ起動時に、sessionsテーブルが再作成されます...")

        # app.pyでBase.metadata.create_all()を呼び出すことでテーブルが再作成される
        # テーブル消去を確定
        conn.commit()

    print("完了！")


if __name__ == "__main__":
    fix_schema()

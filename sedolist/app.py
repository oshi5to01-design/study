import time

# import auth
# import ai_logic as ai
import extra_streamlit_components as stx  # type: ignore

# from datetime import datetime
import streamlit as st
from database import get_db

#
# ページ設定
#
st.set_page_config(page_title="せどりすと", page_icon="🗃")


#
# 初期化
#
# アプリ起動時に一度だけDB管理クラスのインスタンスを作成
db = get_db()


#
# クッキーマネージャーの初期化
#
cookie_manager = stx.CookieManager()


#
# UI用ヘルパー関数
#
def clear_form_state():
    """フォームの入力状態をクリアする"""
    st.session_state.input_name = ""
    st.session_state.input_price = 0
    st.session_state.input_quantity = 1
    st.session_state.input_shop = ""
    st.session_state.input_memo = ""


#
# 高速化エリア(Fragment)
#
@st.fragment
def show_inventory_screen() -> None:
    """在庫一覧画面を表示する"""
    st.subheader("在庫一覧")

    # DBモジュールからデータ取得
    df_items = db.load_items(st.session_state.user_id)

    view_mode = st.radio("表示モード", ["表形式", "カード形式"], horizontal=True)

    if view_mode == "表形式":
        # 表示用に整形
        display_df = df_items[
            ["id", "name", "price", "shop", "quantity", "memo", "created_at"]
        ]
        display_df.columns = [
            "ID",
            "商品名",
            "価格",
            "店舗",
            "在庫数",
            "メモ",
            "登録日",
        ]

        st.data_editor(
            display_df,
            key="editor",
            column_config={
                "ID": st.column_config.NumberColumn(disabled=True),
                "登録日": st.column_config.DatetimeColumn(
                    disabled=True, format="YYYY-MM-DD HH:mm"
                ),
            },
            use_container_width=True,
            hide_index=True,
        )

        # 更新処理
        if st.session_state.editor:
            changes = st.session_state.editor
            needs_rerun = False

            if changes["edited_rows"]:
                for index, updates in changes["edited_rows"].items():
                    item_id = df_items.iloc[index]["id"]
                    col_map = {
                        "商品名": "name",
                        "価格": "price",
                        "店舗": "shop",
                        "在庫数": "quantity",
                        "メモ": "memo",
                    }

                    for col_name, new_value in updates.items():
                        db_col = col_map.get(col_name)
                        if db_col:
                            # dbモジュールで更新
                            db.update_item(item_id, db_col, new_value)
                            st.toast("更新しました")
                needs_rerun = True

            if changes["deleted_rows"]:
                for index in changes["deleted_rows"]:
                    item_id = df_items.iloc[index]["id"]
                    # dbモジュールで削除
                    db.delete_item(item_id)
                    st.toast("削除しました")
                needs_rerun = True

            if needs_rerun:
                time.sleep(0.5)
                st.rerun()

    else:
        # カード形式
        st.write("スマホ編集モード。タップして詳細を開く")
        for index, row in df_items.iterrows():
            item_id = row["id"]
            with st.expander(f"{row['name']} (残:{row['quantity']}個)"):
                new_name = st.text_input(
                    "商品名", value=row["name"], key=f"name_{item_id}"
                )
                col1, col2 = st.columns(2)
                with col1:
                    new_price = st.number_input(
                        "価格", value=row["price"], step=100, key=f"price_{item_id}"
                    )
                with col2:
                    new_quantity = st.number_input(
                        "在庫数", value=row["quantity"], step=1, key=f"qty_{item_id}"
                    )
                new_shop = st.text_input(
                    "店舗", value=row["shop"], key=f"shop_{item_id}"
                )
                new_memo = st.text_area(
                    "メモ", value=row["memo"], key=f"memo_{item_id}"
                )

                btn_col1, btn_col2 = st.columns(2)
                with btn_col1:
                    if st.button(
                        "更新", key=f"upd_{item_id}", use_container_width=True
                    ):
                        # dbモジュールで更新
                        db.update_item(item_id, "name", new_name)
                        db.update_item(item_id, "price", new_price)
                        db.update_item(item_id, "quantity", new_quantity)
                        db.update_item(item_id, "shop", new_shop)
                        db.update_item(item_id, "memo", new_memo)
                        st.toast("更新しました")
                        st.rerun()
                with btn_col2:
                    if st.button(
                        "削除",
                        key=f"del_{item_id}",
                        type="primary",
                        use_container_width=True,
                    ):
                        # dbモジュールで削除
                        db.delete_item(item_id)
                        st.toast("削除しました")
                        st.rerun()

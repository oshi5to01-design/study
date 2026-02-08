import time
from datetime import datetime

import ai_logic as ai
import auth
import extra_streamlit_components as stx  # type: ignore
import streamlit as st
from database import get_db

# -----------------------------------------------
# ページ設定
# -----------------------------------------------
st.set_page_config(page_title="せどりすと", page_icon="📦")


# -----------------------------------------------
# 初期化
# -----------------------------------------------
# アプリ起動時に一度だけDB管理クラスのインスタンスを作成
db = get_db()


# -----------------------------------------------
# クッキーマネージャーの初期化
# -----------------------------------------------
cookie_manager = stx.CookieManager()


# ----------------------------------------------
# UI用ヘルパー関数
# ----------------------------------------------
def clear_form_state() -> None:
    """入力フォームをクリアするコールバック関数"""
    st.session_state.input_name = ""
    st.session_state.input_price = 0
    st.session_state.input_quantity = 1
    st.session_state.input_shop = ""
    st.session_state.input_memo = ""


# -----------------------------------------------
# 高速化エリア(Fragment)
# -----------------------------------------------
@st.fragment
def show_inventory_screen() -> None:
    """
    在庫一覧画面(部分更新対応)

    Notes:
        PCでは表形式、スマホではカード形式で表示する
        部分更新対応のために、st.fragmentを使用する
        表示速度を上げるためサイドバーなど更新の必要がないエリアを更新しないようにする
    """
    st.subheader("現在の在庫一覧")

    # 表示モードを選択
    view_mode = st.radio(
        "表示モード",
        ["表形式（PC向け）", "カード形式（スマホ向け）"],
        horizontal=True,
        key="view_mode_state",
    )

    # 変数・検索
    if "cursor_history" not in st.session_state:
        st.session_state.cursor_history = [None]
    if "active_search" not in st.session_state:
        st.session_state.active_search = ""

    col_search, col_btn = st.columns([4, 1])
    with col_search:
        search_input = st.text_input(
            "検索",
            value=st.session_state.active_search,
            placeholder="商品名を入力・・・",
            label_visibility="collapsed",
        )
    with col_btn:
        if st.button("検索", use_container_width=True):
            if search_input != st.session_state.active_search:
                st.session_state.active_search = search_input
                st.session_state.cursor_history = [None]
                st.rerun()

    current_cursor = st.session_state.cursor_history[-1]
    LIMIT = 5  # 本番では50にする予定

    df_items = db.load_items(
        st.session_state.user_id,
        limit=LIMIT,
        last_id=current_cursor,
        search_query=st.session_state.active_search,
    )

    # ページ送りボタンを表示する内部関数
    def render_pagination(location_key: str):
        """
        指定された位置にページ送りボタンを表示する

        Args:
            location_key (str): ボタンの位置を示すキー

        Returns:
            None
        """
        col_prev, _, col_next = st.columns([1, 2, 1])

        with col_prev:
            # 履歴が１個より多いなら前のページへを表示
            if len(st.session_state.cursor_history) > 1:
                if st.button(
                    "前のページ", key=f"prev_{location_key}", use_container_width=True
                ):
                    st.session_state.cursor_history.pop()
                    st.rerun()

        with col_next:
            # データが満タンなら次のページへを表示
            if len(df_items) == LIMIT:
                if st.button(
                    "次のページ", key=f"next_{location_key}", use_container_width=True
                ):
                    last_id = int(df_items.iloc[-1]["id"])
                    st.session_state.cursor_history.append(last_id)
                    st.rerun()

    # ページ送りボタンを表示
    render_pagination("top")

    # データ表示エリア
    if view_mode == "表形式（PC向け）":
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
                            st.toast("更新しました！")
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
        # スマホ向けカード表示
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
                        st.toast("更新しました！")
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

    # ページ送りボタンを表示
    render_pagination("bottom")


@st.fragment
def show_register_screen() -> None:
    """
    仕入れ登録画面(部分更新対応)

    Notes:
        カメラを起動し、値札を撮影してGeminiで解析する
        解析結果を入力する
        数量、店舗、メモ等を手入力し、DBに登録する
    """
    # セッションステート初期化
    if "input_name" not in st.session_state:
        st.session_state.input_name = ""
    if "input_price" not in st.session_state:
        st.session_state.input_price = 0
    if "input_quantity" not in st.session_state:
        st.session_state.input_quantity = 1
    if "input_shop" not in st.session_state:
        st.session_state.input_shop = ""
    if "input_memo" not in st.session_state:
        st.session_state.input_memo = ""

    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader("新規登録")
    with col2:
        use_camera = st.toggle("カメラ起動")

    if use_camera:
        picture = st.camera_input("値札を撮影")
        if picture:
            # aiモジュールで解析
            result = ai.analyze_image_with_gemini(picture)
            if result:
                st.success("読み取り成功")
                st.session_state.input_name = result.get("name", "")
                st.session_state.input_price = result.get("price", 0)

    with st.form("register_form"):
        name = st.text_input("商品名", key="input_name")
        col1, col2 = st.columns(2)
        with col1:
            price = st.number_input(
                "仕入れ価格", min_value=0, step=100, key="input_price"
            )
        with col2:
            quantity = st.number_input("個数", min_value=1, key="input_quantity")
        shop = st.text_input("仕入先（店舗名）", key="input_shop")
        memo = st.text_area("メモ", key="input_memo")

        btn_col1, btn_col2 = st.columns([1, 1])
        with btn_col1:
            submitted = st.form_submit_button(
                "登録する", type="primary", use_container_width=True
            )
        with btn_col2:
            st.form_submit_button(
                "入力をクリア", on_click=clear_form_state, use_container_width=True
            )

        if submitted:
            if name:
                # dbモジュールで登録
                db.register_item(
                    st.session_state.user_id, name, price, quantity, shop, memo
                )
                st.toast("登録しました！")
                time.sleep(1)
                st.rerun()
            else:
                st.warning("商品名は必須です！")


# ----------------------------------------------
# メイン処理開始
# ----------------------------------------------

# セッションステートの初期化
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.session_state.username = ""


# ---------------------------------------------
# 永続ログインチェック
# ---------------------------------------------
# バックグラウンドに移ったとき等にログインし直しにならないようにする
# セッショントークンをクッキーから取得して、
# 有効期限を確認して、
# 有効ならログイン状態を維持する

# セッショントークンが無効または存在しない場合は、
# ログインページにリダイレクトする

if not st.session_state.logged_in:
    # クッキーからセッショントークンを取得
    token_cookie = cookie_manager.get("session_token")
    if token_cookie:
        user_id, username = auth.validate_session_token(token_cookie)
        if user_id:
            st.session_state.logged_in = True
            st.session_state.user_id = user_id
            st.session_state.username = username
            st.toast(f"お帰りなさい、{username}さん (自動ログイン)")


# URLからトークンを取得 (?token=xxxxx)
query_params = st.query_params
reset_token = query_params.get("token", None)

# ==========================================
# パターンA：パスワード再設定モード
# ==========================================
# URLからトークンを取得して、
# トークン検証して、
# トークンが有効ならパスワード再設定ページを表示する

if reset_token:
    st.title("パスワード再設定")

    # authモジュールを使ってトークン検証
    user = auth.verify_reset_token(reset_token)

    if user:
        st.success(f"本人確認が完了しました。\n対象アカウント: {user[1]}")
        with st.form("new_password_form"):
            new_pw = st.text_input("新しいパスワード", type="password")
            submitted = st.form_submit_button("変更する")

            if submitted:
                if not new_pw:
                    st.warning("パスワードを入力してください")
                else:
                    # authモジュールでパスワード更新
                    if auth.reset_password(user[0], new_pw):
                        st.success("パスワードを変更しました！")
                        st.info("ログイン画面に戻ります")
                        time.sleep(3)
                        st.query_params.clear()
                        st.rerun()
    else:
        st.error("このリンクは無効か、有効期限が切れています。")
        if st.button("ログイン画面へ戻る"):
            st.query_params.clear()
            st.rerun()

    st.stop()  # ここで止める

# ==========================================
# パターンB：ログイン画面 (未ログイン時)
# ==========================================
# ログイン画面
# 未ログイン時のみ表示
# ログインフォームと新規登録フォームとパスワード再設定フォームを表示

# ゲストログイン機能:
# ゲストログインすると、サンプルデータを表示する
# 24時間で削除される

if not st.session_state.logged_in:
    st.title("ログイン")

    tab1, tab2, tab3 = st.tabs(["ログイン", "新規登録", "パスワードを忘れた場合"])

    # --- ログイン ---
    with tab1:
        with st.form("login_form"):
            email = st.text_input("メールアドレス")
            show_password = st.checkbox("パスワードを表示して入力する")
            if show_password:
                password = st.text_input("パスワード", key="pw_visible")
            else:
                password = st.text_input("パスワード", type="password", key="pw_hidden")

            submitted = st.form_submit_button("ログイン")

            if submitted:
                # authモジュールでログインチェック
                user_id, username = auth.check_login(email, password)
                if user_id:
                    st.session_state.logged_in = True
                    st.session_state.user_id = user_id
                    st.session_state.username = username

                    # セッション作成 & クッキー保存
                    token = auth.create_session_token(user_id)
                    cookie_manager.set(
                        "session_token",
                        token,
                        expires_at=datetime.now() + auth.timedelta(days=30),
                    )

                    st.success("ログイン成功！")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("メールアドレスかパスワードが間違っています")

    # --- ゲストログイン ---
    st.markdown("---")
    if st.button("ゲストログイン", use_container_width=True):
        user_id, username = auth.login_as_guest()
        if user_id:
            st.session_state.logged_in = True
            st.session_state.user_id = user_id
            st.session_state.username = username

            # セッション作成 & クッキー保存 (ゲストも永続化)
            token = auth.create_session_token(user_id)
            cookie_manager.set(
                "session_token",
                token,
                expires_at=datetime.now() + auth.timedelta(days=30),
            )

            st.toast("ゲストログインしました！")
            time.sleep(1)
            st.rerun()
        else:
            st.error("ゲストログインに失敗しました。")

    # --- 新規登録 ---
    with tab2:
        st.write("新しくアカウントを作成します。")
        with st.form("signup_form"):
            new_username = st.text_input("ユーザー名（表示名）")
            new_email = st.text_input("メールアドレス")
            new_password = st.text_input("パスワード", type="password")
            submitted_signup = st.form_submit_button("登録する", type="primary")

            if submitted_signup:
                if not new_username or not new_email or not new_password:
                    st.warning("すべての項目を入力してください")
                else:
                    # authモジュールで登録
                    success, msg = auth.register_user(
                        new_username, new_email, new_password
                    )
                    if success:
                        st.success(msg)
                        st.info("「ログイン」タブからログインしてください。")
                    else:
                        st.error(msg)

    # --- リセット申請 ---
    with tab3:
        st.write("登録したメールアドレスを入力してください。")

        with st.form("reset_request_form"):
            reset_email = st.text_input("メールアドレス")
            submitted_reset = st.form_submit_button("リセットリンクを発行")

            if submitted_reset:
                # authモジュールでトークン発行
                if auth.issue_reset_token(reset_email):
                    st.success("パスワード再設定メールを送信しました。")
                    st.info(
                        "メールボックスを確認し、本文内のリンクをクリックしてください。"
                    )
                else:
                    st.error("そのメールアドレスは見つかりません。")

    st.stop()  # ここで止める

# ==========================================
# パターンC：メインアプリ画面 (ログイン済み)
# ==========================================
st.sidebar.success(f"ログイン中: {st.session_state.username}")

if st.sidebar.button("ログアウト"):
    # サーバー側セッション削除
    current_token = cookie_manager.get("session_token")
    if current_token:
        auth.revoke_session_token(current_token)

    # クッキー削除
    cookie_manager.delete("session_token")

    st.session_state.logged_in = False
    st.session_state.user_id = None
    time.sleep(0.5)
    st.rerun()

st.title("せどりすと")

# サイドバーメニュー
with st.sidebar:
    st.header("メニュー")
    menu = st.pills(
        "",
        ["在庫一覧", "仕入れ登録", "設定"],
        selection_mode="single",
        default="在庫一覧",
    )

# --- 1. 在庫一覧画面 ---
if menu == "在庫一覧" or menu is None:
    # フラグメント化した関数を呼ぶ
    show_inventory_screen()

# --- 2. 仕入れ登録画面 ---
elif menu == "仕入れ登録":
    # フラグメント化した関数を呼ぶ
    show_register_screen()

# --- 3. 設定画面 ---
elif menu == "設定":
    st.subheader("アカウント設定")

    # ユーザー名変更
    with st.expander("ユーザー名変更", expanded=False):
        with st.form("change_username_form"):
            st.text_input(
                "現在のユーザー名", value=st.session_state.username, disabled=True
            )
            new_name = st.text_input("新しいユーザー名")
            if st.form_submit_button("変更する", type="primary"):
                if not new_name:
                    st.warning("名前を入力してください")
                elif new_name == st.session_state.username:
                    st.info("現在と同じ名前です")
                else:
                    # dbモジュールで更新
                    if db.update_username(st.session_state.user_id, new_name):
                        st.session_state.username = new_name
                        st.success(f"ユーザー名を「{new_name}」に変更しました！")
                        time.sleep(1)
                        st.rerun()

    st.divider()

    # メールアドレス変更
    with st.expander("メールアドレス変更", expanded=False):
        current_email = db.get_user_email(st.session_state.user_id)  # dbを使う
        with st.form("change_email_form"):
            st.text_input("現在のメールアドレス", value=current_email, disabled=True)
            new_email = st.text_input("新しいメールアドレス")
            if st.form_submit_button("変更する", type="primary"):
                if not new_email:
                    st.warning("新しいメールアドレスを入力してください")
                elif new_email == current_email:
                    st.info("現在と同じメールアドレスです")
                else:
                    # dbモジュールで更新
                    success, msg = db.update_email(st.session_state.user_id, new_email)
                    if success:
                        st.success(msg)
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(msg)

    st.divider()

    # パスワード変更
    with st.expander("パスワード変更", expanded=False):
        with st.form("change_password_form"):
            current_pw = st.text_input("現在のパスワード", type="password")
            new_pw = st.text_input("新しいパスワード", type="password")
            confirm_pw = st.text_input("新しいパスワード（確認）", type="password")
            if st.form_submit_button("変更する", type="primary"):
                if not current_pw or not new_pw:
                    st.error("パスワードを入力してください")
                elif new_pw != confirm_pw:
                    st.error("新しいパスワードが一致しません")
                else:
                    # authモジュールで変更
                    success, msg = auth.change_password(
                        st.session_state.user_id, current_pw, new_pw
                    )
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)

    st.divider()

    # CSV出力
    with st.expander("CSV出力", expanded=False):
        st.write("現在の在庫データをCSV形式でダウンロードします。")
        df_export = db.load_items(st.session_state.user_id)  # dbを使う
        if not df_export.empty:
            csv_data = df_export.to_csv(index=False).encode("utf-8-sig")
            now_str = datetime.now().strftime("%Y%m%d_%H%M")
            st.download_button(
                label="CSVをダウンロード",
                data=csv_data,
                file_name=f"stock_data_{now_str}.csv",
                mime="text/csv",
                type="primary",
            )
        else:
            st.info("ダウンロードするデータがありません。")

    st.divider()

    # 退会
    with st.expander("退会（アカウント削除）", expanded=False):
        st.info("退会すると、登録した在庫データは全て完全に削除され、復元できません。")
        confirm_delete = st.checkbox("上記の注意事項を理解し、退会します")
        if confirm_delete:
            if st.button(
                "退会する(データを全消去)", type="primary", use_container_width=True
            ):
                # dbモジュールで削除
                if db.delete_user_account(st.session_state.user_id):
                    st.success("退会処理が完了しました。ご利用ありがとうございました。")
                    st.session_state.logged_in = False
                    st.session_state.user_id = None
                    st.session_state.username = ""
                    time.sleep(2)
                    st.rerun()


import sqlite3
from pathlib import Path
from datetime import date, datetime
import json
import pandas as pd
import streamlit as st

APP_TITLE = "Wealth AI Manager - Ultimate"
DB_PATH = Path(__file__).with_name("wealth_ultimate.db")

try:
    import yfinance as yf
    YF_AVAILABLE = True
except Exception:
    YF_AVAILABLE = False

st.set_page_config(page_title=APP_TITLE, layout="wide")

@st.cache_resource
def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS assets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        asset_name TEXT NOT NULL,
        asset_type TEXT NOT NULL,
        symbol TEXT,
        quantity REAL NOT NULL DEFAULT 0,
        cost_per_unit REAL NOT NULL DEFAULT 0,
        current_price REAL NOT NULL DEFAULT 0,
        annual_income REAL NOT NULL DEFAULT 0,
        target_price REAL NOT NULL DEFAULT 0,
        note TEXT,
        updated_at TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS cashflows (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        flow_date TEXT NOT NULL,
        category TEXT NOT NULL,
        amount REAL NOT NULL,
        source TEXT,
        note TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS goals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        goal_name TEXT NOT NULL,
        target_amount REAL NOT NULL DEFAULT 0,
        current_amount REAL NOT NULL DEFAULT 0,
        monthly_contribution REAL NOT NULL DEFAULT 0,
        expected_return REAL NOT NULL DEFAULT 0,
        years INTEGER NOT NULL DEFAULT 1,
        note TEXT
    )
    """)

    cur.execute("SELECT COUNT(*) FROM assets")
    if cur.fetchone()[0] == 0:
        now = datetime.now().isoformat(timespec="seconds")
        cur.executemany("""
            INSERT INTO assets
            (asset_name, asset_type, symbol, quantity, cost_per_unit, current_price, annual_income, target_price, note, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            ("SCB", "หุ้น", "SCB.BK", 200, 130.00, 121.00, 2088, 115, "หุ้นปันผล", now),
            ("KTB", "หุ้น", "KTB.BK", 1700, 25.80, 18.50, 2057, 17.5, "ธนาคาร", now),
            ("BGRIM", "หุ้น", "BGRIM.BK", 2800, 11.71, 10.80, 0, 10.5, "เก็งฟื้นตัว", now),
            ("SPY ETF", "กองทุน", "SPY", 3, 510.00, 520.00, 18.00, 0, "ตัวอย่าง US ETF", now),
            ("Gold Fund", "ทอง", "", 1, 137000, 161000, 0, 0, "กองทุนทอง กรอกเอง", now),
            ("Rental Land", "อสังหา/ค่าเช่า", "", 1, 0, 0, 600000, 0, "ค่าเช่าต่อปี", now),
            ("Deposit", "เงินสด", "", 1, 468000, 468000, 7488, 0, "ดอกเบี้ย 1.6%", now),
        ])

    cur.execute("SELECT COUNT(*) FROM cashflows")
    if cur.fetchone()[0] == 0:
        cur.executemany("""
            INSERT INTO cashflows
            (flow_date, category, amount, source, note)
            VALUES (?, ?, ?, ?, ?)
        """, [
            ("2026-01-05", "ค่าเช่าเข้า", 50000, "Rental Land", "รายได้ค่าเช่า"),
            ("2026-02-10", "เงินปันผล", 4200, "SCB", "ตัวอย่าง"),
            ("2026-03-15", "ลงทุนเพิ่ม", -30000, "BGRIM", "ซื้อเพิ่ม"),
            ("2026-03-30", "ดอกเบี้ย", 624, "Deposit", "ประมาณการรายเดือน"),
        ])

    cur.execute("SELECT COUNT(*) FROM goals")
    if cur.fetchone()[0] == 0:
        cur.executemany("""
            INSERT INTO goals
            (goal_name, target_amount, current_amount, monthly_contribution, expected_return, years, note)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [
            ("รายได้เชิงรับ 40,000/เดือน", 480000, 611632, 15000, 0.07, 10, "เป้าปันผล/ค่าเช่า"),
            ("เงินสำรองฉุกเฉิน", 300000, 150000, 5000, 0.02, 3, "กันช็อตชีวิต"),
        ])

    conn.commit()

def run_query(query, params=(), fetch=False):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(query, params)
    rows = cur.fetchall() if fetch else None
    conn.commit()
    return rows

@st.cache_data(ttl=30)
def cached_read_table(table_name, cache_key):
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    df = pd.read_sql_query(f"SELECT * FROM {table_name} ORDER BY id DESC", conn)
    conn.close()
    return df

def read_table(table_name):
    cache_key = st.session_state.get("cache_buster", 0)
    return cached_read_table(table_name, cache_key)

def bump_cache():
    st.session_state["cache_buster"] = st.session_state.get("cache_buster", 0) + 1
    cached_read_table.clear()

def load_assets():
    df = read_table("assets")
    if not df.empty:
        df["cost_value"] = df["quantity"] * df["cost_per_unit"]
        df["market_value"] = df["quantity"] * df["current_price"]
        df["unrealized_pl"] = df["market_value"] - df["cost_value"]
        df["yield_on_cost_pct"] = df.apply(
            lambda r: (r["annual_income"] / r["cost_value"] * 100) if r["cost_value"] else 0, axis=1
        )
        df["target_gap_pct"] = df.apply(
            lambda r: ((r["target_price"] - r["current_price"]) / r["current_price"] * 100)
            if r["current_price"] else 0, axis=1
        )
    return df

def load_cashflows():
    df = read_table("cashflows")
    if not df.empty:
        df["flow_date"] = pd.to_datetime(df["flow_date"])
    return df

def load_goals():
    return read_table("goals")

def future_value(current_amount, monthly_contribution, expected_return, years):
    r = expected_return / 12
    n = int(years) * 12
    if n <= 0:
        return current_amount
    if r == 0:
        return current_amount + monthly_contribution * n
    return current_amount * ((1 + r) ** n) + monthly_contribution * ((((1 + r) ** n) - 1) / r)

def suggest_allocation(lump_sum, style, extra_cash_buffer):
    if lump_sum <= 0:
        return pd.DataFrame(columns=["หมวด", "จำนวนเงิน", "เหตุผล"])

    presets = {
        "อนุรักษ์": {
            "เงินสด/กองทุนตลาดเงิน": 0.35,
            "หุ้นปันผล": 0.30,
            "กองทุนดัชนี/เติบโต": 0.20,
            "ทอง": 0.15,
        },
        "สมดุล": {
            "เงินสด/กองทุนตลาดเงิน": 0.20,
            "หุ้นปันผล": 0.35,
            "กองทุนดัชนี/เติบโต": 0.30,
            "ทอง": 0.15,
        },
        "โตระยะยาว": {
            "เงินสด/กองทุนตลาดเงิน": 0.10,
            "หุ้นปันผล": 0.35,
            "กองทุนดัชนี/เติบโต": 0.40,
            "ทอง": 0.15,
        },
    }

    reasons = {
        "เงินสด/กองทุนตลาดเงิน": "เป็นกันชน เผื่อโอกาสและเรื่องฉุกเฉิน",
        "หุ้นปันผล": "ช่วยสร้างกระแสเงินสดระหว่างทาง",
        "กองทุนดัชนี/เติบโต": "เอาไว้โตระยะยาว",
        "ทอง": "กันความผันผวนและเหตุการณ์โลกปั่นป่วน",
    }

    weights = presets[style].copy()
    if extra_cash_buffer:
        weights["เงินสด/กองทุนตลาดเงิน"] += 0.05
        weights["กองทุนดัชนี/เติบโต"] -= 0.05

    rows = []
    for k, w in weights.items():
        rows.append({
            "หมวด": k,
            "จำนวนเงิน": round(lump_sum * w, 2),
            "เหตุผล": reasons[k]
        })
    return pd.DataFrame(rows)

def build_ai_summary(df_assets, df_flows, goal_monthly_income=40000):
    if df_assets.empty:
        return "ยังไม่มีข้อมูลพอร์ต"

    total_cost = float(df_assets["cost_value"].sum())
    total_value = float(df_assets["market_value"].sum())
    total_pl = float(df_assets["unrealized_pl"].sum())
    total_income = float(df_assets["annual_income"].sum())
    monthly_income = total_income / 12

    type_alloc = df_assets.groupby("asset_type")["market_value"].sum().sort_values(ascending=False)
    top_type = type_alloc.index[0] if len(type_alloc) else "-"
    top_type_pct = (type_alloc.iloc[0] / total_value * 100) if total_value and len(type_alloc) else 0

    biggest_asset = df_assets.sort_values("market_value", ascending=False).iloc[0]
    losers = df_assets[df_assets["unrealized_pl"] < 0].sort_values("unrealized_pl")
    this_month_flow = 0

    if not df_flows.empty:
        tmp = df_flows.copy()
        tmp["month"] = tmp["flow_date"].dt.strftime("%Y-%m")
        current_month = pd.Timestamp.today().strftime("%Y-%m")
        this_month_flow = float(tmp.loc[tmp["month"] == current_month, "amount"].sum())

    lines = []
    lines.append("AI Wealth Summary")
    lines.append(f"- มูลค่าพอร์ตปัจจุบัน: {total_value:,.2f}")
    lines.append(f"- ต้นทุนรวม: {total_cost:,.2f}")
    lines.append(f"- กำไร/ขาดทุนคงค้าง: {total_pl:,.2f}")
    lines.append(f"- รายได้เชิงรับต่อปี: {total_income:,.2f}")
    lines.append(f"- รายได้เชิงรับเฉลี่ยต่อเดือน: {monthly_income:,.2f}")
    lines.append(f"- หมวดสินทรัพย์ใหญ่สุด: {top_type} ({top_type_pct:,.1f}%)")
    lines.append(f"- ตัวใหญ่สุดในพอร์ต: {biggest_asset['asset_name']} มูลค่า {biggest_asset['market_value']:,.2f}")
    lines.append(f"- กระแสเงินสดสุทธิเดือนนี้: {this_month_flow:,.2f}")

    if top_type_pct > 50:
        lines.append("- เตือน: พอร์ตกระจุกตัวค่อนข้างสูง")
    if not losers.empty:
        worst = losers.iloc[0]
        lines.append(f"- จุดถ่วงพอร์ตตอนนี้: {worst['asset_name']} ติดลบ {worst['unrealized_pl']:,.2f}")

    gap = goal_monthly_income - monthly_income
    if gap > 0:
        lines.append(f"- ยังขาดรายได้เชิงรับจากเป้า {goal_monthly_income:,.0f}/เดือน อีกประมาณ {gap:,.2f}")
    else:
        lines.append("- รายได้เชิงรับถึงเป้ารายเดือนแล้ว")

    lines.append("- แผนปฏิบัติ:")
    lines.append("  • รีเฟรชราคาจริงก่อนดูสรุป")
    lines.append("  • ทำ backup JSON/CSV ไว้เสมอ โดยเฉพาะเวลารันบน Community Cloud")
    lines.append("  • ใช้ What-if ช่วยคิดก่อนลงเงินจริง")
    return "\n".join(lines)

@st.cache_data(ttl=900, show_spinner=False)
def fetch_live_price_cached(symbol: str):
    if not YF_AVAILABLE or not symbol:
        return None, "yfinance ไม่พร้อมหรือ symbol ว่าง"
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="5d", interval="1d", auto_adjust=False)
        if hist is not None and not hist.empty:
            price = float(hist["Close"].dropna().iloc[-1])
            return price, "ok"
        fi = getattr(ticker, "fast_info", None)
        if fi and isinstance(fi, dict):
            for key in ["lastPrice", "regularMarketPrice", "previousClose"]:
                val = fi.get(key)
                if val:
                    return float(val), "ok"
        return None, "ไม่พบราคาจาก Yahoo Finance"
    except Exception as e:
        return None, str(e)

def fetch_live_price(symbol: str):
    return fetch_live_price_cached(symbol)

def refresh_all_prices():
    df = load_assets()
    logs = []
    updated = 0

    if df.empty:
        return updated, ["ยังไม่มีสินทรัพย์"]

    for _, row in df.iterrows():
        symbol = (row.get("symbol") or "").strip()
        if not symbol:
            logs.append(f"ข้าม {row['asset_name']} : ไม่มี symbol")
            continue
        price, status = fetch_live_price(symbol)
        if price is not None:
            run_query(
                "UPDATE assets SET current_price=?, updated_at=? WHERE id=?",
                (float(price), datetime.now().isoformat(timespec='seconds'), int(row["id"]))
            )
            logs.append(f"อัปเดต {row['asset_name']} ({symbol}) = {price:,.2f}")
            updated += 1
        else:
            logs.append(f"ไม่สำเร็จ {row['asset_name']} ({symbol}) : {status}")
    bump_cache()
    return updated, logs

def export_backup_json():
    data = {
        "assets": read_table("assets").to_dict(orient="records"),
        "cashflows": read_table("cashflows").to_dict(orient="records"),
        "goals": read_table("goals").to_dict(orient="records"),
        "exported_at": datetime.now().isoformat(timespec="seconds")
    }
    return json.dumps(data, ensure_ascii=False, indent=2)

def restore_from_backup_json(text):
    data = json.loads(text)
    conn = get_conn()
    cur = conn.cursor()
    for table in ["assets", "cashflows", "goals"]:
        cur.execute(f"DELETE FROM {table}")
    conn.commit()

    for row in data.get("assets", []):
        cur.execute("""
            INSERT INTO assets
            (id, asset_name, asset_type, symbol, quantity, cost_per_unit, current_price, annual_income, target_price, note, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            row.get("id"), row.get("asset_name"), row.get("asset_type"), row.get("symbol"),
            row.get("quantity", 0), row.get("cost_per_unit", 0), row.get("current_price", 0),
            row.get("annual_income", 0), row.get("target_price", 0), row.get("note", ""), row.get("updated_at")
        ))

    for row in data.get("cashflows", []):
        cur.execute("""
            INSERT INTO cashflows
            (id, flow_date, category, amount, source, note)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            row.get("id"), row.get("flow_date"), row.get("category"),
            row.get("amount", 0), row.get("source", ""), row.get("note", "")
        ))

    for row in data.get("goals", []):
        cur.execute("""
            INSERT INTO goals
            (id, goal_name, target_amount, current_amount, monthly_contribution, expected_return, years, note)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            row.get("id"), row.get("goal_name"), row.get("target_amount", 0),
            row.get("current_amount", 0), row.get("monthly_contribution", 0),
            row.get("expected_return", 0), row.get("years", 1), row.get("note", "")
        ))
    conn.commit()
    bump_cache()

def table_to_csv_bytes(df):
    return df.to_csv(index=False).encode("utf-8-sig")

def build_scenario(df_assets, equity_change_pct, gold_change_pct, cash_change_pct=0):
    if df_assets.empty:
        return None, 0, 0
    sim = df_assets.copy()
    def apply_change(row):
        asset_type = row["asset_type"]
        price = row["current_price"]
        if asset_type in ["หุ้น", "กองทุน", "คริปโต", "อื่นๆ"]:
            return price * (1 + equity_change_pct / 100)
        elif asset_type == "ทอง":
            return price * (1 + gold_change_pct / 100)
        elif asset_type == "เงินสด":
            return price * (1 + cash_change_pct / 100)
        return price
    sim["scenario_price"] = sim.apply(apply_change, axis=1)
    sim["scenario_value"] = sim["quantity"] * sim["scenario_price"]
    sim["scenario_pl_vs_cost"] = sim["scenario_value"] - sim["cost_value"]
    now_total = df_assets["market_value"].sum()
    future_total = sim["scenario_value"].sum()
    diff = future_total - now_total
    return sim, now_total, diff

def delete_by_id(table, row_id):
    run_query(f"DELETE FROM {table} WHERE id=?", (int(row_id),))
    bump_cache()

def update_asset_price(asset_id, current_price, target_price, annual_income, note):
    run_query("""
        UPDATE assets SET current_price=?, target_price=?, annual_income=?, note=?, updated_at=? WHERE id=?
    """, (current_price, target_price, annual_income, note, datetime.now().isoformat(timespec='seconds'), int(asset_id)))
    bump_cache()

init_db()

st.title(APP_TITLE)
st.caption("Single-file + ราคาจริงฟรี + Import/Export + What-if + พร้อม deploy ขึ้น Streamlit Community Cloud")

tabs = st.tabs([
    "Dashboard", "Assets", "Cashflow", "Goals", "AI Summary",
    "Live Price", "What-if", "Backup", "Deploy Guide"
])

with tabs[0]:
    df_assets = load_assets()
    df_flows = load_cashflows()
    if df_assets.empty:
        st.info("ยังไม่มีข้อมูลสินทรัพย์")
    else:
        total_cost = df_assets["cost_value"].sum()
        total_value = df_assets["market_value"].sum()
        total_pl = df_assets["unrealized_pl"].sum()
        total_income = df_assets["annual_income"].sum()
        monthly_income = total_income / 12

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("มูลค่าพอร์ต", f"{total_value:,.2f}")
        c2.metric("ต้นทุนรวม", f"{total_cost:,.2f}")
        c3.metric("กำไร/ขาดทุนคงค้าง", f"{total_pl:,.2f}")
        c4.metric("Passive Income/เดือน", f"{monthly_income:,.2f}")

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("สัดส่วนสินทรัพย์")
            alloc = df_assets.groupby("asset_type", as_index=False)["market_value"].sum()
            st.bar_chart(alloc.set_index("asset_type"))
        with col2:
            st.subheader("สินทรัพย์ใหญ่สุด")
            top_assets = df_assets.sort_values("market_value", ascending=False)[[
                "asset_name", "asset_type", "symbol", "market_value", "unrealized_pl", "updated_at"
            ]].head(10)
            st.dataframe(top_assets, use_container_width=True)

        st.subheader("Export เร็ว ๆ")
        st.download_button("ดาวน์โหลด assets.csv", table_to_csv_bytes(df_assets), "assets.csv", "text/csv")
        st.download_button("ดาวน์โหลด backup.json", export_backup_json().encode("utf-8"), "wealth_backup.json", "application/json")

with tabs[1]:
    st.subheader("เพิ่มสินทรัพย์")
    with st.form("asset_form"):
        c1, c2, c3 = st.columns(3)
        asset_name = c1.text_input("ชื่อสินทรัพย์")
        asset_type = c2.selectbox("ประเภท", ["หุ้น", "กองทุน", "ทอง", "เงินสด", "อสังหา/ค่าเช่า", "คริปโต", "อื่นๆ"])
        symbol = c3.text_input("Symbol (เช่น SCB.BK, KTB.BK, SPY)")
        c4, c5, c6 = st.columns(3)
        quantity = c4.number_input("จำนวน", min_value=0.0, value=1.0, step=1.0)
        cost_per_unit = c5.number_input("ต้นทุนต่อหน่วย", min_value=0.0, value=0.0, step=100.0)
        current_price = c6.number_input("ราคาปัจจุบัน", min_value=0.0, value=0.0, step=100.0)
        c7, c8, c9 = st.columns(3)
        annual_income = c7.number_input("รายได้ต่อปี", min_value=0.0, value=0.0, step=100.0)
        target_price = c8.number_input("ราคาเป้าหมาย", min_value=0.0, value=0.0, step=1.0)
        note = c9.text_input("หมายเหตุ")
        submitted = st.form_submit_button("บันทึกสินทรัพย์")
        if submitted and asset_name.strip():
            run_query("""
                INSERT INTO assets (asset_name, asset_type, symbol, quantity, cost_per_unit, current_price, annual_income, target_price, note, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (asset_name.strip(), asset_type, symbol.strip(), quantity, cost_per_unit, current_price, annual_income, target_price, note.strip(), datetime.now().isoformat(timespec="seconds")))
            bump_cache()
            st.success("บันทึกแล้ว")

    df_assets = load_assets()
    if not df_assets.empty:
        st.dataframe(df_assets[[
            "id", "asset_name", "asset_type", "symbol", "quantity", "cost_per_unit",
            "current_price", "cost_value", "market_value", "unrealized_pl",
            "annual_income", "yield_on_cost_pct", "target_price", "target_gap_pct", "note", "updated_at"
        ]], use_container_width=True)

        st.subheader("แก้ไขราคาหรือรายได้ของรายการ")
        asset_ids = df_assets["id"].tolist()
        selected_id = st.selectbox("เลือก ID ที่จะแก้", asset_ids)
        selected_row = df_assets[df_assets["id"] == selected_id].iloc[0]
        c1, c2, c3, c4 = st.columns(4)
        new_price = c1.number_input("ราคาปัจจุบันใหม่", value=float(selected_row["current_price"]), step=1.0)
        new_target = c2.number_input("ราคาเป้าหมายใหม่", value=float(selected_row["target_price"]), step=1.0)
        new_income = c3.number_input("รายได้ต่อปีใหม่", value=float(selected_row["annual_income"]), step=100.0)
        new_note = c4.text_input("หมายเหตุใหม่", value=str(selected_row["note"] or ""))
        if st.button("บันทึกการแก้ไข"):
            update_asset_price(selected_id, new_price, new_target, new_income, new_note)
            st.success("อัปเดตรายการแล้ว")

        st.subheader("ลบรายการสินทรัพย์")
        delete_asset_id = st.selectbox("เลือก ID ที่จะลบ", asset_ids, key="delete_asset_id")
        if st.button("ลบสินทรัพย์ที่เลือก"):
            delete_by_id("assets", delete_asset_id)
            st.warning("ลบแล้ว")

with tabs[2]:
    st.subheader("บันทึกกระแสเงินสด")
    with st.form("flow_form"):
        c1, c2, c3 = st.columns(3)
        flow_date = c1.date_input("วันที่", value=date.today())
        category = c2.selectbox("หมวด", ["ค่าเช่าเข้า", "เงินปันผล", "ดอกเบี้ย", "ลงทุนเพิ่ม", "ถอนเงิน", "รายได้ธุรกิจ", "ค่าใช้จ่าย"])
        amount = c3.number_input("จำนวนเงิน (+ รายรับ / - รายจ่าย)", value=0.0, step=100.0)
        c4, c5 = st.columns(2)
        source = c4.text_input("ที่มา")
        note = c5.text_input("หมายเหตุ")
        submitted = st.form_submit_button("บันทึกกระแสเงินสด")
        if submitted:
            run_query("""
                INSERT INTO cashflows (flow_date, category, amount, source, note)
                VALUES (?, ?, ?, ?, ?)
            """, (str(flow_date), category, amount, source.strip(), note.strip()))
            bump_cache()
            st.success("บันทึกแล้ว")

    df_flows = load_cashflows()
    if not df_flows.empty:
        st.dataframe(df_flows, use_container_width=True)
        monthly = df_flows.copy()
        monthly["month"] = df_flows["flow_date"].dt.strftime("%Y-%m")
        monthly_sum = monthly.groupby("month", as_index=False)["amount"].sum().sort_values("month")
        st.subheader("สรุปสุทธิรายเดือน")
        st.bar_chart(monthly_sum.set_index("month"))

        flow_ids = df_flows["id"].tolist()
        del_flow_id = st.selectbox("เลือก ID กระแสเงินสดที่จะลบ", flow_ids)
        if st.button("ลบกระแสเงินสดที่เลือก"):
            delete_by_id("cashflows", del_flow_id)
            st.warning("ลบแล้ว")

with tabs[3]:
    st.subheader("ตั้งเป้าหมาย")
    with st.form("goal_form"):
        goal_name = st.text_input("ชื่อเป้าหมาย")
        c1, c2, c3 = st.columns(3)
        target_amount = c1.number_input("เป้าหมาย (บาท)", min_value=0.0, value=480000.0, step=10000.0)
        current_amount = c2.number_input("มีแล้วตอนนี้", min_value=0.0, value=0.0, step=10000.0)
        monthly_contribution = c3.number_input("เติมต่อเดือน", min_value=0.0, value=5000.0, step=1000.0)
        c4, c5 = st.columns(2)
        expected_return = c4.number_input("ผลตอบแทนคาดหวัง/ปี", min_value=0.0, value=0.07, step=0.01, format="%.2f")
        years = c5.number_input("จำนวนปี", min_value=1, value=10, step=1)
        note = st.text_input("หมายเหตุเป้าหมาย")
        submitted = st.form_submit_button("บันทึกเป้าหมาย")
        if submitted and goal_name.strip():
            run_query("""
                INSERT INTO goals (goal_name, target_amount, current_amount, monthly_contribution, expected_return, years, note)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (goal_name.strip(), target_amount, current_amount, monthly_contribution, expected_return, int(years), note.strip()))
            bump_cache()
            st.success("บันทึกแล้ว")

    df_goals = load_goals()
    if not df_goals.empty:
        df_goals["future_value"] = df_goals.apply(
            lambda r: future_value(r["current_amount"], r["monthly_contribution"], r["expected_return"], r["years"]),
            axis=1
        )
        df_goals["progress_pct"] = df_goals.apply(
            lambda r: (r["current_amount"] / r["target_amount"] * 100) if r["target_amount"] else 0, axis=1
        )
        df_goals["gap_to_target"] = df_goals["target_amount"] - df_goals["future_value"]
        st.dataframe(df_goals[[
            "id", "goal_name", "target_amount", "current_amount", "monthly_contribution",
            "expected_return", "years", "future_value", "progress_pct", "gap_to_target", "note"
        ]], use_container_width=True)

        goal_ids = df_goals["id"].tolist()
        del_goal_id = st.selectbox("เลือก ID เป้าหมายที่จะลบ", goal_ids)
        if st.button("ลบเป้าหมายที่เลือก"):
            delete_by_id("goals", del_goal_id)
            st.warning("ลบแล้ว")

with tabs[4]:
    st.subheader("สรุปภาพรวมแบบ AI")
    goal_income = st.number_input("เป้ารายได้เชิงรับต่อเดือน", min_value=0.0, value=40000.0, step=1000.0)
    df_assets = load_assets()
    df_flows = load_cashflows()
    summary = build_ai_summary(df_assets, df_flows, goal_income)
    st.code(summary, language="text")

    st.subheader("ตัวช่วยจัดเงินก้อน")
    c1, c2, c3 = st.columns(3)
    lump_sum = c1.number_input("มีเงินก้อนเท่าไร", min_value=0.0, value=200000.0, step=10000.0)
    style = c2.selectbox("สไตล์", ["อนุรักษ์", "สมดุล", "โตระยะยาว"])
    extra_cash = c3.checkbox("เพิ่มเงินสำรองอีก 5%", value=True)
    alloc_df = suggest_allocation(lump_sum, style, extra_cash)
    if not alloc_df.empty:
        st.dataframe(alloc_df, use_container_width=True)
        st.bar_chart(alloc_df.set_index("หมวด")["จำนวนเงิน"])

with tabs[5]:
    st.subheader("ดึงราคาจริงฟรี")
    st.write("ใช้กับ symbol ที่มีบน Yahoo Finance เช่น SCB.BK, KTB.BK, BGRIM.BK, SPY, AAPL")
    c1, c2 = st.columns([1,2])
    with c1:
        st.metric("yfinance พร้อมใช้งาน", "Yes" if YF_AVAILABLE else "No")
        if st.button("รีเฟรชราคาทั้งหมด"):
            updated, logs = refresh_all_prices()
            st.success(f"อัปเดตสำเร็จ {updated} รายการ")
            st.code("\n".join(logs), language="text")
    with c2:
        test_symbol = st.text_input("ลองเช็คราคา symbol เดี่ยว", value="SCB.BK")
        if st.button("ทดสอบดึงราคา"):
            price, status = fetch_live_price(test_symbol.strip())
            if price is not None:
                st.success(f"{test_symbol} = {price:,.2f}")
            else:
                st.error(f"ไม่สำเร็จ: {status}")

with tabs[6]:
    st.subheader("What-if Analysis")
    df_assets = load_assets()
    eq_change = st.slider("สมมติหุ้น/กองทุน/คริปโต เปลี่ยน (%)", -50, 50, -10)
    gold_change = st.slider("สมมติทอง เปลี่ยน (%)", -50, 50, 5)
    cash_change = st.slider("สมมติเงินสด/ดอกเบี้ย เปลี่ยน (%)", -10, 10, 0)
    sim, now_total, diff = build_scenario(df_assets, eq_change, gold_change, cash_change)
    if sim is not None:
        c1, c2 = st.columns(2)
        c1.metric("มูลค่าพอร์ตปัจจุบัน", f"{now_total:,.2f}")
        c2.metric("ผลกระทบจากสมมติฐาน", f"{diff:,.2f}")
        st.dataframe(sim[[
            "asset_name", "asset_type", "current_price", "scenario_price",
            "market_value", "scenario_value", "scenario_pl_vs_cost"
        ]], use_container_width=True)

with tabs[7]:
    st.subheader("Backup / Restore")
    backup_json = export_backup_json()
    st.download_button("ดาวน์โหลด backup.json", backup_json.encode("utf-8"), "wealth_backup.json", "application/json")

    df_assets = load_assets()
    df_flows = load_cashflows()
    df_goals = load_goals()
    st.download_button("ดาวน์โหลด assets.csv", table_to_csv_bytes(df_assets), "assets.csv", "text/csv")
    st.download_button("ดาวน์โหลด cashflows.csv", table_to_csv_bytes(df_flows), "cashflows.csv", "text/csv")
    st.download_button("ดาวน์โหลด goals.csv", table_to_csv_bytes(df_goals), "goals.csv", "text/csv")

    uploaded = st.file_uploader("อัปโหลด backup.json เพื่อกู้ข้อมูล", type=["json"])
    if uploaded is not None:
        text = uploaded.read().decode("utf-8")
        if st.button("กู้ข้อมูลจาก backup.json"):
            restore_from_backup_json(text)
            st.success("กู้ข้อมูลเรียบร้อย")

with tabs[8]:
    st.subheader("วิธีเอาขึ้นเว็บ Streamlit Community Cloud")
    st.markdown("""
### โครงไฟล์ที่ควรอยู่ใน GitHub
- `app.py`
- `requirements.txt`
- `.streamlit/config.toml`

### ขั้นตอน
1. สร้าง GitHub repository ใหม่
2. อัปโหลดไฟล์ทั้งหมดขึ้น repo
3. เข้า Streamlit Community Cloud
4. ล็อกอินและเชื่อม GitHub
5. กด Deploy an app
6. เลือก repository ของคุณ
7. ตั้งค่า Main file path เป็น `app.py`
8. กด Deploy

### ข้อควรระวัง
- local file / SQLite บน Community Cloud ไม่ควรใช้เป็นที่เก็บข้อมูลถาวร
- ให้ export backup เป็น JSON/CSV เป็นประจำ
- ถ้าจะเก็บจริงจัง ควรต่อไป Supabase / Google Sheets / Postgres
""")

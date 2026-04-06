
# Wealth AI Manager - Ultimate

เวอร์ชันนี้จัดเต็มกว่าเดิม:
- Single file (`app.py`)
- ดึงราคาจริงฟรีด้วย `yfinance`
- CRUD เบื้องต้น (เพิ่ม/แก้/ลบ)
- Goal planning
- AI summary
- What-if analysis
- Backup / Restore JSON
- Export CSV
- คู่มือ deploy ขึ้น Streamlit Community Cloud

## รันบนเครื่อง
```bash
python -m venv .venv
```

Windows:
```bash
.venv\Scripts\activate
```

macOS / Linux:
```bash
source .venv/bin/activate
```

ติดตั้ง:
```bash
pip install -r requirements.txt
```

รัน:
```bash
streamlit run app.py
```

## Deploy ขึ้นเว็บ
ดูไฟล์ `DEPLOY_STREAMLIT_CLOUD.md`

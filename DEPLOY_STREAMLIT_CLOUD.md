
# วิธี Deploy ขึ้น Streamlit Community Cloud แบบฟรี

1. สร้าง GitHub repo ใหม่
2. อัปโหลดไฟล์:
   - app.py
   - requirements.txt
   - .streamlit/config.toml
3. เข้า Streamlit Community Cloud
4. กด Deploy an app
5. เลือก repo
6. ตั้ง Main file path เป็น app.py
7. กด Deploy

ข้อควรระวัง:
- อย่าใช้ SQLite/local file เป็นที่เก็บถาวรบน Community Cloud
- ให้ backup JSON/CSV เป็นระยะ

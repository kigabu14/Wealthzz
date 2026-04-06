
# วิธี Deploy ขึ้น Streamlit Community Cloud แบบฟรี

## 1) เตรียม GitHub
สร้าง repo ใหม่ เช่น `wealth-ai-manager`

อัปโหลดไฟล์เหล่านี้:
- app.py
- requirements.txt
- .streamlit/config.toml

## 2) เข้า Streamlit Community Cloud
ล็อกอินด้วย GitHub

## 3) Deploy
- กด Deploy an app
- เลือก repo
- Branch: main
- Main file path: app.py
- กด Deploy

## 4) ถ้า build ไม่ผ่าน
เช็กว่า `requirements.txt` อยู่ใน root ของ repo
และชื่อไฟล์หลักคือ `app.py`

## 5) หลัง deploy
จะได้ URL ประมาณ:
`https://your-app-name.streamlit.app`

## 6) ข้อควรระวัง
Community Cloud ไม่การันตี local file persistence
อย่าเก็บข้อมูลสำคัญไว้แต่ใน SQLite/local db อย่างเดียว
ใช้ Backup/Restore ในแอป หรือย้ายไปฐานข้อมูลจริงทีหลัง

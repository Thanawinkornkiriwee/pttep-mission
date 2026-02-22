import os
import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse, PlainTextResponse

app = FastAPI()

# --- ตั้งค่าตำแหน่งโฟลเดอร์รูปภาพ (ปรับ Path ได้ตามต้องการ) ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGE_FOLDER = os.path.join(BASE_DIR, 'media_folder')

valid_extensions = ('.jpg', '.jpeg', '.png', '.bmp')

# ตรวจสอบและโหลดรายชื่อไฟล์ภาพตั้งแต่ตอนเริ่มโปรแกรม
if not os.path.exists(IMAGE_FOLDER):
    print(f"❌ Error: หา Folder นี้ไม่เจอ -> {IMAGE_FOLDER}")
    os.makedirs(IMAGE_FOLDER, exist_ok=True)
    image_files = []
else:
    image_files = sorted([
        f for f in os.listdir(IMAGE_FOLDER) 
        if f.lower().endswith(valid_extensions)
    ])
    print(f"✅ เจอรูปทั้งหมด {len(image_files)} รูป ใน {IMAGE_FOLDER}")
    print('open_link:http://10.61.35.243:1984/image')

# ตัวแปร Global สำหรับเก็บลำดับภาพปัจจุบัน
current_index = 0 

# สร้าง API Endpoint ให้ตรงกับที่คุณต้องการ
@app.get('/image')
async def get_frame():
    global current_index
    
    if not image_files:
        return PlainTextResponse("No images found.", status_code=404)
        
    # ดึงชื่อไฟล์ตาม Index ปัจจุบัน
    filename = image_files[current_index]
    full_path = os.path.join(IMAGE_FOLDER, filename)
    
    # อัปเดต Index สำหรับการเรียกครั้งถัดไป (ถ้าถึงรูปสุดท้ายให้วนกลับไปรูปแรก)
    current_index = (current_index + 1) % len(image_files)
    
    
    # ส่งไฟล์รูปภาพกลับไปให้ Client
    return FileResponse(full_path, media_type='image/jpeg')

if __name__ == "__main__":
    # รันเซิร์ฟเวอร์ด้วย Uvicorn บนพอร์ต 1984 แบบเดียวกับของเดิม
    uvicorn.run(app, host="0.0.0.0", port=1984)
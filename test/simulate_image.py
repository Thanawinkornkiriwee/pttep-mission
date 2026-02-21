import os
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI()

# --- ตั้งค่าตำแหน่งโฟลเดอร์ ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGE_FOLDER = os.path.join(BASE_DIR, 'media_folder')

if not os.path.exists(IMAGE_FOLDER):
    os.makedirs(IMAGE_FOLDER)

# Mount เพื่อให้เข้าถึงไฟล์รูปภาพผ่าน URL ได้ (เช่น /media/image1.jpg)
app.mount("/media", StaticFiles(directory=IMAGE_FOLDER), name="media")

@app.get("/", response_class=HTMLResponse)
async def get_latest_image(request: Request):
    # ดึงไฟล์และเลือกไฟล์ที่อัปเดตล่าสุด
    files = [f for f in os.listdir(IMAGE_FOLDER) 
             if f.lower().endswith((".png", ".jpg", ".jpeg", ".gif"))]
    
    latest_image = ""
    if files:
        # เรียงตามเวลาที่แก้ไขล่าสุด
        files.sort(key=lambda x: os.path.getmtime(os.path.join(IMAGE_FOLDER, x)), reverse=True)
        latest_image = files[0]

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>IP Camera Stream</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ font-family: sans-serif; background: #1a1a1a; color: white; text-align: center; margin: 0; padding: 20px; }}
            .img-box {{ background: #000; display: inline-block; padding: 10px; border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }}
            img {{ max-width: 100%; height: auto; border-radius: 8px; }}
            h2 {{ color: #00ff88; }}
            .footer {{ margin-top: 10px; font-size: 14px; opacity: 0.6; }}
        </style>
        <script>
            // Refresh หน้าเว็บทุกๆ 2 วินาทีเพื่ออัปเดตภาพล่าสุด
            setTimeout(() => {{ location.reload(); }}, 2000);
        </script>
    </head>
    <body>
        <h2>Live Latest Image</h2>
        <div class="img-box">
            {f'<img src="/media/{latest_image}">' if latest_image else "<h3>No image in folder</h3>"}
        </div>
        <div class="footer">File: {latest_image if latest_image else "Waiting..."}</div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

if __name__ == "__main__":
    # --- สำคัญมาก: เปลี่ยน localhost เป็น 0.0.0.0 ---
    # port=5000 (เปลี่ยนเป็นเลขอื่นได้ตามชอบ)
    uvicorn.run(app, host="0.0.0.0", port=5000)
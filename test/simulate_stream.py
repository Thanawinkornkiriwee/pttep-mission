import gi
import os
import shutil

gi.require_version('Gst', '1.0')
gi.require_version('GstRtspServer', '1.0')
from gi.repository import Gst, GstRtspServer, GLib

Gst.init(None)

class CustomRtspServer:
    def __init__(self, folder_path, ip_address="0.0.0.0", port="8554"):
        self.server = GstRtspServer.RTSPServer()
        self.server.set_address(ip_address) 
        self.server.set_service(port)       
        
        # 1. ดึงรายชื่อไฟล์ภาพทั้งหมด
        files = [f for f in os.listdir(folder_path) if f.lower().endswith(('.jpg', '.jpeg', '.png','.mp4'))]
        files.sort()
        
        if not files:
            print(f"ERROR: No images found in {folder_path}")
            return

        # 2. สร้างโฟลเดอร์ชั่วคราวชื่อ tmp_seq เพื่อจำลองชื่อไฟล์ให้เป็น 0.jpg, 1.jpg
        seq_folder = os.path.join(folder_path, "tmp_seq")
        os.makedirs(seq_folder, exist_ok=True)
        
        print(f"Preparing {len(files)} images for slideshow...")
        for i, filename in enumerate(files):
            src = os.path.join(folder_path, filename)
            dst = os.path.join(seq_folder, f"{i}.jpg")
            
            # ลบไฟล์เก่าถ้ามีค้างอยู่ แล้วสร้าง Link เชื่อมไปหาไฟล์จริง
            if os.path.exists(dst):
                os.remove(dst)
            try:
                os.symlink(src, dst) # สร้าง Link ไม่กินพื้นที่ฮาร์ดดิสก์
            except:
                shutil.copy(src, dst) # เผื่อระบบ OS ไม่รองรับ Symlink
        
        factory = GstRtspServer.RTSPMediaFactory()
        
        # 3. ใช้ multifilesrc ดึงภาพจากโฟลเดอร์ชั่วคราว
        # caps="image/jpeg,framerate=1/1" หมายถึง เปลี่ยนภาพทุกๆ 1 วินาที (แก้เลขตรงนี้ได้)
        # เปลี่ยนจาก jpegdec เป็น decodebin
        pipeline = (
            f'multifilesrc location="{seq_folder}/%d.jpg" loop=true caps="image/jpeg,framerate=1/1" ! '
            'decodebin ! videoconvert ! '
            'x264enc speed-preset=ultrafast tune=zerolatency ! '
            'rtph264pay name=pay0 pt=96'
        )
        
        print("Pipeline is ready!")
        
        factory.set_launch(pipeline)
        factory.set_shared(True)
        self.server.get_mount_points().add_factory("/stream", factory)
        self.server.attach(None)
        
        print(f"Server is live at rtsp://10.61.35.243:{port}/stream")

if __name__ == "__main__":
    folder = os.path.abspath("./video_folder") 
    server = CustomRtspServer(folder, "0.0.0.0", "8554")
    loop = GLib.MainLoop()
    try:
        loop.run()
    except KeyboardInterrupt:
        print("\nStopping server...")
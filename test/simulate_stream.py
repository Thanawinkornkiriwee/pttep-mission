import gi
import os

gi.require_version('Gst', '1.0')
gi.require_version('GstRtspServer', '1.0')
from gi.repository import Gst, GstRtspServer, GLib

Gst.init(None)

class CustomRtspServer:
    def __init__(self, video_path, ip_address="0.0.0.0", port="8554"):
        self.server = GstRtspServer.RTSPServer()
        self.server.set_address(ip_address) 
        self.server.set_service(port)       
        
        if not os.path.exists(video_path):
            print(f"ERROR: Video file not found at {video_path}")
            return
            
        factory = GstRtspServer.RTSPMediaFactory()
        
        # ---------------------------------------------------------
        # GStreamer Pipeline สำหรับไฟล์ Video (MP4, AVI, MKV)
        # filesrc: ดึงไฟล์วิดีโอ -> decodebin: ถอดรหัสวิดีโอ/เสียงอัตโนมัติ
        # ---------------------------------------------------------
        pipeline = (
            f'filesrc location="{video_path}" ! decodebin ! videoconvert ! '
            'x264enc speed-preset=ultrafast tune=zerolatency ! '
            'rtph264pay name=pay0 pt=96'
        )
        
        print(f"Pipeline is ready! Streaming video: {os.path.basename(video_path)}")
        
        factory.set_launch(pipeline)
        factory.set_shared(True)
        self.server.get_mount_points().add_factory("/stream", factory)
        self.server.attach(None)
        
        print(f"Server is live at rtsp://10.61.35.243:{port}/stream")

if __name__ == "__main__":
    # ระบุพาทไปที่ "ไฟล์วิดีโอ" โดยตรง ไม่ใช่โฟลเดอร์นะครับ
    video_file = os.path.abspath("./video_folder/pig_trap_1_survey_4.mp4") 
    
    server = CustomRtspServer(video_file, "0.0.0.0", "8554")
    loop = GLib.MainLoop()
    try:
        loop.run()
    except KeyboardInterrupt:
        print("\nStopping server...")
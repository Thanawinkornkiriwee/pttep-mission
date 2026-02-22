import threading
import queue
import logging
import gi

gi.require_version('Gst', '1.0')
gi.require_version('GstRtspServer', '1.0')
from gi.repository import Gst, GstRtspServer, GLib

class RTSPOUTPUTProducer(threading.Thread):
    def __init__(self, config: dict, output_queue: queue.Queue):
        super().__init__()
        self.config = config.get('output_stream', {})
        self.output_queue = output_queue
        self.running = True
        self.daemon = True
        self.logger = logging.getLogger("AIPipeline")
        
        self.ip_address = str(self.config.get('ip_address', '0.0.0.0'))
        self.port = str(self.config.get('port', 8555))
        self.mount = self.config.get('mount', '/result')
        self.width = self.config.get('width', 640)
        self.height = self.config.get('height', 480)
        self.fps = self.config.get('fps', 30)
        
        # คำนวณระยะเวลาต่อเฟรม
        self.duration = int((1.0 / self.fps) * Gst.SECOND)
        self.number_frames = 0
        
        self.loop = None
        self.server = None

    def on_media_configure(self, factory, media):
        """ทำงานทันทีที่มี VLC หรือ Client กดดูสตรีม (เชื่อม appsrc เข้ากับ Queue)"""
        self.number_frames = 0
        appsrc = media.get_element().get_child_by_name('source')
        if appsrc:
            # สั่งให้ appsrc ทักมาขอภาพจากฟังก์ชัน on_need_data
            appsrc.connect('need-data', self.on_need_data)

    def on_need_data(self, src, length):
        """ดึงภาพจาก Output Queue มาสร้างเป็นวิดีโอ RTSP"""
        try:
            frame = self.output_queue.get(timeout=0.1)
            
            data = frame.tobytes()
            buf = Gst.Buffer.new_allocate(None, len(data), None)
            buf.fill(0, data)
            buf.duration = self.duration
            
            # ประทับตราเวลา
            timestamp = self.number_frames * self.duration
            buf.pts = buf.dts = timestamp
            buf.offset = timestamp
            
            self.number_frames += 1
            src.emit('push-buffer', buf)
            
        except queue.Empty:
            pass

    def run(self):
        """สร้าง Server และผูก Loop ให้อยู่ใน Thread เดียวกัน 100%"""
        if not Gst.is_initialized():
            Gst.init(None)

        self.server = GstRtspServer.RTSPServer()
        self.server.set_address(self.ip_address)
        self.server.set_service(self.port)
        
        # 1. ใช้ Factory มาตรฐานแบบเดียวกับ simulate_stream.py เป๊ะ!
        factory = GstRtspServer.RTSPMediaFactory()
        
        # 2. Pipeline โดยใช้ appsrc รับภาพจากหน่วยความจำ
        launch_string = (
            f'appsrc name=source is-live=true block=true format=GST_FORMAT_TIME '
            f'caps=video/x-raw,format=BGR,width={self.width},height={self.height},framerate={self.fps}/1 '
            f'! videoconvert ! video/x-raw,format=I420 '
            f'! x264enc speed-preset=ultrafast tune=zerolatency '
            f'! rtph264pay config-interval=1 name=pay0 pt=96'
        )
        factory.set_launch(launch_string)
        factory.set_shared(True)
        
        # 3. ให้ Factory เรียก on_media_configure เมื่อระบบเริ่มทำงาน
        factory.connect("media-configure", self.on_media_configure)
        
        self.server.get_mount_points().add_factory(self.mount, factory)
        self.server.attach(None)
        
        display_ip = "ANY_IP (0.0.0.0)" if self.ip_address == "0.0.0.0" else self.ip_address
        self.logger.info(f"[RTSPOutput] Result Stream is LIVE at rtsp://{display_ip}:{self.port}{self.mount}")
        
        # รัน MainLoop ใน Thread นี้
        self.loop = GLib.MainLoop()
        self.loop.run()

    def stop(self):
        self.running = False
        if self.loop is not None:
            self.loop.quit()
        self.logger.debug("[RTSPOutput] Stop signal received.")
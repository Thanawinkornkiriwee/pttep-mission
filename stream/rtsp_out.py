import threading
import queue
import logging
import cv2
import gi

gi.require_version('Gst', '1.0')
gi.require_version('GstRtspServer', '1.0')
from gi.repository import Gst, GstRtspServer, GLib

class QueueMediaFactory(GstRtspServer.RTSPMediaFactory):
    """Factory สำหรับดึงภาพจาก Queue ไปสร้างเป็นสตรีมวิดีโอ"""
    def __init__(self, output_queue, fps, width, height):
        super().__init__()
        self.output_queue = output_queue
        self.fps = fps
        self.width = width
        self.height = height
        self.duration = 1 / self.fps * Gst.SECOND  
        self.number_frames = 0
        
        self.launch_string = (
            f'appsrc name=source is-live=true block=true format=GST_FORMAT_TIME '
            f'caps=video/x-raw,format=BGR,width={self.width},height={self.height},framerate={self.fps}/1 '
            f'! videoconvert ! video/x-raw,format=I420 '
            f'! x264enc speed-preset=ultrafast tune=zerolatency '
            f'! rtph264pay config-interval=1 name=pay0 pt=96'
        )

    def do_create_element(self, url):
        return Gst.parse_launch(self.launch_string)

    def do_configure(self, rtsp_media):
        self.number_frames = 0
        appsrc = rtsp_media.get_element().get_child_by_name('source')
        appsrc.connect('need-data', self.on_need_data)

    def on_need_data(self, src, length):
        try:
            # ดึงภาพจากคิว
            frame = self.output_queue.get(timeout=0.1)
            
            data = frame.tobytes()
            buf = Gst.Buffer.new_allocate(None, len(data), None)
            buf.fill(0, data)
            buf.duration = self.duration
            
            timestamp = self.number_frames * self.duration
            buf.pts = buf.dts = int(timestamp)
            buf.offset = timestamp
            
            self.number_frames += 1
            src.emit('push-buffer', buf)
            
        except queue.Empty:
            pass

class RTSPOUTPUTProducer(threading.Thread):
    def __init__(self, config: dict, output_queue: queue.Queue):
        super().__init__()
        self.config = config.get('output_stream', {})
        self.output_queue = output_queue
        self.running = True
        self.daemon = True
        self.logger = logging.getLogger("AIPipeline")
        
        # ดึงการตั้งค่า IP และ Port เตรียมไว้
        self.ip_address = str(self.config.get('ip_address', '0.0.0.0'))
        self.port = str(self.config.get('port', 8555))
        self.mount = self.config.get('mount', '/result')
        self.width = self.config.get('width', 640)
        self.height = self.config.get('height', 480)
        self.fps = self.config.get('fps', 30)
        
        self.loop = None
        self.server = None

    def run(self):
        """ย้ายการสร้างและผูก Server มาไว้ใน Thread เดียวกับ Loop"""
        Gst.init(None)
        self.server = GstRtspServer.RTSPServer()
        self.server.set_address(self.ip_address)
        self.server.set_service(self.port)
        
        factory = QueueMediaFactory(self.output_queue, self.fps, self.width, self.height)
        factory.set_shared(True)
        self.server.get_mount_points().add_factory(self.mount, factory)
        self.server.attach(None)
        
        display_ip = "ANY_IP (0.0.0.0)" if self.ip_address == "0.0.0.0" else self.ip_address
        self.logger.info(f"[RTSPOutput] Result Stream is LIVE at rtsp://{display_ip}:{self.port}{self.mount}")
        
        self.loop = GLib.MainLoop()
        self.loop.run()

    def stop(self):
        self.running = False
        if self.loop is not None:
            self.loop.quit()
        self.logger.debug("[RTSPOutput] Stop signal received.")
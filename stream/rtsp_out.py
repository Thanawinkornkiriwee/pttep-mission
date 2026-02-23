import threading
import queue
import logging
import cv2
import gi
import numpy as np

gi.require_version('Gst', '1.0')
gi.require_version('GstRtspServer', '1.0')
from gi.repository import Gst, GstRtspServer, GLib

class StreamHandler:
    """ตัวช่วยจัดการสถานะภาพของแต่ละสตรีมแยกจากกัน (OCR, Analog ฯลฯ)"""
    def __init__(self, stream_name, out_queue, fps, width, height):
        self.stream_name = stream_name
        self.queue = out_queue
        self.fps = fps
        self.width = width
        self.height = height
        self.duration = int((1.0 / self.fps) * Gst.SECOND)
        self.number_frames = 0
        self.last_frame = None

    def on_media_configure(self, factory, media):
        self.number_frames = 0
        appsrc = media.get_element().get_child_by_name('source')
        if appsrc:
            appsrc.connect('need-data', self.on_need_data)

    def on_need_data(self, src, length):
        try:
            frame = self.queue.get_nowait()
            self.last_frame = frame
        except queue.Empty:
            frame = self.last_frame

        if frame is None:
            # ถ้ายังไม่มีภาพส่งมาเลย ให้สร้างภาพสีดำและพิมพ์ชื่อ Task รอไว้
            frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
            cv2.putText(frame, f"Waiting for {self.stream_name.upper()}...", 
                        (50, self.height//2), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

        data = frame.tobytes()
        buf = Gst.Buffer.new_allocate(None, len(data), None)
        buf.fill(0, data)
        buf.duration = self.duration
        
        timestamp = self.number_frames * self.duration
        buf.pts = buf.dts = timestamp
        buf.offset = timestamp
        
        self.number_frames += 1
        src.emit('push-buffer', buf)

class RTSPOUTPUTProducer(threading.Thread):
    def __init__(self, config: dict, output_queues: dict): # รับตะกร้าแบบหลายใบ (Dict)
        super().__init__()
        self.config = config.get('output_stream', {})
        self.output_queues = output_queues
        self.running = True
        self.daemon = True
        self.logger = logging.getLogger("AIPipeline")
        
        self.ip_address = str(self.config.get('ip_address', '0.0.0.0'))
        self.port = str(self.config.get('port', 8555))
        self.mounts = self.config.get('mounts', {'od': '/od'})
        self.width = self.config.get('width', 640)
        self.height = self.config.get('height', 480)
        self.fps = self.config.get('fps', 30)
        
        self.loop = None
        self.server = None
        self.handlers = []

    def run(self):
        if not Gst.is_initialized():
            Gst.init(None)

        self.server = GstRtspServer.RTSPServer()
        self.server.set_address(self.ip_address)
        self.server.set_service(self.port)
        display_ip = "127.0.0.1" if self.ip_address == "0.0.0.0" else self.ip_address
        
        # วนลูปสร้างเส้นทาง (Mount Point) สำหรับทุกตะกร้าที่ระบุไว้ใน Config
        for stream_name, mount_path in self.mounts.items():
            if stream_name in self.output_queues:
                factory = GstRtspServer.RTSPMediaFactory()
                
                launch_string = (
                    f'appsrc name=source is-live=true block=true format=GST_FORMAT_TIME '
                    f'caps=video/x-raw,format=BGR,width={self.width},height={self.height},framerate={self.fps}/1 '
                    f'! videoconvert ! video/x-raw,format=I420 '
                    f'! x264enc speed-preset=ultrafast tune=zerolatency '
                    f'! rtph264pay config-interval=1 name=pay0 pt=96'
                )
                factory.set_launch(launch_string)
                factory.set_shared(True)
                
                # ผูกตะกร้าเข้ากับ Handler ประจำตัว
                q = self.output_queues[stream_name]
                handler = StreamHandler(stream_name, q, self.fps, self.width, self.height)
                self.handlers.append(handler)
                
                factory.connect("media-configure", handler.on_media_configure)
                self.server.get_mount_points().add_factory(mount_path, factory)
                self.logger.info(f"[{stream_name.upper()} Stream] LIVE at rtsp://{display_ip}:{self.port}{mount_path}")

        self.loop = GLib.MainLoop()
        self.loop.run()

    def stop(self):
        self.running = False
        if self.loop is not None:
            self.loop.quit()
        self.logger.debug("[RTSPOutput] Stop signal received.")
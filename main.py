import argparse
import queue
import time
import sys

from cores import load_config, setup_logger
from stream.input_factory import InputFactory
from stream.rtsp_out import RTSPOUTPUTProducer
from tasks.task_manager import TaskManager

def main():
    # ==========================================
    # 1. Parse Arguments (ตั้งค่าโหมดรับภาพ)
    # ==========================================
    parser = argparse.ArgumentParser(description="PTTEP Mission - AI Pipeline")
    parser.add_argument('--mode', type=str, choices=['rtsp', 'http', 'video', 'image'], default='image', 
                        help="Choose input mode")
    args = parser.parse_args()

    # ==========================================
    # 2. โหลด Config & ตั้งค่า Logger
    # ==========================================
    try:
        config = load_config()
        logger = setup_logger(config)
        logger.info(f"=== Starting AI Pipeline in [{args.mode.upper()}] mode ===")
    except Exception as e:
        print(f"CRITICAL ERROR: Failed to initialize Core systems: {e}")
        sys.exit(1)

    # ==========================================
    # 3. สร้างตะกร้า (Queues) สำหรับรับส่งภาพ
    # ==========================================
    buffer_size = config['receive_img'].get('buffer_size', 1)
    
    # ตะกร้ารับภาพขาเข้า
    frame_queue = queue.Queue(maxsize=buffer_size)
    
    # ตะกร้าส่งภาพขาออก (แยกเป็น Dictionary ตามแผนก เพื่อให้ RTSP ดึงไปสร้าง Stream แยกช่องได้)
    # หมายเหตุ: Key ตรงนี้ต้องตั้งชื่อให้ตรงกับตัวแปร mounts ใน config.yaml
    output_queues = {
        'od': queue.Queue(maxsize=buffer_size),
        'ocr': queue.Queue(maxsize=buffer_size),
        'analog': queue.Queue(maxsize=buffer_size),
        'classification': queue.Queue(maxsize=buffer_size)
    }

    # ==========================================
    # 4. สร้าง Components ต่างๆ (Producers & Consumer)
    # ==========================================
    try:
        # ฝั่งรับภาพ (Camera/HTTP)
        input_producer = InputFactory.create_producer(mode=args.mode, config=config, frame_queue=frame_queue)
    except Exception as e:
        logger.error(f"Failed to create Input Producer: {e}")
        sys.exit(1)

    # ฝั่งส่งภาพออก (RTSP Server หลายช่อง)
    output_producer = RTSPOUTPUTProducer(config=config, output_queues=output_queues)

    # ฝั่งสมอง AI (ดึงภาพเข้า -> คิด -> โยนลงตะกร้าขาออก)
    ai_consumer = TaskManager(config=config, frame_queue=frame_queue, output_queues=output_queues)

    # ==========================================
    # 5. สั่งให้ทุกส่วนเริ่มทำงานคู่ขนานกัน (Start Threads)
    # ==========================================
    input_producer.start()
    output_producer.start()
    ai_consumer.start()

    logger.info("Pipeline is running. Press Ctrl+C to stop.")

    # ==========================================
    # 6. วงลูปหลักและการปิดระบบอย่างปลอดภัย (Graceful Shutdown)
    # ==========================================
    try:
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt detected. Shutting down pipeline gracefully...")
        
        # ส่งสัญญาณหยุดไปยัง Thread ต่างๆ
        input_producer.stop()
        output_producer.stop()
        ai_consumer.stop() 
        
        # รอให้ Thread เคลียร์ Memory และปิดตัวเองจนเสร็จสมบูรณ์
        input_producer.join()
        output_producer.join()
        ai_consumer.join() 
        
        logger.info("=== Pipeline shutdown complete. ===")

if __name__ == "__main__":
    main()
import argparse
import queue
import time
import sys

from cores import load_config, setup_logger
from stream.input_factory import InputFactory

# 1. นำเข้า TaskManager ที่เราเพิ่งสร้าง
from tasks.task_manager import TaskManager 
from stream.rtsp_out import RTSPOUTPUTProducer

def main():
    parser = argparse.ArgumentParser(description="PTTEP Mission - AI Pipeline")
    parser.add_argument('--mode', type=str, choices=['video', 'image'], default='image', 
                        help="Choose input mode")
    args = parser.parse_args()

    try:
        config = load_config()
        logger = setup_logger(config)
        logger.info(f"=== Starting AI Pipeline in [{args.mode.upper()}] mode ===")
    except Exception as e:
        print(f"CRITICAL ERROR: Failed to initialize Core systems: {e}")
        sys.exit(1)

    buffer_size = config['receive_img'].get('buffer_size', 1)
    frame_queue = queue.Queue(maxsize=buffer_size)
    output_queue = queue.Queue(maxsize=buffer_size)

    try:
        input_producer = InputFactory.create_producer(mode=args.mode, config=config, frame_queue=frame_queue)
    except Exception as e:
        logger.error(f"Failed to create Input Producer: {e}")
        sys.exit(1)


    output_producer = RTSPOUTPUTProducer(config=config, output_queue=output_queue)

    # ==========================================
    # 2. สร้าง AI Consumer และโยนตะกร้าใบเดียวกัน (frame_queue) ให้มัน
    # ==========================================
    ai_consumer = TaskManager(config=config, frame_queue=frame_queue, output_queue=output_queue)

    # ==========================================
    # 3. สั่งให้เริ่มทำงานคู่ขนานกัน
    # ==========================================
    input_producer.start()
    output_producer.start()
    ai_consumer.start()

    logger.info("Pipeline is running. Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt detected. Shutting down pipeline gracefully...")
        
        # ==========================================
        # 4. สั่งหยุดการทำงานทั้ง 2 ส่วน
        # ==========================================
        input_producer.stop()
        output_producer.stop()
        ai_consumer.stop() 
        
        # ==========================================
        # 5. รอให้ Thread ปิดตัวเรียบร้อย
        # ==========================================
        input_producer.join()
        ai_consumer.join() 
        
        logger.info("=== Pipeline shutdown complete. ===")

if __name__ == "__main__":
    main()
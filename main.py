import argparse
import queue
import time
import sys
from cores import load_config, setup_logger
from stream.input_factory import InputFactory


def main():

    parser = argparse.ArgumentParser(description="PTTEP Mission - AI Pipeline")
    parser.add_argument('--mode', type=str, choices=['video', 'image'], default='video', 
                        help="Choose input mode: 'video' (Video Stream) or 'image' (Static Image)")
    args = parser.parse_args()


    try:
        config = load_config()
        logger = setup_logger(config)
        logger.info(f"=== Starting AI Pipeline in [{args.mode.upper()}] mode ===")
    except Exception as e:
        print(f"CRITICAL ERROR: Failed to initialize Core systems: {e}")
        sys.exit(1)

    # ==========================================
    # Create Queue (Buffer) connect between receive image and AI
    # ==========================================
    buffer_size = config['receive_img'].get('buffer_size', 1)
    frame_queue = queue.Queue(maxsize=buffer_size)
    logger.debug(f"Frame queue initialized with maxsize={buffer_size}")

    # ==========================================
    # 4. call Factory create Producer (receive image)
    # ==========================================
    try:
        input_producer = InputFactory.create_producer(mode=args.mode, config=config, frame_queue=frame_queue)
    except Exception as e:
        logger.error(f"Failed to create Input Producer: {e}")
        sys.exit(1)

    # ==========================================
    # 5. สร้าง Consumer (ส่วน AI YOLO / Tasks) (เดี๋ยวมาเขียนเพิ่ม)
    # ==========================================
    # ai_consumer = TaskManager(config=config, frame_queue=frame_queue)

   
    input_producer.start()
    # ai_consumer.start()

    logger.info("Pipeline is running. Press Ctrl+C to stop.")

    
    try:
        
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt detected. Shutting down pipeline gracefully...")
        
        # สั่งหยุด Thread ต่างๆ
        input_producer.stop()
        # ai_consumer.stop()
        
        # รอให้ Thread ปิดตัวเรียบร้อย
        input_producer.join()
        # ai_consumer.join()
        
        logger.info("=== Pipeline shutdown complete. ===")

if __name__ == "__main__":
    main()
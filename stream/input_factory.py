import queue
from stream.rtsp_rev import RTSPRECEIVEProducer
# from stream.http_input import HTTPReceiveProducer # (to be written in the future)

class InputFactory:
    """
    Factory Pattern for creating Input Producers based on the selected mode.
    """
    
    @staticmethod
    def create_producer(mode: str, config: dict, frame_queue: queue.Queue):
        """
        Decision maker for creating the appropriate Producer.
        """
        if mode == 'video':
            # Get RTSP URL from config
            url = config['receive_img']['rtsp_url']
            # Return the video receiver object (already implemented)
            return RTSPRECEIVEProducer(rtsp_url=url, frame_queue=frame_queue)
            
        elif mode == 'image':
            # Get HTTP URL from config (to be added in config.yaml later)
            url = config['receive_img'].get('http_url', 'http://localhost/image.jpg')
            # Return the image receiver object (to be implemented)
            # return HTTPReceiveProducer(http_url=url, frame_queue=frame_queue)
            
            # Temporary until http_input.py is implemented
            raise NotImplementedError("image mode is not yet implemented.")
            
        else:
            raise ValueError(f"Unknown input mode: {mode}")
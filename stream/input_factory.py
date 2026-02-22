import queue
from stream.rtsp_rev import RTSPRECEIVEProducer
from stream.http_rev import HTTPRECEIVEProducer

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
           
            url = config['receive_img']['rtsp_url']
            
            return RTSPRECEIVEProducer(rtsp_url=url, frame_queue=frame_queue)
            
        elif mode == 'image':
         
            url = config['receive_img']['http_url']
            
            
            
            return HTTPRECEIVEProducer(http_url=url, frame_queue=frame_queue)
        else:
            raise ValueError(f"Unknown input mode: {mode}")
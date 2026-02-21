import logging
import logging.handlers
import os

def setup_logger(config):
    """
    Set up a Professional Logging System (Dual-File Strategy)
    • 	Display logs on the console
    • 	Record everything into the main log file (e.g., ) according to the configured log level
    • 	Record only ERROR and CRITICAL messages into a separate log file (e.g., )

    """
    
   
    log_level_str = config['system'].get('log_level', 'INFO').upper()
    base_log_file = config['system'].get('log_file', 'logs/system.log')
    
    
    log_levels = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }
    level = log_levels.get(log_level_str, logging.INFO)

   
    os.makedirs(os.path.dirname(base_log_file), exist_ok=True)

   
    logger = logging.getLogger("AIPipeline")
    logger.setLevel(level) 
    
    
    if logger.hasHandlers():
        logger.handlers.clear()

    formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(filename)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # =========================================================
    # Handler 1: Display on screen (Console)
    # =========================================================
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # =========================================================
    # Handler 2: File Log 
    # =========================================================
    main_file_handler = logging.handlers.RotatingFileHandler(
        filename=base_log_file, 
        maxBytes=5 * 1024 * 1024, # remove if file larger than 5 MB
        backupCount=10,            # backup storage 5  File
        encoding='utf-8'
    )
    main_file_handler.setLevel(level)
    main_file_handler.setFormatter(formatter)
    logger.addHandler(main_file_handler)

    # =========================================================
    # Handler 3: File Log only Error (Filter ERROR level)
    # =========================================================
    
    file_name, file_extension = os.path.splitext(base_log_file)
    error_log_file = f"{file_name}_error{file_extension}"
    
    error_file_handler = logging.handlers.RotatingFileHandler(
        filename=error_log_file, 
        maxBytes=5 * 1024 * 1024, 
        backupCount=5, 
        encoding='utf-8'
    )
    error_file_handler.setLevel(logging.ERROR) 
    error_file_handler.setFormatter(formatter)
    logger.addHandler(error_file_handler)

    return logger
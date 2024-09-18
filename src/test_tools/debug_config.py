import logging
import colorlog

# Configurazione del logger
logger = logging.getLogger('PlateRecognitionServer')
logger.setLevel(logging.DEBUG)

# Formattatore per la console (con colori)
console_formatter = colorlog.ColoredFormatter(
    '%(log_colors)s%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    log_color={
        'DEBUG': 'white',
        'INFO': 'green',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'bold_red',
    }
)

# Handler per la console
console_handler = logging.StreamHandler()
console_handler.setFormatter(console_formatter)
console_handler.setLevel(logging.DEBUG)

# Aggiungi l'handler al logger
logger.addHandler(console_handler)

# Esempi di log colorati
logger.debug("Debug message")
logger.info("Information message.")
logger.warning("Warning message")
logger.error("Error message")
logger.critical("Critic message")

logger.info('In order to display colors you need to install colorlog with pip install colorlog')
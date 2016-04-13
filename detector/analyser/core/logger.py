import logging
import logging.handlers
from logging import *
from datetime import *

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

rht = logging.handlers.TimedRotatingFileHandler("detector.log", 'D')
fmt = logging.Formatter("%(asctime)s %(pathname)s %(filename)s %(funcName)s %(lineno)s \
     %(levelname)s - %(message)s", "%Y-%m-%d %H:%M:%S")
rht.setFormatter(fmt)
logger.addHandler(rht)

debug = logger.debug
info = logger.info
warning = logger.warn
error = logger.error
critical = logger.critical

import time
from .log import getLogger

logger = getLogger(__name__)

def show_perf(func):
    start = time.perf_counter()
    func()
    logger.debug(f'{func.__name__} Cost: {time.perf_counter() - start}')


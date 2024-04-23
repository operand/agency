import multiprocessing
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor


class ResourceManager:
    """
    Singleton for globally managing concurrency primitives
    """
    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(ResourceManager, cls).__new__(cls)
        return cls._instance

    def __init__(self, max_workers=None):
        if not self._initialized:
            self._max_workers = max_workers
            self.thread_pool_executor = ThreadPoolExecutor(self._max_workers)
            self.process_pool_executor = ProcessPoolExecutor(self._max_workers)
            self.multiprocessing_manager = multiprocessing.Manager()
            self._initialized = True

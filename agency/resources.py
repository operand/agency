import multiprocessing
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor


class ResourceManager:
    """
    Singleton for globally managing concurrency primitives
    """
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ResourceManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self.thread_pool_executor = ThreadPoolExecutor()
            self.process_pool_executor = ProcessPoolExecutor()
            self.multiprocessing_manager = multiprocessing.Manager()
            self._initialized = True

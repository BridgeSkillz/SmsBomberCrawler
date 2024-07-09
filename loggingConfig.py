import logging
from rich.logging import RichHandler

def setup_logging(level=logging.DEBUG,filename="logs.log"):

    fileHandler = logging.FileHandler(filename)
    formatter = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] -> %(funcName)s() -> %(message)s",datefmt='%d/%m/%Y %H:%M:%S')
    fileHandler.setFormatter(formatter) 

    consoleHandler = RichHandler()

    logging.basicConfig(
        level=level,
        handlers=[consoleHandler, fileHandler],
        format="[%(name)s] -> %(funcName)s() -> %(message)s",
        datefmt='%d/%m/%Y %H:%M:%S',
    )

# setup_logging()

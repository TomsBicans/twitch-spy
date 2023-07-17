import logging
import time
import src.app as app


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)


if __name__ == "__main__":
    start_time = time.time()
    app.main()
    end_time = time.time()
    logging.info(f"Program finished in {end_time - start_time:.2f} seconds.")

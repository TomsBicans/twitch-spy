import logging
import time
import twitch_spy.app as app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)


def main():
    start_time = time.time()
    app.main()
    end_time = time.time()
    logging.info(f"Program finished in {end_time - start_time:.2f} seconds.")


if __name__ == "__main__":
    main()

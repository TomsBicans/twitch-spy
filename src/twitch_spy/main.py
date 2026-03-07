import logging
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)


def main():
    # Parse args and init config before importing app so that all downstream
    # modules (system_logger, storage_manager, etc.) see the correct paths.
    from twitch_spy import cli
    args = cli.parse_args()

    import twitch_spy.config as config
    config.init(args.output_dir)

    import twitch_spy.app as app

    start_time = time.time()
    app.main()
    end_time = time.time()
    logging.info(f"Program finished in {end_time - start_time:.2f} seconds.")


if __name__ == "__main__":
    main()

import os

class OS:
    @staticmethod
    def read_file(file: str):
        """Read file and return content as string."""
        with open(file, 'r', encoding='utf-8') as f:
            content = f.read()
            return content

    @staticmethod
    def create_dir(dir: str):
        """Create the directory if it does not exist."""
        if not os.path.exists(dir):
            os.mkdir(dir)
            return dir
        else:
            return dir
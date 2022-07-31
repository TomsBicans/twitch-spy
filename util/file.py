class File:
    @staticmethod
    def read_file(file: str):
        """Read file and return content as string."""
        with open(file, 'r', encoding='utf-8') as f:
            content = f.read()
            return content
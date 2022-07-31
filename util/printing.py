from math import floor

def mini_print(data: list, threshold: int = None):
    """Omit data in middle of list if list size is above threshold."""
    print(len(data), threshold)
    if len(data) > threshold:
        res = []
        res.extend(data[0:floor(threshold/2)])
        res.append(f"{len(data) - threshold} items ommited.".upper())
        res.extend(data[-(floor(threshold/2)+1):])
        return res
    else:
        return data
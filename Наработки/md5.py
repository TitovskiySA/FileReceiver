import os
import hashlib

def getMd5(path):
    m = hashlib.md5()
    with open(path, "rb") as f:
        lines = f.read()
        m.update(lines)

    md5code = m.hexdigest()
    return md5code

probe = getMd5("C:\\Users\\Алексей\\Desktop\\FileReceiver\\kriminalnoe_chtivo.avi")
print(probe)
inBytes = probe.encode("utf-8")
size = len(inBytes)
print(str(size))

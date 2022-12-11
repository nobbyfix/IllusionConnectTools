from . import xxtea_cocos2d, xxtea_vars
from pathlib import Path


# CONSTANTS
SIGN_LUA = xxtea_vars.calculate_sign(True)
SIGN_OTHER = xxtea_vars.calculate_sign(False)


# execute decryption
def xxtea_decrypt(databytes: bytes, decrypt_len: int, key: bytes):
	datasrc_todecrypt = databytes[:decrypt_len]
	decrypted_bytes = xxtea_cocos2d.decrypt(datasrc_todecrypt, key)
	data_result = b''.join((decrypted_bytes, databytes[decrypt_len:]))
	return data_result

def decrypt(datain: bytes):
	if datain[:len(SIGN_LUA)] == SIGN_LUA:
		is_lua = True
		signlen = len(SIGN_LUA)
	elif datain[:len(SIGN_OTHER)] == SIGN_OTHER:
		is_lua = False
		signlen = len(SIGN_OTHER)
	else:
		return datain

	datasrc = datain[signlen:]
	key = xxtea_vars.generate_key(datasrc[0], datasrc[1]).ljust(16, b'\0')
	assert len(key) == 16

	if is_lua:
		datasrc_clean = datasrc[2:]
		decrypt_len = len(datasrc)-2
	else:
		datasrc_clean = datasrc[6:]
		decrypt_len = datasrc[5] | ((datasrc[4] | ((datasrc[3] | (datasrc[2] << 8)) << 8)) << 8)

	assert len(datasrc_clean) >= 0
	return xxtea_decrypt(datasrc_clean, decrypt_len, key)


def decrypt_file(srcfile, targetfile):
	with open(srcfile, "rb") as srcf:
		src_bytes = srcf.read()
	bytes_out = decrypt(src_bytes)
	with open(targetfile, "wb") as targetf:
		targetf.write(bytes_out)
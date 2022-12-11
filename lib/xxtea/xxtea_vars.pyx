#cython: language_level=3

def calculate_sign(bint isluafile):
	cdef char[7] v, v2

	if isluafile:
		v = [0xF5, 0xB1, 0x92, 0xC2, 0xE6, 0xB5, 0x90] # @D#P$S% <- lua
	else:
		v = [0xF5, 0xA6, 0x85, 0xD1, 0xF5, 0xBA, 0x9F] # @S#T$O% <- other

	v2[0] = v[0] ^ 0xB5
	v2[1] = v[1] ^ v[0]
	v2[2] = v[2] ^ v[1]
	v2[3] = v[3] ^ v[2]
	v2[4] = v[4] ^ v[3]
	v2[5] = v[5] ^ v[4]
	v2[6] = v[5] ^ v[6]
	
	return v2

cdef calculate_key():
	cdef unsigned char i, var
	cdef unsigned char[48] key
	cdef unsigned char[49] keybytes

	for i in range(48): key[i] = 0 # init key
	keybytes = [
		0xF6, 0x99, 0xE9, 0x90,		0xE2, 0x8B, 0xEC, 0x84,
		0xF0, 0xD8, 0x9B, 0xB2,		0x9E, 0xAC, 0x9C, 0xAD,
		0x9A, 0xB6, 0xF2, 0x80,		0xE1, 0x86, 0xE9, 0x87,
		0xD7, 0xA2, 0xCC, 0xAF,		0xC7, 0x94, 0xE0, 0x8F,
		0xFD, 0x90, 0xB0, 0xE4,		0x81, 0xE2, 0x8A, 0xA4,
		0xE7, 0x88, 0xA6, 0x8A,		0xC6, 0xB2, 0xD6, 0xF8,
		0xF8
	]
	
	var = -75
	for i in range(49):
		key[i] = var ^ keybytes[i]
		var = keybytes[i]
	return key


cdef unsigned char[48] GLOBAL_KEY = calculate_key()
cdef unsigned char GLOBAL_KEYLEN = len(GLOBAL_KEY)

def generate_key(int char1, int char2):
	cdef int var1
	cdef unsigned char delta
	cdef unsigned char[16] deltakey

	delta = (char2 + char1) % 13
	if delta < 8: delta = 8

	for i in range(16): deltakey[i] = 0 # init deltakey
	deltakey[0] = GLOBAL_KEY[char1 % GLOBAL_KEYLEN] # v31
	deltakey[1] = GLOBAL_KEY[char2 % GLOBAL_KEYLEN] # v32

	for i in range(2, delta):
		var1 = char2 + char1
		char1 = char2
		char2 = var1
		deltakey[i] = GLOBAL_KEY[var1 % GLOBAL_KEYLEN]

	return deltakey
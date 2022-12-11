import sqlite3, json
from pathlib import Path

GLOBAL_KEY = "dpstorm.or.2019.07.24".encode('ascii')
KEYLEN = len(GLOBAL_KEY)

def decrypt_bytes(DATA_IN: bytes):
	DATA_OUT = bytearray(DATA_IN)
	for i in range(len(DATA_IN)):
		var = GLOBAL_KEY[(i+1) % KEYLEN] ^ DATA_IN[i]
		DATA_OUT[i] = GLOBAL_KEY[i % KEYLEN] ^ var
	return DATA_OUT
def decrypt_row(rowdata: str):
	if rowdata[0] != "`":
		return rowdata
	dataout = decrypt_bytes(bytes.fromhex(rowdata[1:]))
	return dataout.decode('utf8')

def decrypt_db(dbpath: Path):
	conn = sqlite3.connect(str(dbpath))
	master_cursor = conn.execute("SELECT * FROM sqlite_master")
	for schema_row in master_cursor.fetchall():
		if schema_row[0] != 'table': continue

		# do table decrypt
		tablename = schema_row[2]
		cursor = conn.execute(f"SELECT * FROM {tablename}")
		for row_index, encrypted_data in cursor.fetchall():
			decrypted_data = decrypt_row(encrypted_data)
			conn.execute(f"REPLACE INTO {tablename} VALUES (?, ?)", (row_index, decrypted_data,))
		conn.commit()
	conn.close()


def merge_db(default_db_path: Path, merger_db_path: Path):
	conn = sqlite3.connect(str(default_db_path))
	conn.execute("ATTACH DATABASE ? AS new", (str(merger_db_path),))
	cursor = conn.execute("SELECT * FROM new.sql")
	for _, replace_sql_query in cursor.fetchall():
		for sql_query in replace_sql_query.split(";"):
			conn.execute(sql_query)
		conn.commit()
	conn.close()
	merger_db_path.unlink()


def convert_table(cursor, tablename: str, targetdir: Path):
	cursor.execute(f"SELECT * FROM {tablename} WHERE Id='Id'")
	columns = cursor.fetchone()[1].split("#@#")

	cursor.execute(f"SELECT * FROM {tablename} WHERE Id='DataType'")
	datatypes = cursor.fetchone()[1].split("#@#")

	cursor.execute(f"SELECT * FROM {tablename} WHERE Id NOT IN (?, ?)", ('Id', 'DataType'))
	json_out = {}
	for row_index, data in cursor.fetchall():
		data_content = data.split("#@#")
		json_out[row_index] = {}
		for i, content in enumerate(data_content):
			if content == '' or datatypes[i] == 'string':
				content_convert = content
			elif datatypes[i] in ('int', 'long'):
				content_convert = int(content)
			elif datatypes[i] == 'double':
				content_convert = float(content)
			elif datatypes[i] in ('array', 'dict', 'auto'):
				content_convert = json.loads(content or '{}')
			json_out[row_index][columns[i]] = content_convert
		
	with open(Path(targetdir, f"{tablename}.json"), 'w', encoding='utf8') as f:
		json.dump(json_out, f, indent=4, ensure_ascii=False, sort_keys=True)

def convert_db(dbpath: Path, targetdir: Path):
	targetdir.mkdir(parents=True, exist_ok=True)
	
	db = sqlite3.connect(str(dbpath))
	c = db.cursor()

	c.execute("SELECT * FROM sqlite_master")
	for schema_row in c.fetchall():
		if schema_row[0] != 'table': continue
		convert_table(c, schema_row[2], targetdir)
	db.close()
from pathlib import Path
import subprocess, sys
import multiprocessing as mp


LUA_COMPILED_HEAD = bytes([0x1B, 0x4C, 0x4A, 0x02])
def is_lua_compiled(filepath: Path):
	with open(filepath, 'rb') as f:
		filehead = f.read(4)
	return filehead == LUA_COMPILED_HEAD

LUA_DECOMPILER_PATH = Path("lib", "bin", "luajit-decompiler", "main.py")
def decompile_lua_file(file_in: Path, file_out: Path):
	# checks if the file is compiled
	if not is_lua_compiled(file_in):
		file_in.rename(file_out)
		return
	
	try:
		subprocess.run(
			["py", str(LUA_DECOMPILER_PATH), "-f", str(file_in), "-o", str(file_out), "-c"],
			stdout=subprocess.DEVNULL,
			stderr=subprocess.DEVNULL)
		#subprocess.Popen(["py", "LJDecompiler.py", "-f", str(file_in), "-o", str(file_out), "-c"]).wait()
		if file_in != file_out:
			file_in.unlink()
	except:
		print(f'ERROR: "{file_in}" failed to decompile.')


def recursive_decompile_dir(src_dir: Path, search_pattern: str = '*.luac'):
	pool = mp.Pool(mp.cpu_count()-1)
	for luafile in src_dir.rglob(search_pattern):
		targetfile = luafile.with_suffix('.lua')
		pool.apply_async(decompile_lua_file, (luafile,targetfile,))
	pool.close()
	pool.join()
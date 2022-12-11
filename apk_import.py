import shutil, json, sqlite3, argparse
from pathlib import Path
from zipfile import ZipFile, ZipInfo

from lib import Client, util, xxtea, gameconfig, decompile


def execute_clear(*args: Path):
	for dir_ in args:
		if dir_.exists():
			shutil.rmtree(dir_, ignore_errors=True)


def extract_file(zipfile: ZipFile, srcpath: ZipInfo, targetpath: Path, do_mkdirs: bool = False):
	if srcpath.is_dir():
		targetpath.mkdir(exist_ok=True)
	else:
		if do_mkdirs: util.mkdirs(targetpath)
		with zipfile.open(srcpath, 'r') as assetfile, open(targetpath, 'wb') as assettargetfile:
			filebytes = assetfile.read()
			filebytes = xxtea.decrypt(filebytes)
			assettargetfile.write(filebytes)

def extract_obb(zipfile: ZipFile, obbpath: str, targetfolder: Path):
	with zipfile.open(obbpath, 'r') as mainobbfile:
		with ZipFile(mainobbfile, 'r') as main_obb:
			fileamount = len(main_obb.filelist)
			progressbar = util.ProgressBar(fileamount, prefix='Unpacking:')
			for i, file in enumerate(main_obb.filelist, 1):
				targetpath = Path(targetfolder, file.filename)
				extract_file(main_obb, file, targetpath)
				progressbar.update(i)

def execute_extraction(xapk_path: Path, unpack_targetdir: Path):
	print("Unpacking XAPK archive...")
	util.mkdir(unpack_targetdir)
	with ZipFile(xapk_path, 'r') as xapk_archive:
		print("Reading Manifest.json...")
		with xapk_archive.open('manifest.json', 'r') as manifestfile:
			manifest = json.loads(manifestfile.read().decode('utf8'))
	
		print("Unpacking additional asset archives...")
		for obb_expansion in manifest['expansions']:
			extract_obb(xapk_archive, obb_expansion['file'], unpack_targetdir)
		
		print('Unpacking APK archive...')
		APK_PATH = manifest['split_apks'][0]['file']
		with xapk_archive.open(APK_PATH, 'r') as apk_archivefile:
			with ZipFile(apk_archivefile, 'r') as apk_archive:
				print('Extracting apk assets...')
				fileamount = len(apk_archive.filelist)
				progressbar = util.ProgressBar(fileamount, prefix='Unpacking:')
				for i, file in enumerate(apk_archive.filelist, 1):
					if file.filename.startswith('assets/release/'):
						targetpath = Path(unpack_targetdir, file.filename.lstrip('assets/'))
						extract_file(apk_archive, file, targetpath, True)
					progressbar.update(i)
				
				print('Extracting assets.db...')
				assetdbinfo = apk_archive.NameToInfo['assets/64/assets.db']
				assetdbtarget = Path(unpack_targetdir, 'assets.db')
				extract_file(apk_archive, assetdbinfo, assetdbtarget)

				print('Extracting cocos_app.conf...')
				confinfo = apk_archive.NameToInfo['assets/cocos_app.conf']
				conftarget = Path(unpack_targetdir, 'cocos_app.conf')
				extract_file(apk_archive, confinfo, conftarget)
				
	print("Finished extraction.")

def rename_file(src: Path, target: Path, no_copy):
	if target.exists(): return False
	util.mkdirs(target)
	if no_copy: shutil.copyfile(src, target)
	else: src.rename(target)
	return True

def execute_rename(unpack_dir: Path, rename_targetdir: Path):
	print("Reading asset database...")
	ASSETDB_PATH = Path(unpack_dir, 'assets.db')
	conn = sqlite3.connect(str(ASSETDB_PATH))
	c = conn.cursor()
	c.execute('SELECT * FROM assets')
	result = c.fetchall()
	conn.close()

	print("Categorizing assets...")
	categorizeddata = {}
	fileamount = len(result)
	progressbar = util.ProgressBar(fileamount, prefix='Categorizing:')
	for i, datarow in enumerate(result, 1):
		assetpath, _, dbpath, _, _, _ = datarow
		# assetpath, version dbpath, size, hash, external
		# external	- 0: other files
		#			- 1: video/sound files
		# version	- seems to be always same for all files
		if dbpath in categorizeddata:
			categorizeddata[dbpath].append(assetpath)
		else:
			categorizeddata[dbpath] = [assetpath]
		progressbar.update(i)

	print("Renaming asset paths...")
	errorlogger = util.ErrorLogger("rename_errors.log")
	catdatalen = len(categorizeddata)
	progressbar = util.ProgressBar(catdatalen, prefix='Renaming:')
	for i, filedata in enumerate(categorizeddata.items(), 1):
		dbpath, targetpaths = filedata
		srcpath = Path(unpack_dir, dbpath)
		if srcpath.exists():
			for j, targetpath in enumerate(targetpaths):
				filetarget = Path(rename_targetdir, targetpath)
				if not rename_file(srcpath, filetarget, j):
					errorlogger.add_message(f"Error on: {srcpath} -> {filetarget}: Target already exists.")
				if j == 0:
					srcpath = filetarget
		else:
			errorlogger.add_message(f"{srcpath} of {assetpath} can not be found.\n")
		progressbar.update(i)
	errorlogger.output()
	print("Finished renaming.")

def execute_tidy(unpack_dir: Path, target_dir: Path):
	print("Tidying up remaining files...")
	util.mkdir(target_dir)
	for filepath in Path(unpack_dir, 'release').rglob('*'):
		if filepath.is_dir(): continue
		if filepath.suffix == '.luac': continue # skip 32 bit lua files
		if filepath.name == '.packres_success': continue # uninteresting file that is always left over
		filepath.rename(Path(target_dir, filepath.name))

	# rename the config file
	confpath = Path(unpack_dir, 'cocos_app.conf')
	confpath.rename(Path(target_dir, confpath.name))

	print("Removing unpack directory...")
	execute_clear(unpack_dir)
	print("Finished tidying.")

def execute_gc_extract(client_asset_dir: Path, json_out_dir: Path):
	gc_archive_path = Path(client_asset_dir, "gameConfig.db.zip")
	if gc_archive_path.exists():
		with ZipFile(gc_archive_path, 'r') as gc_archive:
			gc_archive.extractall(client_asset_dir)
		gc_archive_path.unlink()

		# decrypt and convert database
		gc_db_path = Path(client_asset_dir, "gameConfig.db")
		gameconfig.decrypt_db(gc_db_path)
		gameconfig.convert_db(gc_db_path, json_out_dir)
	else:
		print("Can't unpack gameconfig archive: doens't exist.")

if __name__ == "__main__":
	# execute parser to allow easy commandline execution
	parser = argparse.ArgumentParser()
	parser.add_argument('xapk', metavar='PATH', type=str, nargs='?', help="Path to the XAPK archive. Required if --extract is True.")
	parser.add_argument('-c', '--client', type=str, help="The client to apply the action to. If not given, an attempt to extract it from xapk archive.")
	parser.add_argument('--clear', type=bool, default=True, action=argparse.BooleanOptionalAction, help="Sets the auto-deletion of all existing assets.")
	parser.add_argument('--extract', type=bool, default=True, action=argparse.BooleanOptionalAction, help="Sets whether files should be extracted.")
	parser.add_argument('--rename', type=bool, default=True, action=argparse.BooleanOptionalAction, help="Sets whether all files should be rename.")
	parser.add_argument('--tidy', type=bool, default=True, action=argparse.BooleanOptionalAction, help="Sets whether the remaining files should be cleaned up.")
	parser.add_argument('--gameconfig', type=bool, default=True, action=argparse.BooleanOptionalAction, help="Sets whether the gameconfig database should be extracted.")
	parser.add_argument('--decompile', type=bool, default=True, action=argparse.BooleanOptionalAction, help="Sets whether the lua files should get decompiled.")
	args = parser.parse_args()

	# make sure additional argument requirements are fullfilled
	if args.extract and not args.xapk:
		print("If extract is enabled, a path to an xapk archive is needed.")
		exit(1)

	if not args.rename and args.tidy:
		print("Cannot tidy up files if renaming is disabled.")
		exit(1)
	
	# determine which client to use
	if args.client:
		CLIENT = Client[args.client]
	elif args.xapk:
		with ZipFile(Path(args.xapk), 'r') as xapk_archive:
			with xapk_archive.open('manifest.json', 'r') as manifestfile:
				manifest = json.loads(manifestfile.read().decode('utf8'))
		CLIENT = Client.from_package_name(manifest['package_name'])
	else:
		print("No Client was given and it could not be found in the XAPK archive.")
		exit(1)

	# load config file and variables
	config = util.JsonConfig('config.json')
	RENAME_TARGET_PATH = Path(config['AssetDir'].format(client = CLIENT.locale_code))
	UNPACK_PATH = Path(RENAME_TARGET_PATH, config['UnpackTempDir'])
	LEFT_FILES_PATH = Path(RENAME_TARGET_PATH, config['AssetRemainDir'])
	LUA_DIR = Path(RENAME_TARGET_PATH, 'script')
	JSON_DIR = Path(RENAME_TARGET_PATH, config['GameConfigJsonDir'])

	# check execution flags and execute
	if args.clear:
		execute_clear(UNPACK_PATH, RENAME_TARGET_PATH, LEFT_FILES_PATH)

	if args.extract:
		execute_extraction(Path(args.xapk), UNPACK_PATH)

	if args.rename:
		execute_rename(UNPACK_PATH, RENAME_TARGET_PATH)

	if args.tidy:
		execute_tidy(UNPACK_PATH, LEFT_FILES_PATH)

	if args.gameconfig:
		execute_gc_extract(RENAME_TARGET_PATH, JSON_DIR)

	if args.decompile:
		decompile.recursive_decompile_dir(LUA_DIR)
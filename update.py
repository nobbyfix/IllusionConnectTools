import argparse
import json
import logging
from pathlib import Path
from zipfile import ZipFile

import requests
from git import Repo

from lib import Client, xxtea, gameconfig, decompile
from lib.util import log_error_exit, get_or_exit, mkdirs, JsonConfig


class CdnDownloader():
	def __init__(self, cndurl, cndurl_fallback):
		self.cdn = cndurl.rstrip("/")
		self.fallback = cndurl_fallback.rstrip("/")

	@staticmethod
	def _download(cdn, fileurl):
		full_url = cdn.rstrip("/") + "/" + fileurl.lstrip("/")
		result = requests.get(full_url)
		return result

	def download(self, fileurl: str):
		result = self._download(self.cdn, fileurl)
		return result.content


def version_check(vms_url: str, current_version: int, useragent: str, device_id: str):
	logging.debug("Sending version check...")
	logging.debug(f"Target URL: {vms_url}.")
	logging.debug(f"Useragent: {useragent}.")
	logging.debug(f"DeviceID: {device_id}.")
	response = requests.post(
		url = vms_url,
		headers = {
			"Accept-Encoding": "identity",
			"Content-Type": "application/x-www-form-urlencoded",
			"User-Agent": useragent,
		},
		params = {
			"opCode": "100101",
			"params": str(
				{
					"pass": device_id,
					"channel": "",
					"version": current_version,
					"did": device_id
			})
	})
	logging.debug("Finished sending version check.")
	return response.json()

def extrack_update_pack(update_packs: list[Path], target_parentdir: Path):
	update_files_changes = {}
	for update_archive_path in update_packs:
		with ZipFile(update_archive_path, 'r') as update_archive:
			# open update info file and read content
			with update_archive.open('update', 'r') as update_info:
				update_data = update_info.read().decode('utf8')

			# split update info by lines and read version number from first line
			update_data_lines = update_data.splitlines(False)
			version_target = update_data_lines[0].replace("version:", "")

			# iterate over info lines starting at the second (where the info starts)
			for assetdata in update_data_lines[2:]:
				assetpath, dbpath, _, _ = json.loads(assetdata)
				assettargetpath = Path(target_parentdir, assetpath)
				if dbpath == "":
					# delete the file if it is marked so
					if assettargetpath.exists():
						update_files_changes[assetpath] = "D"
						assettargetpath.unlink()
				else:
					if dbpath not in update_archive.NameToInfo: continue
					with update_archive.open(dbpath, 'r') as assetfile:
						# mark how the file changed
						if assettargetpath.exists():
							update_files_changes[assetpath] = "C"
						else:
							mkdirs(assettargetpath)
							update_files_changes[assetpath] = "N"

						# decrypt and save data to target file
						decryted_bytes = xxtea.decrypt(assetfile.read())
						with open(assettargetpath, 'wb') as targetfile:
							targetfile.write(decryted_bytes)

		update_archive_path.unlink()

	return int(version_target), update_files_changes


def main(client: Client):
	logging.info(f"Starting version check for {client.name}.")

	# load config file and variables
	logging.debug("Loading updater config.")
	config = JsonConfig('config.json')
	ASSET_DIR = Path(config['AssetDir'].format(client = client.locale_code))
	LUA_DIR = Path(ASSET_DIR, 'script')
	UPDATE_TEMP_DIR = Path(ASSET_DIR, config['UpdateTempDir'])
	UPDATE_TEMP_DIR.mkdir(exist_ok=True, parents=True)
	GAMECONFIG_DIR = Path(ASSET_DIR, config['GameConfigJsonDir'])
	GAME_CONFIG_PATH = Path(ASSET_DIR, "cocos_app.conf")

	# load app config
	logging.debug("Loading app config.")
	cocos_config = JsonConfig(GAME_CONFIG_PATH)
	VMS_URL = cocos_config['captainUrl']
	if "updJobId" in cocos_config:
		GAME_VERSION = cocos_config['updJobId']
	else:
		GAME_VERSION = cocos_config['packJobId']
	if "patchJobId" in cocos_config:
		PATCH_VERSION = cocos_config['patchJobId']
	else:
		PATCH_VERSION = GAME_VERSION
	logging.info(f"Client Version - Game: {GAME_VERSION}, Patch: {PATCH_VERSION}.")

	# send version check to server
	DEVICE_ID = config['DeviceID']
	USERAGENT = config['UserAgent']
	response = version_check(VMS_URL, GAME_VERSION, USERAGENT, DEVICE_ID)
	if response['status'] == 10001:
		log_error_exit(f"Wrong Version Information: Version {GAME_VERSION} does not exist.")
	elif response['status'] != 0:
		log_error_exit("Unknown error occured during version check.", response)

	# assert valid version data has been received and retrieve data from response
	httpData = get_or_exit(response, 'data', "Invalid response: No httpdata content.")
	data = get_or_exit(httpData, 'data', "Invalid response: No data content.")
	retval = get_or_exit(httpData, 'ret', "Invalid response: No ret cotent.")
	latest_version = get_or_exit(data, 'targetV', "Invalid response: No targetV.")
	cdn_url = get_or_exit(data, 'cdnUrl', "Invalid response: No CdnUrl.", level=logging.WARN)
	cdn_url2 = get_or_exit(data, 'extraCdnUrl', "Invalid response: No ExtraCdnUrl.", level=logging.WARN)
	if not (cdn_url or cdn_url2):
		log_error_exit("Did not receive any CdnUrl.")
	logging.info(f"Server Version - Game: {latest_version}.")

	# setup downloader and repository
	downloader = CdnDownloader(cdn_url, cdn_url2)
	update_repository = Repo(str(Path(config["AssetRepo"])))

	# define updater function
	def apply_update(game_ver_target, patch_ver_target, file_changes):
		actual_version = max(game_ver_target, patch_ver_target)

		# save updated file changes
		filechange_fp = Path(ASSET_DIR, "_update", str(actual_version)+".json")
		mkdirs(filechange_fp)
		with open(filechange_fp, 'w', encoding='utf8') as f:
			json.dump(file_changes, f, indent=4)

		# decrypt, apply and convert gameconfig database
		db_upd_path = Path(ASSET_DIR, "gameUpdateConfig.db")
		if db_upd_path.exists():
			db_path = Path(ASSET_DIR, "gameConfig.db")
			gameconfig.decrypt_db(db_upd_path)
			gameconfig.merge_db(db_path, db_upd_path)
			gameconfig.convert_db(db_path, GAMECONFIG_DIR)

		# decompile lua files
		decompile.recursive_decompile_dir(LUA_DIR)

		# save version number
		cocos_config['updJobId'] = int(game_ver_target)
		cocos_config['patchJobId'] = int(patch_ver_target)
		cocos_config.save()

		# commit to the repository
		update_repository.git.add(client.locale_code) # adds only all files inside the current clients directory
		update_repository.git.commit('-m', f'[{client.locale_code}] GAME: {actual_version}')
		update_repository.remotes.origin.push()

	def execute_update():
		# pylint: disable=used-before-assignment
		if int(latest_version) <= GAME_VERSION:
			logging.info("Client is on newest version.")
		else:
			for pack_upd in data['pack'].values():
				update_zips = []
				for file in pack_upd['64']:
					content = downloader.download(file['url'])
					targetfile = Path(UPDATE_TEMP_DIR, Path(file['url']).name)
					with open(targetfile, 'wb') as f:
						f.write(content)
					update_zips.append(targetfile)
				updated_version, file_changes = extrack_update_pack(update_zips, ASSET_DIR)
				apply_update(updated_version, updated_version, file_changes)

	def execute_patch():
		patch_version = int(data['patchInfo']['patchVersion'])
		logging.info(f"Server Version - Patch: {patch_version}.")
		if patch_version <= PATCH_VERSION:
			logging.info("Client is on newest patch.")
		else:
			patch = data['patchInfo']['patch']['64']
			logging.info(f"New Patch Available with {len(patch)} files.")
			changed_files = {}
			for patchedfile in patch:
				content = downloader.download(patchedfile['url'])
				logictargetpath = patchedfile['logic']
				targetpath = Path(ASSET_DIR, logictargetpath)
				if targetpath.exists(): changed_files[logictargetpath] = "C"
				else:
					changed_files[logictargetpath] = "N"
					mkdirs(targetpath)
				with open(targetpath, 'wb') as f:
					decrypted_data = xxtea.decrypt(content)
					f.write(decrypted_data)
			apply_update(GAME_VERSION, patch_version, changed_files)

	if retval == 0:
		logging.debug("Starting patch routine.")
		execute_patch()
	elif retval == 1:
		logging.debug("Starting update and patch routines.")
		execute_update()
		#execute_patch()
		main(client)
	elif retval == 2:
		logging.warning("The server is currently in maintanance mode.")
		notice = get_or_exit(data, 'notice', "Invalid response: No notice.")
		notice_en = get_or_exit(notice, 'en', "Invalid response: No default english notice.")
		logging.debug(notice_en)
	elif retval == 3:
		logging.warning("Need to force update apk.")
	else:
		logging.warning("There is no update / Unknown return code.")


if __name__ == "__main__":
	# set up logger to file
	logging.basicConfig(level=logging.DEBUG, format="[%(asctime)s] [%(levelname)s]: %(message)s", datefmt="%x %X", filename="update_dbg.log")
	# set up logging to error file
	errorfile = logging.FileHandler('update_error.log')
	errorfile.setLevel(logging.ERROR)
	errorfile.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s]: %(message)s", datefmt="%x %X"))
	logging.getLogger("").addHandler(errorfile)
	# set up logging to console
	console = logging.StreamHandler()
	console.setLevel(logging.INFO)
	console.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s]: %(message)s", datefmt="%x %X"))
	logging.getLogger("").addHandler(console)
	logging.debug("##############################")

	# execute parser to allow easy commandline execution
	parser = argparse.ArgumentParser()
	parser.add_argument('-c', '--client', required=True, type=str, help="The client to apply the action to.")
	args = parser.parse_args()

	# execute main with given client
	main(Client[args.client])
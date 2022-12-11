import sys
import json
import logging
from pathlib import Path
from dataclasses import dataclass
from typing import Any

from lib import Client


class LoggingDict(dict):
	def get_with_error(self, key: str, error_msg: str, logging_level: int = logging.ERROR, do_exit: bool = True) -> Any:
		"""
		Tries to get a value of key from the dict.  
		Should that fail, an error message is logged and the program may be exited.

		key: the key to load a value from the dict
		error_msg: error message to be printed if the value is not found
		logging_level: logging level of the logging module
		exit: whether the program should exit if the value is not found
		"""
		value = self.get(key)
		if value:
			return value

		# since value was not found, log error message and exit program if exit is True
		logging.log(logging_level, error_msg)
		if do_exit:
			sys.exit()


@dataclass
class Config:
	AssetrepoPath: Path
	DeviceID: str
	UserAgent: str
	UnpackSubpath: Path = Path("_unpack")
	RemainSubpath: Path = Path("_remain")
	UpdateSubpath: Path = Path("_update")

	def ClientPath(self, client: Client) -> Path:
		return Path(self.AssetrepoPath, client.locale_code)

	def UnpackPath(self, client: Client) -> Path:
		return Path(self.ClientPath(client), self.UnpackSubpath)

	def RemainPath(self, client: Client) -> Path:
		return Path(self.ClientPath(client), self.RemainSubpath)

	def UpdatePath(self, client: Client) -> Path:
		return Path(self.ClientPath(client), self.UpdateSubpath)



def save_config(configdata: dict, fp: Path = Path("config.json")) -> None:
	with open(fp, 'w', encoding="utf8") as f:
		json.dump(configdata, f)

def create_config(fp: Path = Path("config.json"), ignore_user_promts: bool = False, force: bool = False) -> bool:
	"""
	Create the config file for use in all scripts.

	fp: The filepath to create the config file at.  
	ignore_user_promts: Does not prompt the user to enter certain fields.

	Returns False if the file already exists, otherwise True.
	"""
	if not force:
		if fp.exists():
			logging.warning(f"Tried to create config at {fp}, but it already exists.")
			return False

	configdata = {
		"AssetRepoPath": "",
		"DeviceID": "",
		"UserAgent": "",
		"UnpackPath": "_unpack",
		"RemainPath": "_remain",
		"UpdatePath": "_update",
	}

	if ignore_user_promts:
		logging.warning("""User promts during config creation have been ignored.
			They still need to be filled out at a later point to make all scripts work.""")
	else:
		configdata["AssetRepoPath"] = input("Asset Repository Location: ")
		configdata["DeviceID"] = input("DeviceID: ")
		configdata["UserAgent"] = input("UserAgent: ")

	save_config(configdata, fp)
	return True


def load_config(fp: Path = Path("config.json")) -> Config:
	# create new config if it does not exist
	if not fp.exists():
		create_config(fp)

	# load json config
	try:
		with open(fp, 'r', encoding='utf8') as f:
			configdata = json.load(f)
	except json.JSONDecodeError:
		logging.error("Config file contains invalid json.")
		answer = input("Config file is invalid, recreate it? (y/n) ")
		if answer.lower() in ("yes", "y"):
			create_config(fp, force=True)
			return load_config(fp)

		# exit program, can not continue with invalid config file
		logging.debug("Config file will not be recreated, exiting program.")
		sys.exit()

	# if these fields are not defined, the program can not continue
	assetrepo = get_or_prompt(configdata, "AssetRepoPath", "Asset Repository Location: ")
	deviceid = get_or_prompt(configdata, "DeviceID", "DeviceID: ")
	useragent = get_or_prompt(configdata, "UserAgent", "UserAgent: ")

	# create the args dict and add optional fields
	args = { "assetrepo": assetrepo, "deviceid": deviceid, "useragent": useragent }
	for argkey, confkey in (("unpack","UnpackPath"),("remain","RemainPath"),("update","UpdatePath")):
		if value := configdata.get(confkey):
			args[argkey] = value

	return Config(**args)
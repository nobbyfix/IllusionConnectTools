import os
import json
import logging
from pathlib import Path


class JsonConfig(dict):
	def __init__(self, filepath: os.PathLike):
		self.path = Path(filepath)
		self.load()

	def load(self):
		if self.path.exists():
			with open(self.path, 'r', encoding='utf8') as f:
				json_dict = json.load(f)
		else: json_dict = {}
		super().__init__(json_dict)

	def save(self, *json_dump_args):
		with open(self.path, 'w', encoding='utf8') as f:
			json.dump(self, f, *json_dump_args)


# useful file path operations
def mkdir(dirpath: Path):
	if not dirpath.exists():
		dirpath.mkdir(parents=True)
def mkdirs(filepath: Path):
	mkdir(filepath.parent)


# stolen from https://stackoverflow.com/questions/3173320/text-progress-bar-in-the-console
def printProgressBar(iteration, total, prefix = '', suffix = 'Complete', decimals = 1, length = 50, fill = '█', printEnd = "\r"):
	"""
	Call in a loop to create terminal progress bar
	@params:
		iteration	- Required  : current iteration (Int)
		total		- Required  : total iterations (Int)
		prefix		- Optional  : prefix string (Str)
		suffix		- Optional  : suffix string (Str)
		decimals	- Optional  : positive number of decimals in percent complete (Int)
		length		- Optional  : character length of bar (Int)
		fill		- Optional  : bar fill character (Str)
		printEnd	- Optional  : end character (e.g. "\r", "\r\n") (Str)
	"""
	percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
	filledLength = int(length * iteration // total)
	progress = fill * filledLength + '-' * (length - filledLength)
	print(f'\r{prefix} |{progress}| {percent}% {suffix}', end = printEnd)
	# Print New Line on Complete
	if iteration == total:
		print()

# simplified progress bar class with only the useful stuff i use
class ProgressBar():
	def __init__(self, total: int, prefix: str, suffix: str = 'Complete', iterstart: int = 0):
		self.total = total
		self.prefix = prefix
		self.suffix = suffix
		printProgressBar(iterstart, total, prefix, suffix)

	def update(self, iteration):
		printProgressBar(iteration, self.total, self.prefix, self.suffix)

# collects error messages and outputs them to console or a file depending on the amount
class ErrorLogger():
	def __init__(self, logfile: Path, max_msg: int = 10):
		self.logfilepath = logfile
		self.max_msg = max_msg
		self.messages = []

	def add_message(self, msg: str):
		self.messages.append(msg)

	def output(self):
		if len(self.messages) > self.max_msg:
			with open(self.logfilepath, 'w', encoding='utf8') as f:
				for msg in self.messages:
					f.write(msg+"\n")
		else:
			for msg in self.messages:
				print(msg)


# error logging utility
def log_error_exit(error_msg: str, debug_output = None):
	logging.error(error_msg)
	if debug_output: logging.debug(debug_output)
	exit(1)
def get_or_exit(datadict: dict, key, error_msg = '', level = logging.ERROR):
	if key in datadict:
		return datadict[key]
	else:
		if level == logging.ERROR:
			log_error_exit(error_msg, datadict)
		else:
			logging.log(level, error_msg)
			logging.debug(datadict)

def get_or_prompt(datadict: dict, key: str, prompt_msg: str):
	if key in datadict:
		return datadict[key]
	# datadict does not contain key, prompt for user input
	return input(prompt_msg)
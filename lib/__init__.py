from enum import Enum
from typing import Optional


class AbstractClient(Enum):
	active: bool
	locale_code: str
	package_name: str

	def __new__(cls, value, active, locale, package_name):
		# this should be done differently, but i am too lazy to do that now
		# TODO: change it
		if not hasattr(cls, "package_names"):
			cls.package_names = {}

		obj = object.__new__(cls)
		obj._value_ = value
		obj.active = active
		obj.locale_code = locale
		obj.package_name = package_name
		cls.package_names[package_name] = obj
		return obj

	@classmethod
	def from_package_name(cls, package_name) -> Optional['AbstractClient']:
		return cls.package_names.get(package_name)


class Client(AbstractClient):
	EN = (1, True, 'en-US', 'com.superprism.illusion')
	KR = (2, True, 'ko-KR', 'com.cyou.illusionc.gp')
	TW_OLD = (3, False, 'zh-TW', 'com.mamba.dreamlandrecon') # discontinued
	JP = (4, True, 'ja-JP', 'com.efun.mjlj')
	TW = (5, True, 'zh-TW', 'com.mover.twmjljr')
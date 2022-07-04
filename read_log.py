import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class KO_LogEntry:
	def __init__(self, raw_entry: str) -> None:
		self.timestamp = None
		self.entry_kind = None
		self.user_login = None
		self.user_nickname = None
		self.message = None
		self.valid = self._parse_raw_entry(raw_entry)

	def _parse_raw_entry(self, line: str) -> bool:
		# Test for brackets around log timestamp
		if line[0] != '[' or line[20] != ']':
			logger.error(f"Unexpected formatted line: {line.strip()}")
			return False
		year = int(line[1:5])
		month = int(line[6:8])
		day = int(line[9:11])
		hour = int(line[12:14])
		minute = int(line[15:17])
		second = int(line[18:20])
		self.timestamp = datetime(year=year, month=month, day=day, hour=hour, minute=minute, second=second)
		# check for brackets around message kind. Some messages like
		# 'Loading Map' and 'Server Start/Stop' dont have these but who the
		# heck cares about that stuff
		if line[22] == '<':
			kind_end_index = line.index('>', 22)
			self.entry_kind = line[23:kind_end_index]
			# Check for brackets around username
			message_start_index = kind_end_index+2
			if line[message_start_index] != '[':
				logger.error(f"Unexpected formatted line: {line.strip()}")
				return False
			user_end_index = line.index(']', message_start_index)
			self.message = line[user_end_index+1:].strip()
			user_login_end_index = line.index(' (', message_start_index+2)
			self.user_login = line[message_start_index+1:user_login_end_index]
			self.user_nickname = line[user_login_end_index+2:user_end_index-1]
			return True
		return False


if __name__ == '__main__':
	logging.basicConfig(level=logging.DEBUG, format='%(asctime)s.%(msecs)03d %(levelname)s {%(module)s} [%(funcName)s] %(message)s')

	with open('.\\data\\TM2_knock_out_login_-2013-07-04_to_2014-05-24\\GameLog.knock_out.txt', 'r', encoding='utf-8') as gamelogfile:
		linenum = 0
		for line in gamelogfile.readlines():
			linenum += 1

			result = KO_LogEntry(line)
			if result.valid:
				logger.info(result.user_login + ' ' + result.user_nickname)

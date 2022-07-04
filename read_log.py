import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class KO_User:
	def __init__(self, login: str, nickname: str) -> None:
		self.login = login
		self.nickname = nickname
	
	def __repr__(self) -> str:
		return str(self.login) + ", " + str(self.nickname)


class KO_UserResult:
	def __init__(self, user: KO_User, time: datetime, ko_reason: str) -> None:
		self.user = user
		self.ko_time = time
		self.ko_reason = ko_reason


class KO_UserLookup:
	def __init__(self) -> None:
		self.users = {}	# type: dict[str, list[str]]

	def add_user(self, user: KO_User) -> None:
		login = user.login.strip()
		nickname = user.nickname.strip()
		if login not in self.users:
			self.users[login] = []
		if nickname not in self.users[login]:
			self.users[login].append(nickname)

	def get_login(self, nickname: str) -> str:
		for login, nicknames in self.users.items():
			if nickname.strip() in nicknames:
				return login
		else:
			logger.error(f"Login not found for nickname: {nickname}")
			return None


class KO_LogEntry:
	parsing_errors = []

	def __init__(self, raw_entry: str) -> None:
		self.timestamp = None
		self.entry_kind = None
		self.user = None
		self.message = None
		self.valid = False
		try:
			self.valid = self._parse_raw_entry(raw_entry)
		except:
			self.parsing_errors.append(raw_entry)

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
			user_end_index = line.index(')]', message_start_index) + 1
			self.message = line[user_end_index+1:].strip()
			user_login_end_index = line.index(' (', message_start_index+2)
			self.user = KO_User(line[message_start_index+1:user_login_end_index], line[user_login_end_index+2:user_end_index-1])
			return True
		return False


class KO_Instance:
	def __init__(self) -> None:
		self.start_time = None	# type: datetime
		self.end_time = None	# type: datetime
		self.host = None	# type: str
		self.results = []	# type: list[KO_UserResult]

	def add_result(self, player_result: KO_UserResult) -> None:
		self.results.append(player_result)


def read_ko_logfile(filepath: str, server_login: str, kos: 'list[KO_Instance]', user_lookup: KO_UserLookup) -> None:
	logger.info("Opening " + filepath)
	with open(filepath, 'r', encoding='utf-8') as gamelogfile:
		linenum = 0
		new_instance = None
		for line in gamelogfile.readlines():
			linenum += 1

			entry = KO_LogEntry(line)
			if entry.valid:
				user_lookup.add_user(entry.user)

				if entry.user.login != server_login and ('/ko start' in entry.message or '/kostart' in entry.message):
					new_instance = KO_Instance()
					new_instance.host = entry.user
					new_instance.start_time = entry.timestamp
				elif new_instance:

					if entry.user.login == server_login and ('has been KO for ' in entry.message or ' is KO ' in entry.message):
						result_nickname = ''
						result_login = ''
						result_reason_raw = ''
						if entry.message.startswith('>> '):
							result_nickname = entry.message[3:entry.message.index(' is KO ')]
							result_login = user_lookup.get_login(result_nickname)
							has_been_ko_index = entry.message.index(' is KO ', 3)
							result_reason_raw = entry.message[has_been_ko_index+7:]
						else:
							server_header_len = 0
							if entry.message.startswith('Server〉'):
								server_header_len = len('Server〉')
							elif entry.message.startswith('Server 〉'):
								server_header_len = len('Server 〉')
							if server_header_len == 0:
								logger.info(f"New type of KO message: {entry.message}")
							has_been_ko_index = entry.message.index('has been KO for ', server_header_len)
							result_nickname = entry.message[server_header_len:has_been_ko_index-1]
							result_login = user_lookup.get_login(result_nickname)
							result_reason_raw = entry.message[has_been_ko_index+16:]

						if 'DNF' in result_reason_raw:
							result_reason = 'DNF'
						elif 'Worst place finish':
							result_reason = 'WPF'
						else:
							logger.error(f"Unknown result reason for {entry.message}")
							result_reason = 'Unknown'
						new_instance.add_result(KO_UserResult(KO_User(result_login, result_nickname), entry.timestamp, result_reason))

					elif entry.user.login == server_login and ('The KnockOut Champ is ' in entry.message or 'KnockOut has ended! ' in entry.message):
						champ_nickname = ''
						champ_login = ''
						if entry.message.startswith('>> '):
							champ_nickname = entry.message[23:entry.message.index(' is the Champ!')]
							champ_login = user_lookup.get_login(champ_nickname)
						else:
							server_header_len = 0
							if entry.message.startswith('Server〉'):
								server_header_len = len('Server〉')
							elif entry.message.startswith('Server 〉'):
								server_header_len = len('Server 〉')
							if server_header_len == 0:
								logger.info(f"New type of KO message: {entry.message}")
							champ_nickname = entry.message[server_header_len + 22:]
							champ_login = user_lookup.get_login(champ_nickname)

						new_instance.add_result(KO_UserResult(KO_User(champ_login, champ_nickname), entry.timestamp, 'CHAMP'))
						new_instance.end_time = entry.timestamp
						kos.append(new_instance)
						new_instance = None


if __name__ == '__main__':
	logging.basicConfig(level=logging.DEBUG, format='%(asctime)s.%(msecs)03d %(levelname)s {%(module)s} [%(funcName)s] %(message)s')

	user_lookup = KO_UserLookup()
	kos = []	# type: list[KO_Instance]

	read_ko_logfile('.\\data\\TM2_knock_out_login_-2013-07-04_to_2014-05-24\\GameLog.knock_out.txt', 'knock_out', kos, user_lookup)
	#read_ko_logfile('.\\data\\TM2_mx_knockout_login_-2011-11-03_to_2017-05-28\\GameLog.mx_knockout.txt', 'mx_knockout', kos, user_lookup)
	kos = sorted(kos, key=lambda x: x.start_time)

	logger.info("Writing kos.txt")
	with open('kos.txt', 'w', encoding='utf-8') as kos_file:
		for ko in kos:
			kos_file.write("KO Started: " + ko.start_time.strftime("%c") + "\n")
			kos_file.write("Host: " + str(ko.host) + "\n")
			kos_file.write("Length: " + str(ko.end_time - ko.start_time) + "\n")
			kos_file.write(str(len(ko.results)) + " Player(s):\n")
			for player in ko.results[::-1]:
				kos_file.write("\t" + str(player.ko_reason) + "\t\t" + str(player.user) + "\n")
			kos_file.write("\n")

	logger.info("Writing user_list.txt")
	with open('user_list.txt', 'w', encoding='utf-8') as user_list_file:
		for login, nicknames in user_lookup.users.items():
			user_list_file.write(login + ": " + ', '.join(nicknames) + '\n')


	# Load MatchSettings Success

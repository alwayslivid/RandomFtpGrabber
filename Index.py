
import Persistence
import FileSysIntf
from Threading import SyncedOnObj
import random
import Logging

# Interface for RandomFileQueue
class Filesystem:
	def listDir(self, path):
		return path.listDir()

	def isFile(self, path):
		return isinstance(path, File)

	def isDir(self, path):
		return isinstance(path, Dir)

	def handleException(self, exctype, value, traceback):
		Logging.logException("Filesystem", exctype, value, traceback)

	TemporaryException = FileSysIntf.TemporaryException

class FileBase:
	def __init__(self, url):
		self.url = url

	def __str__(self):
		return self.url

class File(FileBase):
	def __repr__(self):
		return "File(%r)" % self.url

class Dir(FileBase):
	def __init__(self, url, childs=None):
		super().__init__(url)
		self.childs = childs
		self.lastException = None

	@SyncedOnObj
	def listDir(self):
		if self.childs is not None:
			return self.childs

		Logging.log("listDir: %s" % self.url)

		try:
			dirs, files = FileSysIntf.listDir(self.url)
		except FileSysIntf.TemporaryException as e:
			Logging.log("ListDir temporary exception on %s:" % self.url, str(e) or type(e))
			# Reraise so that the outer caller gets noticed that it can retry later.
			raise
		except Exception as e:
			Logging.log("ListDir unrecoverable exception on %s:" % self.url, str(e) or type(e))
			self.lastException = e
			self.childs = []
			return []

		self.childs = \
			list(map(Dir, dirs)) + \
			list(map(File, files))
		index.save()

		# By raising TemporaryException here, it will have the effect that we will try again later.
		raise FileSysIntf.TemporaryException("queried one list-dir, do more next round")

	def __str__(self):
		return self.url

	def __repr__(self):
		return "Dir(%r, %s)" % (self.url, Persistence.betterRepr(self.childs))

class Index:
	def __init__(self, sources=None):
		"""
		:type sources: dict[str,Dir]
		"""
		self.sources = sources or {}
		self._loadSources()
		import main
		main.reloadHandlers += [self._loadSources]

	def _loadSources(self):
		import main
		for source in main.Sources:
			if source not in self.sources:
				self.sources[source] = Dir(url=source)
		for source in self.sources:
			if source not in main.Sources:
				del self.sources[source]

	def getRandomSource(self):
		"""
		:rtype: Dir
		"""
		return random.choice(list(self.sources.values()))

	def getSource(self, source):
		return self.sources[source]

	def __repr__(self):
		return "Index(%s)" % Persistence.betterRepr(self.sources)

filesystem = Filesystem()

index = Persistence.load("index.db", Index)

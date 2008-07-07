"Automatically remove the unwanted garbage from the 'austausch-ordner'."
import os, commands, datetime, logging, shutil, stat

class Prune(object):
    BASE_PATH = "/home/archiv/austausch-ordner"
    CONF_PATH = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                             "conf")
    LOG_NAME = "prune.log"
    GARBAGE_PATH = os.path.join(BASE_PATH, "misc")
    
    counter = {}
    cache = {}
    
    def __init__(self):
        logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s *%(levelname)s* %(message)s',
                    filename=os.path.join(self.BASE_PATH, self.LOG_NAME),
                    filemode='a')
    
    def start(self):
        # Deleting empty dirs
        self._prune_dirs(4)
        self._prune_orphans()
        self._prune_garbage(14)
        logging.info(self._get_stats())
        
    def _get_exceptions(self, etype):
        if etype == 'base_files':
            if not 'base_files' in self.cache:
                res = list()
                fp = open(os.path.join(self.CONF_PATH,
                          "basefiles_exceptions.txt"), 'r')
                for line in fp:
                    res.append(line.strip())
                self.cache['base_files'] = res
            return self.cache['base_files']
    
    def _chdir(self, subdir=''):
        os.chdir(os.path.join(self.BASE_PATH, subdir))
        
    def _inc_counter(self, key):
        try:
            self.counter[key] += 1
        except KeyError:
            self.counter[key] = 1
        
    def _get_stats(self):
        ret = "I deleted a total of %r directories and moved %r orphans. " % \
              (self.counter.get('dirs_deleted', "zarro"),
               self.counter.get('orphans_moved', "not a single"))
        ret += "I also did stuff to the garbage folder and killed %r files " \
               "and %r directories." % \
               (self.counter.get('garbage_files_deleted', "no"),
                self.counter.get('garbage_dirs_deleted', "not even a half"))
        return ret
    
    def _prune_dirs(self, size=4):
        "Deletes all directory in the base dir smaller than 'size'"
        logging.debug("Starting _prune_dirs with size limit %d" % size)
        self._chdir()
        cmd = "du -s * | sort -n"
        out = commands.getoutput(cmd)
        for line in out.split("\n"):
            parts = line.split()
            try:
                dir_size = int(parts[0])
            except ValueError:
                continue
            if dir_size <= size:
                dirname = " ".join(parts[1:])
                dir_type = os.stat(dirname)[stat.ST_MODE]
                if stat.S_ISDIR(dir_type):
                    logging.info("Deleting dir '%s', because its size is lower "\
                                 "than %d kbytes." % (dirname, size))
                    shutil.rmtree(dirname, True)
                    self._inc_counter('dirs_deleted')
                else:
                    logging.debug("Ignoring file '%s', because it seems not "\
                                  "to be a directory, however it's smaller "\
                                  "than %d kbytes." % (dirname, size))
                    
    def _prune_orphans(self, subdir = ''):
        self._chdir(subdir)
        exceptions = self._get_exceptions('base_files')
        logging.debug("Starting _prune_orphans in subdir '%s'" % (subdir or "/"))
        for filename in os.listdir('.'):
            if os.path.isfile(filename) and filename not in exceptions:
                logging.info("Moving file '%s' to '%s', because it does not " \
                             "not belong into the root folder!" % \
                             (filename, self.GARBAGE_PATH))
                shutil.move(filename, self.GARBAGE_PATH)
                self._inc_counter('orphans_moved')
                
    def _prune_garbage(self, days):
        "Throws away the garbage older than 'days'"
        logging.debug("Starting _prune_garbage with days = %d" % days)
        os.chdir(self.GARBAGE_PATH)
        for root, dirs, files in os.walk(self.GARBAGE_PATH, False):
            for _filename in files:
                filename = os.path.join(self.GARBAGE_PATH, root, _filename)
                lasta = datetime.datetime.fromtimestamp(
                                                    os.path.getatime(filename))
                diff = datetime.datetime.now()-lasta
                if diff.days >= days:
                    logging.info("Deleting file '%s' in garbage folder, " \
                                 "because it has not been accessed for more " \
                                 "than %d days." % (filename, diff.days))
                    os.unlink(filename)
                    self._inc_counter('garbage_files_deleted')
            for _dirname in dirs:
                dirname = os.path.join(self.GARBAGE_PATH, root, _dirname)
                lasta = datetime.datetime.fromtimestamp(
                                                    os.path.getatime(dirname))
                diff = datetime.datetime.now()-lasta
                if diff.days >= days:
                    logging.debug("Trying to delete folder '%s' in garbage " \
                                  "folder, as it's been too long untouched.")
                    try:
                        os.rmdir(dirname)
                        logging.info("Deleted folder '%s' in garbage folder.")
                        self._inc_counter('garbage_dirs_deleted')
                    except OSError, ex:
                        if ex.errno == 39:
                            logging.debug("Skipping dir, because it's not empty.")
                
if __name__ == "__main__":
    probj = Prune()
    probj.start()
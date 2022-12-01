from abc import abstractmethod

class Plugin(object):
    def __init__(self, infos):
        self.infos = infos

    @abstractmethod
    def load(self):
        """Code to execute on every plugin import
        """
        return

    @abstractmethod
    def close(self):
        """Code to execute when activity browser get closed
        """
        return

    @abstractmethod
    def remove(self):
        """Code to execute when plugin is removed from project
        """
        return

    @abstractmethod
    def delete(self):
        """Code to execute on plugin deletion
        """
        return
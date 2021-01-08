import abc


class AbstractManager(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractproperty
    def data_type(self):
        pass

    @abc.abstractproperty
    def extension(self):
        pass

    @abc.abstractproperty
    def base_file_name(self):
        pass

    @abc.abstractproperty
    def new_versioned_file(self):
        pass

    @abc.abstractproperty
    def latest_versioned_file(self):
        pass

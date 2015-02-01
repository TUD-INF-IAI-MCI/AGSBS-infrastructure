class MAGSBS_error(Exception):
    """Just a parent."""
    pass

class SubprocessError(MAGSBS_error):
    pass

class WrongFileNameError(MAGSBS_error):
    pass

class TOCError(MAGSBS_error):
    pass

class MissingMandatoryField(MAGSBS_error):
    pass

class ConfigurationError(MAGSBS_error):
    pass

class ConfigurationNotFoundError(MAGSBS_error):
    pass

class StructuralError(MAGSBS_error):
    pass


class FileNotFoundError(MAGSBS_error):
    pass

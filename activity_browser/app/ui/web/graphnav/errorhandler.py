# -*- coding: utf-8 -*-

class ErrorHandler:
    """
    ErrorHandler enables meaningful high-level function except messages without losing low-level traceback error or type error

    """
    @staticmethod
    def trace_error(e: Exception): #prints traceback error if exception is raised
        if not (e is None):
            print("Unexpected error:", str(e))
            import traceback
            traceback.print_exc()

        else:
            import sys
            last_error = sys.exc_info()[0]
            print("Unexpected error:", last_error)

            type_error: TypeError = ErrorHandler.safe_cast(last_error, TypeError)
            if not (type_error is None):
                print(type_error.args)

    @staticmethod
    def safe_cast(val, to_type, default=None):
        try:
            return to_type(val)
        except (ValueError, TypeError):
            return default

import sys


class recli:
    def __init__(self) -> None:
        return

    @staticmethod
    def _process_msg(_msg: str) -> str:
        processed_msg: str = ''
        b_count: int = 0
        h_count: int = 0

        for _i in range(len(_msg)):
            _char: str = _msg[_i]

            if _char == '*' and _msg[max(_i - 1, 0)] != '\\':
                processed_msg += '\033[1m' if b_count % 2 == 0 else '\033[0m'
                b_count += 1
            elif _char == '~' and _msg[max(_i - 1, 0)] != '\\':
                processed_msg += '\033[1;36m' if h_count % 2 == 0 else '\033[0m'
                h_count += 1
            elif _char == '\\' and _msg[min(_i + 1, len(_msg) - 1)] in ('*', '~'):
                continue
            else:
                processed_msg += _char

        return processed_msg

    @staticmethod
    def serialize_msg(__msg: str) -> str:
        return __msg.replace('*', '\\*').replace('~', '\\~')

    def info(__msg: any, end: str = '\n', process_msg: bool = True) -> None:
        sys.stdout.write(
            ' :: '
            + (recli._process_msg(str(__msg)) if process_msg else str(__msg))
            + end
        )
        sys.stdout.flush()

    def warn(__msg: any, end: str = '\n', process_msg: bool = True) -> None:
        sys.stderr.write(
            ' :: \033[1;33mwarning\033[0m: '
            + (recli._process_msg(str(__msg)) if process_msg else str(__msg))
            + end
        )
        sys.stderr.flush()

    def error(__msg: any, end: str = '\n', process_msg: bool = True) -> None:
        sys.stderr.write(
            ' :: \033[1;31merror\033[0m: '
            + (recli._process_msg(str(__msg)) if process_msg else str(__msg))
            + end
        )
        sys.stderr.flush()

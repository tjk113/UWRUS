import time
import os

class Log:
    def __init__(self) -> None:
        # Timestamp format: YYYY-MM-DD_HH-MM-SS_TZ (TZ is timezone offset)
        self.__timestamp: str            = time.strftime('%Y-%m-%d_%I-%M-%S-%p_%z', time.localtime(time.time()))
        self.__nothing_to_update: bool   = None
        self.__star_names: list[str]     = []
        self.__update_results: list[str] = []
        self.__error_message: str        = None

    def set_nothing_to_update(self, nothing_to_update: bool) -> None:
        self.__nothing_to_update = nothing_to_update
    
    def add_star_name(self, star_name: str, type: str) -> None:
        self.__star_names.append(f'{star_name} ({type})')

    def add_update_result(self, update_result: str) -> None:
        self.__update_results.append(update_result)

    def add_error_message(self, error_message: str) -> None:
        self.__error_message = error_message

    def out(self):
        if not os.path.exists('.\\logs'):
            os.mkdir('.\\logs')
        with open(f'logs\\{self.__timestamp}.log', 'w+') as file:
            file.write(f'{self.__timestamp}\n')
            if self.__nothing_to_update:
                file.write('Info="No new RTA or SS records to update"')
                return
            if self.__star_names:
                for i, star_name, update_result in enumerate(zip(self.__star_names, self.__update_results)):
                    file.write(f'star_name_{i}={star_name}\nupdate_result_{i}={update_result}\n')
            if self.__error_message:
                file.write(f'Error="{self.__error_message}"')
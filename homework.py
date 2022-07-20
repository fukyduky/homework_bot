import logging
import os
import sys
import time
from typing import Dict, List

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot: telegram.Bot, message: str):
    """Отправляет сообщение в Telegram чат."""
    try:
        logger.info('Начата отправка сообщения')
        sent_message = bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message
        )
    except telegram.error.BadRequest as error:
        raise error
    else:
        logger.info(f'Сообщение отправлено в Telegram: "{message}"')
    return sent_message


def get_api_answer(current_timestamp: int) -> Dict:
    """Делает запрос к эндпоинту API-сервиса."""
    timestamp = current_timestamp
    params = {'from_date': timestamp}

    try:
        logger.info('Начат запрос к API')
        response = requests.get(url=ENDPOINT, params=params, headers=HEADERS)
    except ConnectionError as error:
        raise error

    if response.status_code != requests.codes.ok:
        response.raise_for_status()

    try:
        result = response.json()
    except requests.exceptions.JSONDecodeError as error:
        raise error
    return result


def check_response(response: Dict) -> List:
    """Проверяет ответ API на корректность."""
    if not isinstance(response, dict):
        raise TypeError

    try:
        homeworks = response.get('homeworks')
    except KeyError as error:
        raise error
    except TypeError as error:
        raise error

    if not isinstance(homeworks, list):
        raise TypeError
    return homeworks


def parse_status(homework: Dict[str, str]) -> str:
    """Извлекает из конкретной домашней работе статус этой работы."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')

    if homework_status not in HOMEWORK_STATUSES:
        raise KeyError('Статус домашней работы не соответствует ожидаемому')
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens() -> bool:
    """Проверяет доступность переменных окружения."""
    return all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID))


def main():
    """Основная логика работы бота."""
    logger.debug('Бот запущен')
    if check_tokens() is False:
        logger.critical('Токен не заполнен')
        sys.exit('Работа бота прервана')

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())

    try:
        response = get_api_answer(current_timestamp)
        homeworks: List = check_response(response)
        for homework in homeworks:
            message = parse_status(homework)
            send_message(bot, message)
        current_timestamp = int(response['current_date'])
    except Exception as error:
        error_message = f'Сбой в работе программы: {error}'
        logger.error(error_message)
        send_message(bot, error_message)
    finally:
        time.sleep(RETRY_TIME)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format=(
            '%(asctime)s [%(levelname)s] %(name)s: %(message)s (%(funcName)s)'
        ),
        filename='main.log'
    )
    main()
# https://github.com/python-telegram-bot/python-telegram-bot/tree/master/examples

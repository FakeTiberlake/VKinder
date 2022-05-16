import vk_api
import json
import datetime
from vk_api.longpoll import VkLongPoll, VkEventType
import configparser
from vk_api.exceptions import ApiError
from database import engine, Base, Session, User, DatingUser, Photos, BlackList
from sqlalchemy.exc import IntegrityError, InvalidRequestError

# Прочитаем файл с конфигурациями

config = configparser.ConfigParser()  # создаём объекта парсера
config.read("config.ini")  # читаем конфиг
print(config['VK']['group_token'])
print(config['VK']['user_token'])
print(config['VK']['V'])

# Работа с ВК
vk = vk_api.VkApi(token=group_token)
longpoll = VkLongPoll(vk)
# Работа с БД
session = Session()
connection = engine.connect()


class UserVK:
    """Пользователь ВК"""

    def __init__(self):
        self.token = user_token


def search_users(sex, age_at, age_to, city):
    """Ищет людей по критериям"""
    all_persons = []
    link_profile = 'https://vk.com/id'
    vk_ = vk_api.VkApi(token=user_token)
    response = vk_.method('users.search',
                          {'sort': 1,
                           'sex': sex,
                           'status': 1,
                           'age_from': age_at,
                           'age_to': age_to,
                           'has_photo': 1,
                           'count': 25,
                           'online': 1,
                           'hometown': city
                           })
    for element in response['items']:
        person = [
            element['first_name'],
            element['last_name'],
            link_profile + str(element['id']),
            element['id']
        ]
        all_persons.append(person)
        return all_persons


def get_photo(user_owner_id):
    """Поиск фотографий"""
    vk_ = vk_api.VkApi(token=user_token)
    try:
        response = vk_.method('photos.get',
                              {
                                  'access_token': user_token,
                                  'v': V,
                                  'owner_id': user_owner_id,
                                  'album_id': 'profile',
                                  'count': 10,
                                  'extended': 1,
                                  'photo_sizes': 1,
                              })
    except ApiError:
        return 'Фотографии недоступны'
    users_photos = []
    for i in range(10):
        try:
            users_photos.append(
                [response['items'][i]['likes']['count'],
                 'photo' + str(response['items'][i]['owner_id']) + '_' + str(response['items'][i]['id'])])
        except IndexError:
            users_photos.append(['нет фото.'])
        return users_photos


def sort_likes(photos):
    """Сортировка фотографий по лайкам, удаление лишних элементов"""
    result = []
    for el in photos:
        if el != 'Нет фотографий' and photos != 'Фотографии недоступны':
            result.append(el)
    return sorted(result)


def json_create(lst):
    """Создание JSON-файла с результатами"""
    today = datetime.date.today()
    today_str = f'{today.day}.{today.month}.{today.year}'
    res = {}
    res_list = []
    for num, info in enumerate(lst):
        res['data'] = today_str
        res['first_name'] = info[0]
        res['second_name'] = info[1]
        res['link'] = info[2]
        res['id'] = info[3]
        res_list.append(res.copy())

    with open("result.json", "a", encoding='UTF-8') as write_file:
        json.dump(res_list, write_file, ensure_ascii=False)

    print(f'Информация о загруженных файлах успешно записана в JSON-файл')

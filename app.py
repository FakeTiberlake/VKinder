import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from functions import search_users, get_photo, sort_likes, json_create
from database import engine, Session, write_msg, register_user, add_user, add_user_photos, add_to_black_list, \
    check_db_user, check_db_black, check_db_favorites, check_db_master, delete_db_blacklist, delete_db_favorites
from config import group_token

# Прочитаем файл с конфигурациями

config = configparser.ConfigParser()  # создаём объекта парсера
config.read("config.ini")  # читаем конфиг
print(config['VK']['group_token'])


# Работа с VK_API
vk = vk_api.VkApi(token=group_token)
longpoll = VkLongPoll(vk)
# Работа с базой данных
session = Session()
connection = engine.connect()


class Bot:
    """Общается с пользователем"""

    def __init__(self):
        self.token = group_token


def loop_bot():
    for this_event in longpoll.listen():
        if this_event.type == VkEventType.MESSAGE_NEW:
            if this_event.to_me:
                message_text = this_event.text
                return message_text, this_event.user_id


def menu_bot(id_num):
    write_msg(id_num,
              f"Вас приветствует бот - Vkinder!\n"
              f"\nЕсли вы здесь впервые - пройдите регистрацию.\n"
              f"Для регистрации введите - Да.\n"
              f"Если вы зарегистрированы - начинайте поиск.\n"
              f"\nДля поиска - девушка 18-25 Чита\n"
              f"Перейти в избранное нажмите - 2\n"
              f"Перейти в черный список - 0\n")

    def show_info():
        write_msg(user_id, f'Это была последняя анкета.'
                           f'Перейти в избранное - 2'
                           f'Перейти в черный список - 0'
                           f'Поиск - девушка 18-35 Иркутск'
                           f'Меню бота - Vkinder')

    def reg_new_user(id_num):
        write_msg(id_num, 'Вы прошли регистрацию.')
        write_msg(id_num,
                  f"Vkinder - для активации бота\n")
        register_user(id_num)

    def go_to_favorites(ids):
        all_all_users = check_db_favorites(ids)
        write_msg(ids, f'Избранные анкеты:')
        for nums, users in enumerate(all_all_users):
            write_msg(ids, f'{users.first_name}, {users.last_name}, {users.link}')
            write_msg(ids, '1 - Удалить из избранного, 0 - Далее \nq - Выход')
            msg_texts, user_ids = loop_bot()
            if msg_texts == '0':
                if nums >= len(all_all_users) - 1:
                    write_msg(user_ids, f'Это была последняя анкета.\n'
                                        f'Vkinder - вернуться в меню\n')
            # Удалить запись из базы данных - избранное
            elif msg_texts == '1':
                delete_db_favorites(users.vk_id)
                write_msg(user_ids, f'Анкета успешно удалена.')
                if nums >= len(all_all_users) - 1:
                    write_msg(user_ids, f'Это была последняя анкета.\n'
                                        f'Vkinder - вернуться в меню\n')
            elif msg_texts.lower() == 'q':
                write_msg(ids, 'Vkinder - для активации бота.')
                break

    def go_to_blacklist(ids):
        all_all_users = check_db_black(ids)
        write_msg(ids, f'Анкеты в черном списке:')
        for num, user in enumerate(all_all_users):
            write_msg(ids, f'{user.first_name}, {user.last_name}, {user.link}')
            write_msg(ids, '1 - Удалить из черного списка, 0 - Далее \nq - Выход')
            msg_texts, user_ids = loop_bot()
            if msg_texts == '0':
                if num >= len(all_all_users) - 1:
                    write_msg(user_ids, f'Это была последняя анкета.\n'
                                        f'Vkinder - вернуться в меню\n')
            # Удалить запись из базы данных - ЧЁРНЫЙ СПИСОК
            elif msg_texts == '1':
                print(user.id)
                delete_db_blacklist(user.vk_id)
                write_msg(user_ids, f'Анкета успешно удалена')
                if num >= len(all_all_users) - 1:
                    write_msg(user_ids, f'Это была последняя анкета.\n'
                                        f'Vkinder - вернуться в меню\n')
            elif msg_texts.lower() == 'q':
                write_msg(ids, 'Vkinder - для активации бота.')
                break


    def go_to_menu():
        while True:
            msg_text, user_id = loop_bot()
            if msg_text == "vkinder":
                menu_bot(user_id)
                msg_text, user_id = loop_bot()
                # Регистрация пользователя в базе данных
                if msg_text.lower() == 'да':
                    reg_new_user(user_id)
                # Поиск пары
                elif len(msg_text) > 1:
                    sex = 0
                    if msg_text[0:7].lower() == 'девушка':
                        sex = 1
                    elif msg_text[0:7].lower() == 'мужчина':
                        sex = 2
                    age_at = msg_text[8:10]
                    if int(age_at) < 18:
                        write_msg(user_id, 'Минимальный возраст - 18 лет.')
                        age_at = 18
                    age_to = msg_text[11:14]
                    if int(age_to) >= 100:
                        write_msg(user_id, 'Максимальный возраст 99 лет.')
                        age_to = 99
                    city = msg_text[14:len(msg_text)].lower()
                    # Поиск анкет
                    result = search_users(sex, int(age_at), int(age_to), city)
                    json_create(result)
                    current_user_id = check_db_master(user_id)
                    # Отбор анкет
                    for i in range(len(result)):
                        dating_user, blocked_user = check_db_user(result[i][3])
                        # Получение фотографий и сортировка по лайкам
                        user_photo = get_photo(result[i][3])
                        if user_photo == 'нет доступа к фото' or dating_user is not None or blocked_user is not None:
                            continue
                        sorted_user_photo = sort_likes(user_photo)
                        # Вывод сортированных данных по анкетам
                        write_msg(user_id, f'\n{result[i][0]}  {result[i][1]}  {result[i][2]}', )
                        try:
                            write_msg(user_id, f'фото:',
                                      attachment=','.join
                                      ([sorted_user_photo[-1][1], sorted_user_photo[-2][1],
                                        sorted_user_photo[-3][1]]))
                        except IndexError:
                            for photo in range(len(sorted_user_photo)):
                                write_msg(user_id, f'фото:',
                                          attachment=sorted_user_photo[photo][1])
                        # Ожидание ввода пользователем
                        write_msg(user_id, '1 - Добавить, 2 - Заблокировать, 0 - Далее, \nq - выход из поиска')
                        msg_text, user_id = loop_bot()
                        if msg_text == '0':
                            # Проверка на последнюю запись
                            if i >= len(result) - 1:
                                show_info()
                        # Добавление пользователя в избранное
                        elif msg_text == '1':
                            # Проверка на последнюю запись
                            if i >= len(result) - 1:
                                show_info()
                                break
                            # Попытка добавить анкету в базу данных
                            try:
                                add_user(user_id, result[i][3], result[i][1],
                                         result[i][0], city, result[i][2], current_user_id.id)
                                # Попытка добавить фотографию анкеты в базу данных
                                add_user_photos(user_id, sorted_user_photo[0][1],
                                                sorted_user_photo[0][0], current_user_id.id)
                            except AttributeError:
                                write_msg(user_id, 'Вы не зарегистрированы\n Введите Vkinder для перезагрузки бота')
                                break
                        # Добавление пользователя в чёрный список
                        elif msg_text == '2':
                            # Проверка на последнюю запись
                            if i >= len(result) - 1:
                                show_info()
                            # Блокирование пользователя
                            add_to_black_list(user_id, result[i][3], result[i][1],
                                              result[i][0], city, result[i][2],
                                              sorted_user_photo[0][1],
                                              sorted_user_photo[0][0], current_user_id.id)
                        elif msg_text.lower() == 'q':
                            write_msg(user_id, 'Введите Vkinder для активации бота')
                            break

                # Перейти в избранное
                elif msg_text == '2':
                    go_to_favorites(user_id)

                # Перейти в черный список
                elif msg_text == '0':
                    go_to_blacklist(user_id)


    if __name__ == '__main__':
        go_to_menu()
        
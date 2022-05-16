import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
import configparser
from random import randrange
import sqlalchemy as sq
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError, InvalidRequestError

# Прочитаем файл с конфигурациями

config = configparser.ConfigParser()  # создаём объекта парсера
config.read("config.ini")  # читаем конфиг
print(config['VK']['group_token'])

# Подключимся в БД

Base = declarative_base()

engine = sq.create_engine('postgresql://user@localhost:5432/vkinder_db',
                          client_encoding='utf8')

Session = sessionmaker(bind=engine)

# Работа с ВК
vk = vk_api.VkApi(token=group_token)
longpoll = VkLongPoll(vk)
# Работа с БД
session = Session()
connection = engine.connect()


class User(Base):
    """Пользователь ВК"""
    __tablename__ = 'user'
    id = sq.Column(sq.Integer, primary_key=True, autoincrement=True)
    vk_id = sq.Column(sq.Integer, unique=True)


class DatingUser(Base):
    """Избранные анкеты"""
    __tablename__ = 'dating_user'
    id = sq.Column(sq.Integer, primary_key=True, autoincrement=True)
    vk_id = sq.Column(sq.Integer, unique=True)
    first_name = sq.Column(sq.String)
    last_name = sq.Column(sq.String)
    marital_status = sq.Column(sq.String)
    city = sq.Column(sq.String)
    link = sq.Column(sq.String)
    id_user = sq.Column(sq.Integer, sq.ForeignKey('user.id', ondelete='CASCADE'))


class Photos(Base):
    """Фото избранных анкет"""
    __tablename__ = 'photos'
    id = sq.Column(sq.Integer, primary_key=True, autoincrement=True)
    link_photo = sq.Column(sq.String)
    count_likes = sq.Column(sq.Integer)
    count_comments = sq.Column(sq.Integer)
    id_dating_user = sq.Column(sq.Integer, sq.ForeignKey('dating_user.id', ondelete='CASCADE'))


class BlackList(Base):
    """Чёрный список"""
    __tablename__ = 'dating_user'
    id = sq.Column(sq.Integer, primary_key=True, autoincrement=True)
    vk_id = sq.Column(sq.Integer, unique=True)
    first_name = sq.Column(sq.String)
    last_name = sq.Column(sq.String)
    marital_status = sq.Column(sq.String)
    city = sq.Column(sq.String)
    link = sq.Column(sq.String)
    id_user = sq.Column(sq.Integer, sq.ForeignKey('user.id', ondelete='CASCADE'))


# Функции работы с базой данных
def delete_db_blacklist(ids):
    """Удаление пользователя из чёрного списка"""
    current_user = session.query(BlackList).filter_by(vk_id=ids).first()
    session.delete(current_user)
    session.commit()


def delete_db_favorites(ids):
    """Удаление пользователя из избранного"""
    current_user = session.query(DatingUser).filter_by(vk_id=ids).first()
    session.delete(current_user)
    session.commit()


def check_db_master(ids):
    """Проверка, зарегистрирован ли пользователь бота в базе данных"""
    current_user_id = session.query(User).filter_by(vk_id=ids).first()
    return current_user_id


def check_db_user(ids):
    """Проверка, есть ли пользователь в базе данных"""
    dating_user = session.query(DatingUser).filter_by(
        vk_id=ids).first()
    blocked_user = session.query(BlackList).filter_by(
        vk_id=ids).first()
    return dating_user, blocked_user


def check_db_black(ids):
    """Проверка, есть ли пользователь в черном списке"""
    current_users_id = session.query(User).filter_by(vk_id=ids).first()
    # Найдём все анкеты из чёрного списка, которые добавил этот пользователь
    all_users = session.query(BlackList).filter_by(id_user=current_users_id.id).all()
    return all_users


def check_db_favorites(ids):
    """Проверка, есть ли пользователь в избранном"""
    current_users_id = session.query(User).filter_by(vk_id=ids).first()
    # Найдём все анкеты из избранного, которые добавил этот пользователь
    all_all_users = session.query(DatingUser).filter_by(id_user=current_users_id.id).all()
    return all_all_users


def write_msg(user_id, message, attachment=None):
    """Написать сообщение пользователю"""
    vk.method('messages.send',
              {'user_id': user_id,
               'message': message,
               'random_id': randrange(10 ** 7),
               'attachment': attachment})


def register_user(vk_id):
    """Регистрация пользователя"""
    try:
        new_user = User(
            vk_id=vk_id
        )
        session.add(new_user)
        session.commit()
        return True
    except (IntegrityError, InvalidRequestError):
        return False


def add_user(event_id, vk_id, first_name, last_name, marital_status, city, link, id_user):
    """Сохранение выбранного пользователя в базе данных"""
    try:
        new_user = DatingUser(
            vk_id=vk_id,
            first_name=first_name,
            last_name=last_name,
            marital_status=marital_status,
            city=city,
            link=link,
            id_user=id_user
        )
        session.add(new_user)
        session.commit()
        write_msg(event_id,
                  'Пользователь успешно добавлен в избранное')
        return True
    except (IntegrityError, InvalidRequestError):
        write_msg(event_id,
                  'Пользователь уже в избранном')
        return False


def add_user_photos(event_id, link_photo, count_likes, count_comments, id_dating_user):
    """Сохранение в базе данных фотографий добавленного пользователя"""
    try:
        new_user = Photos(
            link_photo=link_photo,
            count_likes=count_likes,
            count_comments=count_comments,
            id_dating_user=id_dating_user
        )
        session.add(new_user)
        session.commit()
        write_msg(event_id,
                  'Фото пользователя сохранено в избранном')
        return True
    except (IntegrityError, InvalidRequestError):
        write_msg(event_id,
                  'Невозможно добавить фото этого пользователя (Уже сохранено)')
        return False


def add_to_black_list(event_id, vk_id, first_name, last_name, marital_status, city, link, link_photo, count_likes,
                      id_user):
    """Добавление пользователя в чёрный список"""
    try:
        new_user = BlackList(
            vk_id=vk_id,
            first_name=first_name,
            last_name=last_name,
            marital_status=marital_status,
            city=city,
            link=link,
            link_photo=link_photo,
            count_likes=count_likes,
            id_user=id_user
        )
        session.add(new_user)
        session.commit()
        write_msg(event_id,
                  'Пользователь успешно заблокирован')
        return True
    except (IntegrityError, InvalidRequestError):
        write_msg(event_id,
                  'Пользователь уже в черном списке')
        return False


if __name__ == '__main__':
    Base.metadata.create_all(engine)

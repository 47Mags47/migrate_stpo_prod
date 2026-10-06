import string 
import random

from datetime import datetime
from connect import (
    get_target_connection,
)

def convert_datetime(value):
    """
    Приводит дату к datetime для MySQL.
    """

    if value is None or value == "":
        return None

    if isinstance(value, datetime):
        return value

    value = str(value).strip()

    formats = [
        "%d.%m.%Y %H:%M:%S",
        "%d.%m.%Y %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
    ]

    for date_format in formats:

        try:
            return datetime.strptime(
                value,
                date_format,
            )

        except ValueError:
            continue

    raise ValueError(
        f"Не удалось преобразовать дату: {value}"
    )
    
def random_str(length):
    characters = string.ascii_letters + string.digits
    random_string = ''.join(random.choices(characters, k=length))
    return random_string
    
def create_file(data):
    connect = get_target_connection()
    
    with connect.cursor() as cursor:
        cursor.execute(f"""
            INSERT INTO `base__files`(
                `disk`,
                `path`,
                `name`,
                `origin_name`,
                `is_disabled`,
                `status_id`,
                `created_at`,
                `updated_at`,
                `deleted_at`
            )
            VALUES
            (
                '{data['disk']}',
                '{data['path']}',
                '{random_str(40)}',
                '{data['origin_name']}',
                0,
                1,
                '{convert_datetime(datetime.now())}',
                '{convert_datetime(datetime.now())}',
                NULL
            )
        """)
    connect.commit()
    return cursor.lastrowid

def log(msg):
    print(f"[{datetime.now():%H:%M:%S}] {msg}")
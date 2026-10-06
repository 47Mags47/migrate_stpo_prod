# from connect import check_connections
# from reset_db import reset_dbs

from administrate.migrate_cities import migrate_cities
from administrate.migrate_divisions import migrate_divisions

from base.migrate_user_division import migrate_user_division
from base.migrate_users import migrate_users
# from base.migrate_notifications import migrate_notifications
# # from appeal.migrate_appeals import migrate_appeals
from appeal.migrate_appeals2 import migrate_appeals
# from appeal.migrate_messages import migrate_messages

# RESET = "\033[0m"
# RED = "\033[31m"
# GREEN = "\033[32m"
# YELLOW = "\033[33m"
# BLUE = "\033[34m"
# CYAN = "\033[36m"

# def main():
#     print("=" * 60)
#     print("STPO DATABASE MIGRATION")
#     print("=" * 60)

#     # 1. Проверяем подключения
#     print(f"{BLUE}\n[1] Проверка подключений{RESET}")

#     if not check_connections():
#         print(f"{RED}\n✗ Подключение к базам не установлено{RESET}")
#         return

#     print(f"{GREEN}\n✓ Подключение к обеим базам успешно{RESET}")

#     # 2. Сбрасываем целевую БД
#     print(f"{BLUE}\n[2] Сброс целевой базы{RESET}")

#     reset_dbs()

#     # 3. Здесь дальше будут миграции
#     print(f"{BLUE}\n[3] Перенос данных{RESET}")

#     migrate_cities()
#     migrate_divisions()
#     migrate_users()
#     migrate_appeals()
#     # migrate_messages()
#     # migrate_notifications()

def migrate_administrate():
    migrate_cities()
    migrate_divisions()
    
def migrate_base():
    migrate_users()
    migrate_user_division()

def migrate_moduls():
    migrate_appeals()

if __name__ == "__main__":
    # migrate_administrate()
    # migrate_base()
    migrate_moduls()
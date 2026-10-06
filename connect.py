# migrate_db/connect.py
import os
from contextlib import contextmanager
import pymysql
from pymysql.cursors import DictCursor

# ------------------------------------------------------------------ env
def load_env(path=".env"):
    import os
    
    if not os.path.exists(path):
        raise FileNotFoundError(f"Файл {path} не найден")

    with open(path, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()

            if not line or line.startswith("#"):
                continue

            key, value = line.split("=", 1)
            os.environ[key.strip()] = value.strip()

load_env()

DB_SOURCE_HOST      = os.getenv("DB_SOURCE_HOST", 'localhost')
DB_SOURCE_PORT      = os.getenv("DB_SOURCE_PORT", 3306)
DB_SOURCE_USER      = os.getenv("DB_SOURCE_USER")
DB_SOURCE_PASSWORD  = os.getenv("DB_SOURCE_PASSWORD")
DB_SOURCE_DATABASE  = os.getenv("DB_SOURCE_DATABASE")

DB_TARGET_HOST      = os.getenv("DB_TARGET_HOST", 'localhost')
DB_TARGET_PORT      = os.getenv("DB_TARGET_PORT", 3306)
DB_TARGET_USER      = os.getenv("DB_TARGET_USER")
DB_TARGET_PASSWORD  = os.getenv("DB_TARGET_PASSWORD")
DB_TARGET_DATABASE  = os.getenv("DB_TARGET_DATABASE")

# ------------------------------------------------------------------ configs
SOURCE_CONFIG = dict(
    host=DB_SOURCE_HOST,
    port=DB_SOURCE_PORT,
    user=DB_SOURCE_USER,
    password=DB_SOURCE_PASSWORD,
    database=DB_SOURCE_DATABASE,
    charset="utf8mb4",
    cursorclass=DictCursor,
    autocommit=False,
)

TARGET_CONFIG = dict(
    host=DB_TARGET_HOST,
    port=DB_TARGET_PORT,
    user=DB_TARGET_USER,
    password=DB_TARGET_PASSWORD,
    database=DB_TARGET_DATABASE,
    charset="utf8mb4",
    cursorclass=DictCursor,
    autocommit=False,
)

# ------------------------------------------------------------------ engines (lazy)
def get_source_connection():
    return pymysql.connect(**SOURCE_CONFIG)


def get_target_connection():
    return pymysql.connect(**TARGET_CONFIG)


# ------------------------------------------------------------------ contexts
@contextmanager
def src_conn():
    """Контекстный менеджер: соединение с БД-источником.
    Коммитит при успехе, откатывает при исключении."""
    conn = get_source_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@contextmanager
def dst_conn():
    """Контекстный менеджер: соединение с БД-приёмником."""
    conn = get_target_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ------------------------------------------------------------------ diagnostics
def check_connection(cfg, database):
    """Проверяет подключение к MySQL и конкретной базе."""
    try:
        conn = pymysql.connect(**cfg)
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")

                cur.execute("SELECT DATABASE()")
                current_database = cur.fetchone()["DATABASE()"]

                cur.execute("SELECT VERSION()")
                version = cur.fetchone()["VERSION()"]

                cur.execute(
                    """
                    SELECT COUNT(*) AS cnt
                    FROM information_schema.tables
                    WHERE table_schema = DATABASE()
                    """
                )
                tables_count = cur.fetchone()["cnt"]

            print(f"✓ MySQL: {cfg['host']}")
            print(f"✓ База: {current_database}")
            print(f"✓ Версия MySQL: {version}")
            print(f"✓ Таблиц: {tables_count}")

            return True
        finally:
            conn.close()

    except Exception as e:
        print(f"✗ Ошибка подключения к базе {database}")
        print(f"  {e}")
        return False


def check_connections():
    print("=" * 60)
    print("ПРОВЕРКА ПОДКЛЮЧЕНИЙ К БАЗАМ ДАННЫХ")
    print("=" * 60)

    print("\n[1] Источник")
    source_ok = check_connection(SOURCE_CONFIG, DB_SOURCE_DATABASE)

    print("\n[2] Целевой")
    target_ok = check_connection(TARGET_CONFIG, DB_TARGET_DATABASE)

    print("\n" + "=" * 60)
    if source_ok and target_ok:
        print("✓ Оба подключения успешно установлены")
    else:
        print("✗ Не удалось подключиться ко всем базам")
    print("=" * 60)

    return source_ok and target_ok


if __name__ == "__main__":
    check_connections()
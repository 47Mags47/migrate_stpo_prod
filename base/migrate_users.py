#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Перенос пользователей
из STPO_prod.main__users в stpo.base__users.

division_id не переносится.
Связь пользователя с подразделением
будет перенесена отдельно через pivot-таблицу.

Пользователи с id=1 и id=2 в новой БД сохраняются.
"""

RESET = "\033[0m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
CYAN = "\033[36m"

from pathlib import Path
import sys
from datetime import datetime

sys.path.append(str(Path(__file__).resolve().parent.parent))

from connect import get_source_connection, get_target_connection


TRUNCATE_TARGET = True


def log(msg):
    print(f"[{datetime.now():%H:%M:%S}] {msg}")


def convert_datetime(value):
    """
    Приводит дату к формату MySQL:
    YYYY-MM-DD HH:MM:SS
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
            return datetime.strptime(value, date_format)
        except ValueError:
            continue

    raise ValueError(
        f"Не удалось преобразовать дату: {value}"
    )


def migrate_users():

    src = None
    dst = None

    try:
        src = get_source_connection()
        dst = get_target_connection()

        print(f'{CYAN}\n-MIGRATE_USERS{RESET}')

        # ============================================================
        # Получаем пользователей из старой БД
        # ============================================================

        with src.cursor() as cur:
            cur.execute("""
                SELECT
                    first_name,
                    last_name,
                    middle_name,
                    full_name,
                    phone,
                    email,
                    login,
                    password,
                    email_verified_at,
                    remember_token,
                    created_at,
                    updated_at
                FROM main__users
                WHERE id NOT IN (1, 7, 17)
                ORDER BY id
            """)
            users = cur.fetchall()

        log(f"Записей в источнике: {len(users)}")

        # ============================================================
        # Подготавливаем данные
        # ============================================================

        rows = []

        skipped_users = 0

        for user in users:
            try:
                email_verified_at = convert_datetime(user["email_verified_at"])
                created_at = convert_datetime(user["created_at"])
                updated_at = convert_datetime(user["updated_at"])

            except ValueError as exc:

                log(
                    f"⚠ Ошибка даты: "
                    f"id={user['id']} | "
                    f"name={user['full_name']} | "
                    f"value={exc}"
                )

                raise

            rows.append((
                user["first_name"] or "",
                user["last_name"],
                user["middle_name"],
                user["full_name"] or "",
                user["phone"],
                user["email"],
                user["login"] or "",
                email_verified_at,
                user["password"] or "",
                user["remember_token"],
                created_at,
                updated_at,
            ))

        # ============================================================
        # Вставка
        # ============================================================

        sql = """
            INSERT INTO base__users
                (
                    first_name,
                    last_name,
                    middle_name,
                    full_name,
                    phone,
                    email,
                    login,
                    email_verified_at,
                    password,
                    remember_token,
                    created_at,
                    updated_at
                )
            VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )
        """

        if rows:
            with dst.cursor() as cur:
                cur.executemany(sql, rows)

        log(f"Вставлено: {len(rows)}")

        # ============================================================
        # Проверяем максимальный ID
        # и устанавливаем AUTO_INCREMENT
        # ============================================================

        with dst.cursor() as cur:

            cur.execute("""
                SELECT MAX(id) AS m
                FROM base__users
            """)

            next_id = (cur.fetchone()["m"] or 0) + 1

            cur.execute(
                f"""
                ALTER TABLE base__users
                AUTO_INCREMENT = {next_id}
                """
            )

        # ============================================================
        # Commit
        # ============================================================

        dst.commit()

        log("✅ Успех")

    except Exception as exc:

        if dst is not None:
            dst.rollback()

        log(f"❌ Ошибка: {exc}")

        raise

    finally:

        if src is not None:
            src.close()

        if dst is not None:
            dst.close()


if __name__ == "__main__":

    try:
        migrate_users()

    except Exception:
        sys.exit(1)
import os
from datetime import timedelta

from colors import (
    CYAN,
    RESET,
    GREEN
)
from helpers import (
    log,
    random_str
)
from connect import (
    get_source_connection,
    get_target_connection,
)

# HACK По хорошему надо вынести в хелперы
def getUserLogins():
    from connect import (
        get_target_connection,
    )
    
    target_source = get_target_connection()
    with target_source.cursor() as cursor:
        cursor.execute(f"""
            SELECT `login`
            FROM `base__users`
        """)
        
    result = []
    for user in cursor.fetchall():
        result.append(user['login'])
    
    return result

def migrate_appeals():
    print(f"{CYAN}\n-MIGRATE_APPEALS{RESET}" )
    
    ### Заполняем переменные
    ##################################################
    ### Conection
    source_connect = get_source_connection()
    target_connect = get_target_connection()
    
    userLogins = getUserLogins()
    
    ### Получаем исходные данные
    ##################################################
    print(f"{CYAN}\n-Получаем исходные данные{RESET}" )
    
    ### Source appeals
    log(f"{RESET}-- Получение Appeals{RESET}")
    with source_connect.cursor() as cursor:
        cursor.execute("""
            SELECT
                `csvi__appeal__appeals`.`id`,
                `csvi__appeal__appeals`.`comment`,
                `csvi__appeal__them`.`name` AS 'them_name',
                `csvi__appeal__category`.`name` AS 'them_group_name',
                `csvi__appeal__statuses`.`name` AS 'status_name',
                `sender`.`login` AS 'sender_login',
                `worker`.`login` AS 'worker_login',
                `csvi__appeal__appeals`.`created_at`,
                `csvi__appeal__appeals`.`updated_at`
            FROM `csvi__appeal__appeals`
            INNER JOIN `csvi__appeal__them` ON `csvi__appeal__them`.`id` = `csvi__appeal__appeals`.`them_id`
            INNER JOIN `csvi__appeal__category` ON `csvi__appeal__category`.`id` = `csvi__appeal__them`.`category_id`
            INNER JOIN `csvi__appeal__statuses` ON `csvi__appeal__statuses`.`code` = `csvi__appeal__appeals`.`status_code`
            INNER JOIN `main__users` AS `sender` ON `sender`.`id` = `csvi__appeal__appeals`.`sender_id`
            LEFT JOIN `main__users` AS `worker` ON `worker`.`id` = `csvi__appeal__appeals`.`accepted_by`
            ORDER BY `csvi__appeal__appeals`.`created_at`
        """)
        sorce_appeals = cursor.fetchall()
    log(f"{GREEN}-- Appeals получены{RESET}")
    
    ### Переносим Обращения
    ##################################################
    print(f"{CYAN}\n-Перенос дынных{RESET}" )
    
    ### Создаем чаты
    log(f"{RESET}-- Создаем чаты{RESET}")
    with target_connect.cursor() as cursor:
        for i, appeal in enumerate(sorce_appeals):
            ### Создаем чаты
            cursor.execute(f"""
                INSERT INTO `base__chat`
                    (
                        created_at,
                        updated_at
                    )
                VALUES
                    (
                        '{appeal['created_at']}',
                        '{appeal['created_at']}'
                    )
            """)
            sorce_appeals[i]['chat_id'] = cursor.lastrowid
            
    target_connect.commit()
    log(f"{GREEN}-- Чаты созданы{RESET}")
    
    ### Добавляем участников
    log(f"{RESET}-- Добавление участников к чатам{RESET}")
    with target_connect.cursor() as cursor:
        for i, appeal in enumerate(sorce_appeals):
            
            ### Cоздатели
            if(appeal['sender_login'] not in userLogins):
                log(f"{RESET}Пропущена вставка: Не найдем пользователь '{appeal['sender_login']}'{RESET}") 
                continue 
                        
            cursor.execute(f"""
                INSERT INTO `base__chat_subscribers`(
                    `chat_id`, 
                    `user_id`
                )
                VALUES(
                    {appeal['chat_id']},
                    (SELECT `id` FROM `base__users` WHERE `login` LIKE '{appeal['sender_login']}')
                )
            """)

            ### Работники
            if(appeal['worker_login'] == None):
                continue
            
            if(appeal['worker_login'] not in userLogins):
                log(f"{RESET}Пропущена вставка: Не найдем пользователь '{appeal['worker_login']}'{RESET}") 
                continue 
            
            cursor.execute(f"""
                INSERT INTO `base__chat_subscribers`(
                    `chat_id`, 
                    `user_id`
                )
                VALUES(
                    {appeal['chat_id']},
                    (SELECT `id` FROM `base__users` WHERE `login` LIKE '{appeal['worker_login']}')
                )
            """)
            
    target_connect.commit()
    log(f"{GREEN}-- Участники добавлены{RESET}")
 
    ### Переносим обращения
    log(f"{RESET}-- Перенос обращений{RESET}")
    with target_connect.cursor() as cursor:
        for i, appeal in enumerate(sorce_appeals):
            sorce_appeals[i]['clear_comment'] = appeal['comment'].replace('"', '\\"')
            
            if(appeal['sender_login'] not in userLogins):
                log(f"{RESET}Пропущена вставка: Не найдем пользователь '{appeal['sender_login']}'{RESET}") 
                continue 
                
            query = f"""
                INSERT INTO `appeal__appeals` (
                    `comment`,
                    `chat_id`,
                    `sender_id`,
                    `worker_id`,
                    `them_id`,
                    `status_id`,
                    `created_at`,
                    `updated_at`
                )
                VALUES (
                    "{appeal['clear_comment']}",
                    {appeal['chat_id']},
                    (SELECT `id` FROM `base__users` WHERE `login` = "{appeal['sender_login']}"),
                    (
                        SELECT CASE
                            WHEN "{appeal['sender_login']}" = "None" THEN NULL
                            WHEN "{appeal['sender_login']}" != "None" THEN (SELECT `id` FROM `base__users` WHERE `login` = "{appeal['sender_login']}")
                        END
                    ),
                    COALESCE(
                        (
                            SELECT `appeal__thems`.`id`
                            FROM `appeal__thems`
                            INNER JOIN `appeal__them_groups` ON `appeal__them_groups`.`id` = `appeal__thems`.`group_id`
                            WHERE
                                `appeal__thems`.`name` = "{appeal['them_name']}"
                                AND `appeal__them_groups`.`name` = "{appeal['them_group_name']}"
                        ),
                        (
                            SELECT `appeal__thems`.`id`
                            FROM `appeal__thems`
                            WHERE `appeal__thems`.`name` = "Моей темы нет в списке"
                        )
                    ),
                    (
                        SELECT CASE
                            WHEN "{appeal['status_name']}" = "Принята" THEN (SELECT `id` FROM `appeal__statuses` WHERE `code` = "in_work")
                            WHEN "{appeal['status_name']}" = "Закрыта" THEN (SELECT `id` FROM `appeal__statuses` WHERE `code` = "closed")
                            WHEN "{appeal['status_name']}" = "Создана" THEN (SELECT `id` FROM `appeal__statuses` WHERE `code` = "new")
                            WHEN "{appeal['status_name']}" = "Возобновлена" THEN (SELECT `id` FROM `appeal__statuses` WHERE `code` = "reaccepted")
                        END
                    ),
                    "{appeal['created_at']}",
                    "{appeal['updated_at']}"
                )
            """
            cursor.execute(query)
            sorce_appeals[i]['new_appeal_id'] = cursor.lastrowid
            
    target_connect.commit()
    log(f"{GREEN}-- Обращения перенесены{RESET}")
    
    log(f"{RESET}-- Перенос сообщений{RESET}")
    with source_connect.cursor() as source_cursor:
        for i, appeal in enumerate(sorce_appeals):
            
            if(appeal['sender_login'] not in userLogins):
                log(f"{RESET}Пропущена вставка: Не найдем пользователь '{appeal['sender_login']}'{RESET}") 
                continue 
            
            sql = f"""
                SELECT
                    `main__users`.`login` as 'sender_login',
                    `csvi__appeal__messages`.`message`,
                    `csvi__appeal__messages`.`is_system`,
                    `csvi__appeal__messages`.`is_file`,
                    `csvi__appeal__messages`.`created_at`,
                    `csvi__appeal__messages`.`updated_at`
                FROM `csvi__appeal__messages`
                INNER JOIN `main__users` ON `main__users`.`id` = `csvi__appeal__messages`.`sender_id`
                WHERE `csvi__appeal__messages`.`appeal_id` = {appeal['id']}
            """
            source_cursor.execute(sql)
            source_messages = source_cursor.fetchall()
            
            with target_connect.cursor() as target_cursor:
                counter = 0
                for i, message in enumerate(source_messages):
                    
                    source_messages[i]['message'] = message['message'].replace("\\", "\\\\")
                    source_messages[i]['message'] = message['message'].replace('"', '\\"')
                    source_messages[i]['message'] = message['message'].replace("'", "\\'")
                    
                    message['message'] = message['message'].replace("\\", "\\\\")
                    message['message'] = message['message'].replace('"', '\\"')
                    message['message'] = message['message'].replace("'", "\\'")
                    
                    if (message['is_file'] == 0):           
                        sql = f"""
                            INSERT INTO `base__chat_messages`(
                                `message`,
                                `is_readed`,
                                `is_system`,
                                `chat_id`,
                                `sender_id`,
                                `created_at`,
                                `updated_at`,
                                `deleted_at`
                            )
                            VALUES(
                                '{ message['message'] }',
                                0,
                                { message['is_system'] },
                                { appeal['chat_id'] },
                                (SELECT `id` FROM `base__users` WHERE `login` = "{ message['sender_login'] }"),
                                '{ message['created_at'] }',
                                '{ message['updated_at'] }',
                                NULL
                            )
                        """
                        target_cursor.execute(sql)
                        
                        message['new_message_id'] = target_cursor.lastrowid
                        source_messages[i]['new_message_id'] = message['new_message_id']
                    else:
                        # создать пустое сообщение
                        sql = f"""
                            INSERT INTO `base__chat_messages`(
                                `message`,
                                `is_readed`,
                                `is_system`,
                                `chat_id`,
                                `sender_id`,
                                `created_at`,
                                `updated_at`,
                                `deleted_at`
                            )
                            VALUES(
                                NULL,
                                0,
                                { message['is_system'] },
                                { appeal['chat_id'] },
                                (SELECT `id` FROM `base__users` WHERE `login` = "{ message['sender_login'] }"),
                                '{ message['created_at'] }',
                                '{ message['updated_at'] }',
                                NULL
                            )
                        """
                        target_cursor.execute(sql)
                        
                        message['new_message_id'] = target_cursor.lastrowid
                        source_messages[i]['new_message_id'] = message['new_message_id']
                        
                        # Физически перенести файл
                        fileName = random_str(40)
                        fromPath = f"/var/www/STPO.Prod/storage/app/private/csvi/appeal/chat/{ appeal['id'] }"
                        toPath = f"/var/www/STPO/storage/app/private/appeals/messages/{ appeal['new_appeal_id'] }"
                        
                        fullFromPath = ''
                        flag = True
                        
                        if os.path.exists(f"{ fromPath }/{ message['message'] }"):
                            fullFromPath = f"{ fromPath }/{ message['message'] }"
                        elif os.path.exists(f"{ fromPath }/{ message['created_at'].strftime('%Y%m%d%H%M%S') }_{ message['message'] }"):
                            fullFromPath = f"{ fromPath }/{ message['created_at'].strftime('%Y%m%d%H%M%S') }_{ message['message'] }"
                        elif os.path.exists(f"{ fromPath }/{ (message['created_at'] + timedelta(hours=7)) .strftime('%Y%m%d%H%M%S') }_{ message['message'] }"):
                            fullFromPath = f"{ fromPath }/{ (message['created_at'] + timedelta(hours=7)) .strftime('%Y%m%d%H%M%S') }_{ message['message'] }"
                        elif os.path.exists(f"{ fromPath }/{ (message['created_at'] + timedelta(hours=7, seconds=1)) .strftime('%Y%m%d%H%M%S') }_{ message['message'] }"):
                            fullFromPath = f"{ fromPath }/{ (message['created_at'] + timedelta(hours=7, seconds=1)) .strftime('%Y%m%d%H%M%S') }_{ message['message'] }"
                        elif os.path.exists(f"{ fromPath }/{ (message['created_at'] + timedelta(hours=7, seconds=-1)) .strftime('%Y%m%d%H%M%S') }_{ message['message'] }"):
                            fullFromPath = f"{ fromPath }/{ (message['created_at'] + timedelta(hours=7, seconds=-1)) .strftime('%Y%m%d%H%M%S') }_{ message['message'] }"
                        else:
                            log(f"{RESET}Пропущена вставка: Не найден файл '{ appeal['id'] }/{ message['message'] } ({ message['created_at'].strftime('%Y%m%d%H%M%S') }){RESET}") 
                            flag = False
                            counter = counter + 1
                            continue
                        
                        if os.path.exists(toPath) == False:
                            os.mkdir(toPath)
                        
                        with open(fullFromPath, 'rb') as remote_file:
                            if os.path.exists(f"{ toPath }/{ fileName }") == True:
                                continue
                            
                            with open(f"{ toPath }/{ fileName }", 'wb') as local_file:
                                local_file.write(remote_file.read())
                                
                        # Создать запись в base__file 
                        if(flag == False):
                            continue
                        
                        sql = f"""
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
                            VALUES(
                                'appeals',
                                'messages',
                                '{ fileName }',
                                '{ message['message'] }',
                                0,
                                (SELECT `id` FROM `base__file_statuses` WHERE `code` LIKE 'ok'),
                                '{ message['created_at'] }',
                                '{ message['updated_at'] }',
                                NULL
                            )
                        """
                        target_cursor.execute(sql)
                        
                        message['file_id'] = target_cursor.lastrowid
                        message['new_file_name'] = fileName
                        
                        source_messages[i]['file_id'] = message['file_id']
                        source_messages[i]['new_file_name'] = fileName
                        
                        # Создать запись в base__chat_attachments
                        sql = f"""
                            INSERT INTO `base__chat_attachments`(
                                `message_id`,
                                `file_id`
                            )
                            VALUES(
                                { message['new_message_id'] },
                                { message['file_id'] }
                            )
                        """
                        target_cursor.execute(sql)
                        pass
    print(counter)
    target_connect.commit()
    log(f"{GREEN}-- Сообщения перенесены{RESET}")
                
    print('end')
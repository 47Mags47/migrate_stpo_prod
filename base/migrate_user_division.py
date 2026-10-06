from colors import (
    CYAN,
    RESET,
    GREEN
)
from helpers import (
    log
)
from connect import (
    get_source_connection,
    get_target_connection,
)

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

def migrate_user_division():
    userLogins = getUserLogins()
    
    print(f"{CYAN}\n-MIGRATE_PIVOT_USER_DIVISION{RESET}" )
    
    source_connect = get_source_connection()
    target_connect = get_target_connection()
    
    with source_connect.cursor() as cursor:
        cursor.execute("""
            SELECT 
                `main__users`.`login`,
                `main__divisions`.`name` AS 'division_name',
                `main__cityes`.`name` AS 'city_name'
            FROM `main__users`
            INNER JOIN `main__divisions` ON `main__divisions`.`id` = `main__users`.`division_id`
            INNER JOIN `main__cityes` ON `main__cityes`.`code` = `main__divisions`.`city_code`
        """)
        sorce_users = cursor.fetchall()
    log(f"{GREEN}Users получены{RESET}")

    with target_connect.cursor() as cursor:
        for user in sorce_users:
            if(user['login'] not in userLogins):
                log(f"{RESET}Пропущена вставка: Не найдем пользователь '{ user['login'] }'{RESET}") 
                continue 
            
            user['division_name'] = user['division_name'].replace('"', '\\"')
            user['city_name'] = user['city_name'].replace('"', '\\"')
            
            sql = f"""
                INSERT INTO `base__user_pivot_division`
                    (
                        `user_id`, 
                        `division_id`
                    )
                VALUES
                    (
                        (SELECT `id` FROM `base__users` WHERE `login` = '{ user['login'] }'), 
                        (
                            SELECT 
                                `administrate__divisions`.`id` 
                            FROM `administrate__divisions` 
                            INNER JOIN `administrate__cities` ON `administrate__cities`.`id` = `administrate__divisions`.`city_id`
                            WHERE 
                                `administrate__divisions`.`name` = '{ user['division_name'] }'
                                AND `administrate__cities`.`name` = '{ user['city_name'] }'
                        )
                    )
            """
            cursor.execute(sql)
            
    target_connect.commit()
    log(f"{GREEN}Данные перенесены{RESET}")  
    
if __name__ == "__main__":
    migrate_user_division()
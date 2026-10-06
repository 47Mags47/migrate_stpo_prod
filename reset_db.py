import subprocess
import sys
import os
from pathlib import Path

PROJECT_DIR = Path(os.getenv('TARGET_PATH'))

def run_command(command):
    print(f"\n$ {' '.join(command)}")
    print("-" * 60)

    result = subprocess.run(
        command,
        cwd=PROJECT_DIR,
        text=True,
    )

    if result.returncode != 0:
        print(f"\n✗ Команда завершилась с ошибкой: {result.returncode}")
        sys.exit(result.returncode)

    print("✓ Успешно")


def reset_dbs():
    print("=" * 60)
    print("СБРОС И ПЕРЕСОЗДАНИЕ БАЗЫ STPO")
    print("=" * 60)

    # php artisan migrate:fresh
    run_command([
        "php",
        "artisan",
        "migrate:fresh",
    ])

    # php artisan db:seed --class="Database\\Seeders\\Prod\\ProdSeeder"
    run_command([
        "php",
        "artisan",
        "db:seed",
        "--class=Database\\Seeders\\Prod\\ProdSeeder",
    ])

    print("\n" + "=" * 60)
    print("✓ БАЗА УСПЕШНО ПЕРЕСОЗДАНА И ЗАПОЛНЕНА")
    print("=" * 60)


if __name__ == "__main__":
    reset_dbs()

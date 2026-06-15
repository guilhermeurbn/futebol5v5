"""Remove contas e jogadores artificiais criados por testes automatizados."""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.db import load_json_data, save_json_data


TEST_USERNAME_RE = re.compile(r"^user\d+_", re.IGNORECASE)
TEST_PLAYER_NAME_RE = re.compile(r"^user\s+\d+$", re.IGNORECASE)
TEST_NOTIFICATION_RE = re.compile(
    r"usu[aá]rio\s+user\d+_.*\(\s*user\s+\d+\s*\)",
    re.IGNORECASE,
)


def main() -> int:
    users = load_json_data("users", [])
    test_users = [
        user
        for user in users
        if TEST_USERNAME_RE.match((user.get("username") or "").strip())
    ]
    test_user_ids = {user.get("id") for user in test_users if user.get("id")}
    clean_users = [user for user in users if user not in test_users]

    players = load_json_data("jogadores", [])
    test_players = [
        player
        for player in players
        if player.get("owner_user_id") in test_user_ids
        or TEST_PLAYER_NAME_RE.match((player.get("nome") or "").strip())
    ]
    clean_players = [player for player in players if player not in test_players]

    notifications = load_json_data(
        "admin_notificacoes",
        {"ultimo_id": 0, "notificacoes": [], "arquivadas": []},
    )
    clean_notifications = dict(notifications)
    removed_notifications = 0
    for key in ("notificacoes", "arquivadas"):
        items = notifications.get(key, [])
        test_items = [
            item
            for item in items
            if isinstance(item, dict)
            and TEST_NOTIFICATION_RE.search((item.get("mensagem") or "").strip())
        ]
        clean_notifications[key] = [
            item for item in items if item not in test_items
        ]
        removed_notifications += len(test_items)

    save_json_data("users", clean_users)
    save_json_data("jogadores", clean_players)
    save_json_data("admin_notificacoes", clean_notifications)

    print(f"Usuarios de teste removidos: {len(test_users)}")
    print(f"Jogadores de teste removidos: {len(test_players)}")
    print(f"Notificacoes de teste removidas: {removed_notifications}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

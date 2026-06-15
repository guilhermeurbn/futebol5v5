"""Define uma senha compartilhada para todas as contas do ambiente atual."""

import os
import sys

from werkzeug.security import check_password_hash

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.auth_service import AuthService


def main() -> int:
    password = os.getenv("NATRAVE_SHARED_PASSWORD", "")
    if len(password) < 6:
        print("Defina NATRAVE_SHARED_PASSWORD com pelo menos 6 caracteres.")
        return 1

    service = AuthService()
    users = service._carregar()

    for user in users:
        service.definir_nova_senha(user.get("id"), password)

    updated_users = service._carregar()
    for user in updated_users:
        user.pop("senha_resetada_em", None)
        user.pop("senha_resetada_por", None)
    service._salvar(updated_users)

    valid = all(
        check_password_hash(user.get("password_hash", ""), password)
        and not user.get("senha_temporaria_ativa", False)
        for user in updated_users
    )
    if not valid:
        print("Nao foi possivel validar todas as contas.")
        return 1

    print(f"Senha atualizada e verificada em {len(updated_users)} contas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

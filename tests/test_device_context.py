from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import criar_app


def test_login_uses_single_responsive_auth_intro():
    app = criar_app('testing')

    with app.test_client() as client:
        response = client.get(
            '/login',
            headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15',
            },
        )

    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'Times equilibrados' in body
    assert 'auth-title--hero-lockup' in body

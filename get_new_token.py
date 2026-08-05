import argparse
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
]


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Authorize web2kindle to send mail through Gmail."
    )
    parser.add_argument(
        "--secrets-dir",
        default=Path("."),
        type=Path,
        help="directory containing client_secret.json and token.json",
    )
    args = parser.parse_args(argv)
    client_secret_path = args.secrets_dir / "client_secret.json"
    token_path = args.secrets_dir / "token.json"
    flow = InstalledAppFlow.from_client_secrets_file(
        str(client_secret_path),
        SCOPES,
    )
    creds = flow.run_local_server(port=0)
    token_path.write_text(creds.to_json(), encoding="utf-8")


if __name__ == "__main__":
    main()

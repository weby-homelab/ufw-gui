"""Explicit one-time provisioning for a brand-new UFW-GUI data directory."""

from backend.services.database_service import initialize_empty_database


def main() -> None:
    initialize_empty_database()
    print("Initialized a new UFW-GUI database. Start the application normally.")


if __name__ == "__main__":
    main()

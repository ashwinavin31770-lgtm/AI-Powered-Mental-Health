from backend.app.database import DB_PATH, init_db, seed_defaults


def main() -> None:
    init_db()
    seed_defaults()
    print(f"Database initialized at {DB_PATH}")


if __name__ == "__main__":
    main()
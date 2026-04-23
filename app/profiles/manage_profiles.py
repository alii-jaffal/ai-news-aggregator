import argparse
import json
import sys

from app.database.repository import Repository
from app.profiles.profile_store import get_runtime_user_profile


def _parse_preference_entries(entries: list[str]) -> dict:
    preferences = {}
    for entry in entries:
        if "=" not in entry:
            raise ValueError(f"Invalid preference entry: {entry}")
        key, raw_value = entry.split("=", 1)
        key = key.strip()
        raw_value = raw_value.strip()
        if not key:
            raise ValueError(f"Invalid preference key in entry: {entry}")
        try:
            value = json.loads(raw_value)
        except json.JSONDecodeError:
            value = raw_value
        preferences[key] = value
    return preferences


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage DB-backed user profiles.")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("list", help="List stored user profiles.")
    subparsers.add_parser("show-active", help="Show the active user profile.")

    upsert = subparsers.add_parser("upsert", help="Create or update a user profile.")
    upsert.add_argument("--slug", required=True)
    upsert.add_argument("--name", required=True)
    upsert.add_argument("--title", required=True)
    upsert.add_argument("--background", required=True)
    upsert.add_argument("--expertise-level", required=True)
    upsert.add_argument("--interest", action="append", default=[], dest="interests")
    upsert.add_argument(
        "--preferred-source-type",
        action="append",
        default=[],
        dest="preferred_source_types",
    )
    upsert.add_argument("--preference", action="append", default=[], dest="preferences")
    upsert.add_argument("--newsletter-top-n", type=int, required=True)
    upsert.add_argument("--active", action="store_true")

    set_active = subparsers.add_parser("set-active", help="Set the active user profile.")
    set_active.add_argument("slug")

    return parser


def _print_profile_list(repo: Repository) -> None:
    profiles = repo.list_user_profiles()
    if not profiles:
        print("No user profiles found.")
        return

    for profile in profiles:
        marker = "*" if profile.is_active else "-"
        print(
            f"{marker} {profile.slug} | {profile.name} | "
            f"top_n={profile.newsletter_top_n} | "
            f"sources={','.join(profile.preferred_source_types or [])}"
        )


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 1

    repo = Repository()

    if args.command == "list":
        _print_profile_list(repo)
        return 0

    if args.command == "show-active":
        profile = get_runtime_user_profile(repo=repo)
        print(json.dumps(profile, indent=2, sort_keys=True))
        return 0

    if args.command == "upsert":
        profile = repo.upsert_user_profile(
            slug=args.slug,
            name=args.name,
            title=args.title,
            background=args.background,
            expertise_level=args.expertise_level,
            interests=args.interests,
            preferred_source_types=args.preferred_source_types,
            preferences=_parse_preference_entries(args.preferences),
            newsletter_top_n=args.newsletter_top_n,
            is_active=True if args.active else None,
        )
        print(f"Upserted profile {profile.slug}")
        return 0

    if args.command == "set-active":
        profile = repo.set_active_user_profile(args.slug)
        if profile is None:
            print(f"User profile not found: {args.slug}", file=sys.stderr)
            return 1
        print(f"Active profile set to {profile.slug}")
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

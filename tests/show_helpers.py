from pathlib import Path

HELLO_C = '#include <stdio.h>\nint main(void){puts("hello, world");return 0;}\n'


def write_entry(root: Path, slug: str, station: int, source: str, *,
                build: str = "cc -o prog prog.c", run: str = "./prog",
                run_seconds: float = 5.0, build_seconds: float = 30.0,
                fallback: str | None = None, full_screen: bool | None = None,
                year: int = 2026, rows: int | None = None) -> Path:
    d = root / slug
    d.mkdir(parents=True)
    (d / "prog.c").write_text(source)
    text = (
        f'title = "{slug}"\nauthor = "Test Author"\nyear = {year}\nstation = {station}\n'
        f'source = "prog.c"\nbuild = "{build}"\nrun = "{run}"\n'
        f'run_seconds = {run_seconds}\nbuild_seconds = {build_seconds}\n'
    )
    if full_screen is not None:
        text += f'full_screen = {"true" if full_screen else "false"}\n'
    if rows is not None:
        text += f"rows = {rows}\n"
    (d / "entry.toml").write_text(text)
    if fallback is not None:
        (d / "fallback.cast").write_text(fallback)
    return d

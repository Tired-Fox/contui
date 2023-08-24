from pathlib import Path
from subprocess import Popen, PIPE

from badges import *

if __name__ == "__main__":
    from tempfile import TemporaryFile
    from re import search, finditer, match, IGNORECASE
    import sys

    args = sys.argv[1:]
    try:
        project = args[0]
        name = args[1]
    except:
        raise ValueError("Expected at least two arguments: '<repo>' '<name>'")

    primary = "9cf"
    if len(args) >= 3:
        primary = args[1]
    
    project_badges: list[tuple[str, str, Parameters]] = [
        (
            "version",
            Create.badge("verson", str(__import__(name).__version__), "9cf"),
            {"style": "flat-square", "logo": "aiohttp", "logoColor": "white"},
        ),
        (
            "license",
            f"github/license/tired-fox/{project}.svg",
            {"style": "flat-square", "color": primary}
        ),
        (
            "maintained",
            f"badge/maintained-yes-{primary}.svg",
            {"style": "flat-square"}
        ),
        (
            "built_with_love",
            "badge/Built_With-❤-D15D27",
            {"style": "for-the-badge", "labelColor": "E26D25"}
        ),
    ]

    def _get_test_links() -> list[tuple[Name, Url]]:
        passed, total, covered = 0, 0, 0
        with TemporaryFile() as file:
            data = Popen(f'pytest --cov="./{project}" tests/', stdout=file, stderr=PIPE)
            data.wait()
            file.seek(0)
            output = file.read().decode("utf-8")

        for line in output.split("\n"):
            if search(r"TOTAL\s+(\d+)\s+(\d+)\s+(\d+)%", line) is not None:
                _, _, covered = search(r"TOTAL\s+(\d+)\s+(\d+)\s+(\d+)%", line).groups()
                covered = int(covered)
            elif search(r"(failed|passed)", line) is not None:
                for status in finditer(r"\s(\d{1,})\s(?!warning)([a-z]+),?", line):
                    count, condition = status.groups()
                    if condition == "passed":
                        passed = int(count)
                    total += int(count)

        test_link = sheild_io_link(
            Create.badge(
                "tests",
                f"{passed}/{total}",
                Color.percentage(passed / total if passed > 0 else 0),
            ),
            {
                "style": "flat-square",
                "logo": "testcafe",
                "logoColor": "white",
            },
        )

        test_cov_link = sheild_io_link(
            Create.badge("coverage", f"{covered}%25", Color.percentage(covered / 100)),
            {
                "style": "flat-square",
                "logo": "codeforces",
                "logoColor": "white",
            },
        )

        return [("tests", test_link), ("coverage", test_cov_link)]

    badges = Badges(_get_test_links)

    for badge in project_badges:
        badges.badge(*badge)

    badges.collect("assets/badges/")
    header_badges = f"""\
<!-- Header Badges -->

<div align="center">
  
<img src="assets/badges/version.svg" alt="Version"/>
<a href="https://github.com/Tired-Fox/{project}/releases" alt="Release"><img src="https://img.shields.io/github/v/release/tired-fox/{project}.svg?style=flat-square&color=9cf"/></a>
<a href="https://github.com/Tired-Fox/{project}/blob/main/LICENSE" alt="License"><img src="assets/badges/license.svg"/></a>
<img src="assets/badges/maintained.svg" alt="Maintained"/>
<br>
<img src="assets/badges/tests.svg" alt="Tests"/>
<img src="assets/badges/coverage.svg" alt="Coverage"/>
  
</div>

<!-- End Header -->\
"""
    footer_badges = """\
<!-- Footer Badges --!>

<br>
<div align="center">
  <img src="assets/badges/made_with_python.svg" alt="Made with python"/>
  <img src="assets/badges/built_with_love.svg" alt="Built with love"/>
</div>

<!-- End Footer -->\
"""
    print("Copying badge: made_with_python")
    Path("assets/badges/made_with_python.svg").write_text(PRESETS["made_with_python"])

    readme = [path for path in Path("").glob("*.md") if path.as_posix().lower() == "readme.md"]
    readme = readme[0] if len(readme) > 0 else None

    if readme is not None:
        lines = readme.read_text().split("\n")
        idx = 0
        while idx < len(lines):
            if match(r"\s*<!--\s*Header\s*Badges\s*-->\s*", lines[idx], IGNORECASE) is not None:
                entry = idx
                end = idx
                while idx < len(lines):
                    if match(r"\s*<!--\s*End\s*Header\s*-->\s*", lines[idx], IGNORECASE) is not None: 
                        end = idx
                        break
                    idx += 1
                else:
                    end = entry
                lines[entry:end+1] = header_badges.split("\n")
                break
            idx += 1

        idx = 0
        while idx < len(lines):
            if match(r"\s*<!--\s*Footer\s*Badges\s*-->\s*", lines[idx], IGNORECASE) is not None:
                entry = idx
                end = idx
                while idx < len(lines):
                    if match(r"\s*<!--\s*End\s*Footer\s*-->\s*", lines[idx], IGNORECASE) is not None: 
                        end = idx
                        break
                    idx += 1
                else:
                    end = entry
                lines[entry:end+1] = footer_badges.split("\n")
                break
            idx += 1

        readme.write_text("\n".join(lines))
        print("\x1b[1mUpdated README.md\x1b[22m")
    else:
        print(f"\x1b[1mHeader Badges:\x1b[22m\n{header_badges}")
        print(f"\x1b[1mFooter Badges:\x1b[22m\n{footer_badges}")

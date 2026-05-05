#!/usr/bin/env python3

import os
import shlex
import subprocess
import difflib
from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.application.current import get_app
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.styles import Style


COMMANDS = {
    "help": {
        "desc": "사용 가능한 명령어 목록을 보여줍니다.",
        "params": [],
        "example": "help",
    },
    "exit": {
        "desc": "커스텀 쉘을 종료합니다.",
        "params": [],
        "example": "exit",
    },
    "clear": {
        "desc": "화면을 깨끗하게 지웁니다.",
        "params": [],
        "example": "clear",
    },
    "pwd": {
        "desc": "현재 작업 중인 디렉터리 위치를 보여줍니다.",
        "params": [],
        "example": "pwd",
    },
    "cd": {
        "desc": "디렉터리를 이동합니다.",
        "params": ["..", "~", "/", "./"],
        "example": "cd ..",
    },
    "ls": {
        "desc": "현재 디렉터리의 파일 목록을 보여줍니다.",
        "params": ["-l", "-a", "-al", "-lh"],
        "example": "ls -al",
    },
    "mkdir": {
        "desc": "새 디렉터리를 만듭니다.",
        "params": ["폴더이름"],
        "example": "mkdir test",
    },
    "touch": {
        "desc": "새 파일을 만들거나 파일의 수정 시간을 갱신합니다.",
        "params": ["파일이름"],
        "example": "touch memo.txt",
    },
    "cat": {
        "desc": "파일 내용을 출력합니다.",
        "params": ["파일이름"],
        "example": "cat memo.txt",
    },
    "grep": {
        "desc": "파일 내용에서 특정 문자열이나 패턴을 검색합니다.",
        "params": ['"검색어"', "-n", "-i", "-r"],
        "example": 'grep -n "main" program.c',
    },
    "cp": {
        "desc": "파일이나 디렉터리를 복사합니다.",
        "params": ["원본", "대상", "-r"],
        "example": "cp a.txt b.txt",
    },
    "mv": {
        "desc": "파일을 이동하거나 이름을 바꿉니다.",
        "params": ["원본", "대상"],
        "example": "mv old.txt new.txt",
    },
    "rm": {
        "desc": "파일을 삭제합니다. 주의해서 사용해야 합니다.",
        "params": ["파일이름", "-r", "-i"],
        "example": "rm -i memo.txt",
    },
    "df": {
        "desc": "디스크 사용량을 보여줍니다.",
        "params": ["-h"],
        "example": "df -h",
    },
    "free": {
        "desc": "메모리 사용량을 보여줍니다.",
        "params": ["-h"],
        "example": "free -h",
    },
    "ps": {
        "desc": "실행 중인 프로세스를 보여줍니다.",
        "params": ["aux", "-ef"],
        "example": "ps aux",
    },
    "explain": {
        "desc": "명령어의 의미와 예시를 초보자용으로 설명합니다.",
        "params": [],
        "example": "explain grep",
    },
}


ALIASES = {
    "ll": "ls -al",
    "la": "ls -a",
    "..": "cd ..",
    "home": "cd ~",
}


class BeginnerShellCompleter(Completer):
    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        words = text.split()

        # 1. 첫 번째 단어 입력 중이면 명령어 자동완성
        if len(words) == 0 or (len(words) == 1 and not text.endswith(" ")):
            current = words[0] if words else ""
            all_commands = list(COMMANDS.keys()) + list(ALIASES.keys())

            for cmd in all_commands:
                if cmd.startswith(current):
                    desc = COMMANDS.get(
                        cmd,
                        {"desc": f"단축 명령어: {ALIASES.get(cmd, '')}"}
                    )["desc"]

                    yield Completion(
                        cmd,
                        start_position=-len(current),
                        display=cmd,
                        display_meta=desc,
                    )

        # 2. 두 번째 단어부터는 파라미터 + 파일/디렉터리 자동완성
        else:
            cmd = words[0]
            current = words[-1] if not text.endswith(" ") else ""

            if cmd in ALIASES:
                cmd = ALIASES[cmd].split()[0]

            # 명령어별 추천 파라미터
            if cmd in COMMANDS:
                for param in COMMANDS[cmd]["params"]:
                    if str(param).startswith(current):
                        yield Completion(
                            param,
                            start_position=-len(current),
                            display=param,
                            display_meta=f"{cmd} 명령어에서 자주 쓰는 옵션/인자",
                        )

            # 현재 폴더의 파일/디렉터리 자동완성
            try:
                for item in os.listdir("."):
                    if item.startswith(current):
                        suffix = "/" if os.path.isdir(item) else ""
                        yield Completion(
                            item + suffix,
                            start_position=-len(current),
                            display=item + suffix,
                            display_meta="파일/디렉터리",
                        )
            except PermissionError:
                pass


def print_help():
    print("\n[사용 가능한 명령어]")
    for cmd, info in COMMANDS.items():
        print(f"  {cmd:<10} - {info['desc']}")
        print(f"             예시: {info['example']}")

    print("\n[단축 명령어]")
    for alias, real_cmd in ALIASES.items():
        print(f"  {alias:<10} -> {real_cmd}")

    print("\n[단축키]")
    print("  Ctrl + L      화면 지우기")
    print("  Ctrl + Space  자동완성 열기")
    print("  F2            도움말 보기")
    print()


def explain_command(cmd):
    if cmd in ALIASES:
        print(f"\n'{cmd}'는 단축 명령어입니다.")
        print(f"실제로는 다음 명령어를 실행합니다: {ALIASES[cmd]}\n")
        return

    if cmd not in COMMANDS:
        print(f"\n'{cmd}'에 대한 설명이 아직 등록되어 있지 않습니다.")
        print("그래도 리눅스에 설치된 명령어라면 실행은 가능할 수 있습니다.\n")
        return

    info = COMMANDS[cmd]
    params = ", ".join(info["params"]) if info["params"] else "없음"

    print(f"\n[{cmd}] 명령어 설명")
    print(f"의미: {info['desc']}")
    print(f"자주 쓰는 옵션/인자: {params}")
    print(f"사용 예시: {info['example']}\n")


def run_builtin(args):
    cmd = args[0]

    if cmd == "exit":
        print("커스텀 쉘을 종료합니다.")
        raise SystemExit

    elif cmd == "help":
        print_help()

    elif cmd == "clear":
        os.system("clear")

    elif cmd == "pwd":
        print(f"현재 위치: {os.getcwd()}")

    elif cmd == "cd":
        if len(args) < 2:
            target = str(Path.home())
        else:
            target = os.path.expanduser(args[1])

        try:
            os.chdir(target)
            print(f"이동 완료: {os.getcwd()}")
        except FileNotFoundError:
            print("오류: 그런 디렉터리가 없습니다.")
        except NotADirectoryError:
            print("오류: 디렉터리가 아니라 파일입니다.")
        except PermissionError:
            print("오류: 해당 디렉터리에 접근할 권한이 없습니다.")

    elif cmd == "explain":
        if len(args) < 2:
            print("사용법: explain 명령어")
            print("예시: explain grep")
        else:
            explain_command(args[1])

    else:
        return False

    return True


def make_readable_output(cmd, result):
    output = result.stdout.strip()
    error = result.stderr.strip()

    if output:
        if cmd == "ls":
            print("\n[파일 목록]")
            print(output)
            print()

        elif cmd == "df":
            print("\n[디스크 사용량]")
            print("Tip: Use%가 높을수록 디스크 공간이 부족하다는 뜻입니다.")
            print(output)
            print()

        elif cmd == "free":
            print("\n[메모리 사용량]")
            print("Tip: available 값이 현재 사용 가능한 메모리입니다.")
            print(output)
            print()

        elif cmd == "ps":
            print("\n[프로세스 목록]")
            print("Tip: PID는 프로세스 번호입니다. kill 명령어에서 사용할 수 있습니다.")
            print(output)
            print()

        else:
            print(output)

    if error:
        print("\n[오류 메시지]")
        print(error)
        print("\n초보자용 안내:")
        print("- 명령어 철자가 맞는지 확인해보세요.")
        print("- 파일 이름이나 디렉터리 이름이 실제로 존재하는지 확인해보세요.")
        print("- 권한 문제가 있다면 sudo가 필요한 상황일 수 있습니다.\n")


def run_external(args):
    cmd = args[0]

    try:
        result = subprocess.run(
            args,
            text=True,
            capture_output=True,
        )
        make_readable_output(cmd, result)

    except FileNotFoundError:
        similar = difflib.get_close_matches(cmd, list(COMMANDS.keys()), n=1)

        print(f"오류: '{cmd}' 명령어를 찾을 수 없습니다.")

        if similar:
            print(f"혹시 '{similar[0]}' 명령어를 입력하려고 했나요?")

        print("help를 입력하면 이 쉘에서 추천하는 명령어를 볼 수 있습니다.")

    except PermissionError:
        print("오류: 실행 권한이 없습니다.")

    except Exception as e:
        print(f"알 수 없는 오류가 발생했습니다: {e}")


def expand_alias(line):
    if not line.strip():
        return line

    first = line.split()[0]

    if first in ALIASES:
        rest = line.split()[1:]
        return ALIASES[first] + (" " + " ".join(rest) if rest else "")

    return line


def build_bottom_toolbar():
    try:
        app = get_app()
        text = app.current_buffer.text.strip()
    except Exception:
        return HTML(
            "<bottom-toolbar>"
            "명령어를 입력하세요. 예: help, ls, cd, grep"
            "</bottom-toolbar>"
        )

    if not text:
        return HTML(
            "<bottom-toolbar>"
            "명령어를 입력하세요. 예: help, ls, cd, grep | "
            "Ctrl+Space: 자동완성 | F2: 도움말 | Ctrl+L: 화면 지우기"
            "</bottom-toolbar>"
        )

    words = text.split()
    cmd = words[0]

    if cmd in ALIASES:
        real_cmd = ALIASES[cmd].split()[0]
        real_info = COMMANDS.get(real_cmd)

        if real_info:
            params = ", ".join(real_info["params"]) if real_info["params"] else "파라미터 없음"
            return HTML(
                f"<bottom-toolbar>"
                f"단축 명령어: {cmd} → {ALIASES[cmd]} | "
                f"{real_cmd}: {real_info['desc']} | "
                f"파라미터: {params} | "
                f"예시: {real_info['example']}"
                f"</bottom-toolbar>"
            )

        return HTML(
            f"<bottom-toolbar>"
            f"단축 명령어: {cmd} → {ALIASES[cmd]}"
            f"</bottom-toolbar>"
        )

    if cmd in COMMANDS:
        info = COMMANDS[cmd]
        params = ", ".join(info["params"]) if info["params"] else "파라미터 없음"

        return HTML(
            f"<bottom-toolbar>"
            f"{cmd} | {info['desc']} | "
            f"파라미터: {params} | "
            f"예시: {info['example']}"
            f"</bottom-toolbar>"
        )

    similar = difflib.get_close_matches(cmd, list(COMMANDS.keys()) + list(ALIASES.keys()), n=1)

    if similar:
        return HTML(
            f"<bottom-toolbar>"
            f"'{cmd}' 명령어를 찾을 수 없습니다. "
            f"혹시 '{similar[0]}'를 입력하려고 했나요?"
            f"</bottom-toolbar>"
        )

    return HTML(
        "<bottom-toolbar>"
        "등록되지 않은 명령어입니다. 리눅스 명령어라면 실행은 가능할 수 있습니다."
        "</bottom-toolbar>"
    )


def main():
    style = Style.from_dict({
        "prompt": "ansigreen bold",
        "bottom-toolbar": "reverse",
    })

    kb = KeyBindings()

    @kb.add("c-l")
    def _(event):
        os.system("clear")

    @kb.add("f2")
    def _(event):
        print_help()

    @kb.add("c-space")
    def _(event):
        event.app.current_buffer.start_completion(select_first=False)

    session = PromptSession(
        completer=BeginnerShellCompleter(),
        key_bindings=kb,
        complete_while_typing=True,
        bottom_toolbar=build_bottom_toolbar,
        style=style,
    )

    print("Beginner Shell에 오신 것을 환영합니다.")
    print("help를 입력하면 사용 가능한 명령어를 볼 수 있습니다.")
    print("exit를 입력하면 종료합니다.\n")

    while True:
        cwd = os.getcwd()

        try:
            line = session.prompt(HTML(f"<prompt>beginner-shell:{cwd}$ </prompt>"))

        except KeyboardInterrupt:
            print("\nCtrl+C 입력됨. 종료하려면 exit를 입력하세요.")
            continue

        except EOFError:
            print("\n커스텀 쉘을 종료합니다.")
            break

        line = line.strip()

        if not line:
            continue

        line = expand_alias(line)

        try:
            args = shlex.split(line)

        except ValueError:
            print("오류: 따옴표 사용이 올바르지 않습니다.")
            continue

        if not args:
            continue

        if args[0] in COMMANDS:
            handled = run_builtin(args)

            if not handled:
                run_external(args)
        else:
            run_external(args)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3

import os
import shlex
import subprocess
import difflib
import json
import getpass
import re
from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.application.current import get_app
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.styles import Style


DEFAULT_COMMANDS = {
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
        "params": ["\"검색어\"", "-n", "-i", "-r"],
        "example": "grep -n \"main\" program.c",
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


def load_commands():
    try:
        script_dir = Path(__file__).parent
        json_path = script_dir / "commands.json"
        if json_path.exists():
            with open(json_path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"[경고] commands.json 로드 중 오류 발생: {e}")
    return DEFAULT_COMMANDS


COMMANDS = load_commands()


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


background_processes = []
local_variables = {}


def expand_variables(line):
    def replace_braces(match):
        var_name = match.group(1)
        return local_variables.get(var_name, os.environ.get(var_name, ""))
        
    line = re.sub(r'\${([a-zA-Z_][a-zA-Z0-9_]*)}', replace_braces, line)
    
    def replace_plain(match):
        var_name = match.group(1)
        return local_variables.get(var_name, os.environ.get(var_name, ""))
        
    line = re.sub(r'\$([a-zA-Z_][a-zA-Z0-9]*)', replace_plain, line)
    return line


def run_builtin(args, session=None):
    cmd = args[0]

    if cmd == "exit":
        print("커스텀 쉘을 종료합니다.")
        raise SystemExit

    elif cmd == "help":
        print_help()

    elif cmd == "clear":
        os.system("cls" if os.name == "nt" else "clear")

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

    elif cmd == "export":
        if len(args) < 2:
            for k, v in os.environ.items():
                print(f"export {k}={shlex.quote(v)}")
        else:
            arg = args[1]
            if "=" in arg:
                key, val = arg.split("=", 1)
                os.environ[key] = val
                local_variables[key] = val
                print(f"환경 변수 설정 완료: {key}={val}")
            else:
                key = arg
                if key in local_variables:
                    os.environ[key] = local_variables[key]
                    print(f"환경 변수로 등록 완료 (로컬 변수 '{key}'의 값 복사): {key}={os.environ[key]}")
                else:
                    print(f"오류: '{key}'라는 로컬 변수가 존재하지 않습니다.")

    elif cmd == "history":
        if session and hasattr(session, "history"):
            history_strings = list(session.history.get_strings())
            for idx, h_cmd in enumerate(history_strings, 1):
                print(f"  {idx:<4}  {h_cmd}")
        else:
            print("히스토리 내역이 없습니다.")

    elif cmd == "klas":
        script_dir = Path(__file__).parent
        klas_script = script_dir / "klas.py"
        if not klas_script.exists():
            print("오류: klas.py 스크립트 파일을 찾을 수 없습니다.")
        else:
            import sys
            try:
                subprocess.run(
                    [sys.executable, str(klas_script)],
                    stdin=sys.stdin,
                    stdout=sys.stdout,
                    stderr=sys.stderr,
                )
            except Exception as e:
                print(f"klas 실행 중 오류 발생: {e}")

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


def run_external(line, args, is_background=False):
    import sys
    cmd = args[0]
    has_pipeline_or_redir = any(symbol in line for symbol in ["|", ">", "<"])
    capture_cmds = ["df", "free", "ps"]
    should_capture = (cmd in capture_cmds) and not has_pipeline_or_redir and not is_background

    def inject_grep_color(cmd_line):
        if "--color" in cmd_line:
            return cmd_line
        return re.sub(r'\b(grep|egrep|fgrep)\b', r'\1 --color=auto', cmd_line)

    try:
        if is_background:
            line_to_run = inject_grep_color(line)
            if has_pipeline_or_redir:
                p = subprocess.Popen(
                    line_to_run,
                    shell=True,
                    stdin=subprocess.DEVNULL,
                    preexec_fn=os.setsid if (os.name != 'nt' and hasattr(os, 'setsid')) else None
                )
            else:
                if cmd in ["grep", "egrep", "fgrep"] and "--color" not in line:
                    args.append("--color=auto")
                p = subprocess.Popen(
                    args,
                    stdin=subprocess.DEVNULL,
                    preexec_fn=os.setsid if (os.name != 'nt' and hasattr(os, 'setsid')) else None
                )
            background_processes.append({
                "process": p,
                "line": line
            })
            print(f"[백그라운드 작업 시작] PID: {p.pid} - {line}")
            return

        if should_capture:
            result = subprocess.run(
                args,
                text=True,
                capture_output=True,
            )
            make_readable_output(cmd, result)
        else:
            if has_pipeline_or_redir:
                line_to_run = inject_grep_color(line)
                subprocess.run(
                    line_to_run,
                    shell=True,
                    stdin=sys.stdin,
                    stdout=sys.stdout,
                    stderr=sys.stderr,
                )
            else:
                if cmd == "ls" and "--color" not in line and os.name != 'nt':
                    if len(args) == 1:
                        args.append("--color=auto")
                    elif "--color=auto" not in args:
                        args.append("--color=auto")

                if cmd in ["grep", "egrep", "fgrep"] and "--color" not in line:
                    args.append("--color=auto")

                subprocess.run(
                    args,
                    stdin=sys.stdin,
                    stdout=sys.stdout,
                    stderr=sys.stderr,
                )

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
        cols = app.renderer.output.get_size().columns
    except Exception:
        import shutil
        cols, _ = shutil.get_terminal_size()

    try:
        app = get_app()
        text = app.current_buffer.text.strip()
    except Exception:
        text = ""

    if not text:
        msg = "도움말: help 입력 또는 [F2] 키 | 자동완성: [Ctrl+Space] 또는 [Tab] | 화면 정리 [Ctrl+L] | 쉘 종료: [exit]"
        if len(msg) <= cols - 5:
            return HTML(f"<bottom-toolbar>{msg}</bottom-toolbar>")

        line1 = "도움말: help 입력 또는 [F2] 키 | 자동완성: [Ctrl+Space] 또는 [Tab]"
        line2 = "단축키: 화면 정리 [Ctrl+L] | 쉘 종료: [exit] 입력 또는 [Ctrl+D]"
        if len(line1) > cols - 5:
            line1 = "도움말: help / F2 | 자동완성: Tab"
            line2 = "화면정리: Ctrl+L | 종료: exit"
        if len(line1) > cols - 5:
            return HTML(f"<bottom-toolbar>help / F2: 도움말 | Ctrl+L: 화면정리 | exit: 종료</bottom-toolbar>")
        return HTML(f"<bottom-toolbar>{line1}\n{line2}</bottom-toolbar>")

    words = text.split()
    cmd = words[0]

    def format_toolbar_content(prefix, command_name, info):
        desc = info.get("desc", "")
        params_list = info.get("params", [])
        params = ", ".join(params_list) if params_list else "파라미터 없음"
        example = info.get("example", "")

        # 1-line full text check
        full_text = f"{prefix}{command_name}: {desc} | 파라미터: {params} | 예시: {example}"
        if len(full_text) <= cols - 5:
            return full_text

        # 2-line structure check
        line1 = f"{prefix}{command_name}: {desc}"
        line2 = f"파라미터: {params} | 예시: {example}"

        if len(line2) > cols - 5:
            line2 = f"파라미터: {params}"
        if len(line2) > cols - 5:
            line2 = f"파라미터: {params[:max(10, cols - 15)]}..."
        if len(line2) > cols - 5:
            line2 = ""

        if line2:
            if len(line1) > cols - 5:
                max_desc_len = max(10, cols - len(prefix) - len(command_name) - 10)
                line1 = f"{prefix}{command_name}: {desc[:max_desc_len]}..."
            return f"{line1}\n{line2}"

        # 1-line compressed check
        max_desc_len = max(10, cols - len(prefix) - len(command_name) - 10)
        return f"{prefix}{command_name}: {desc[:max_desc_len]}..."

    if cmd in ALIASES:
        real_cmd = ALIASES[cmd].split()[0]
        real_info = COMMANDS.get(real_cmd)
        prefix = f"단축어: {cmd} → {ALIASES[cmd]} | "
        
        if real_info:
            content = format_toolbar_content(prefix, real_cmd, real_info)
        else:
            line = f"단축 명령어: {cmd} → {ALIASES[cmd]}"
            if len(line) <= cols - 5:
                return HTML(f"<bottom-toolbar>{line}</bottom-toolbar>")
            line1 = f"단축 명령어: {cmd} → {ALIASES[cmd]}"
            line2 = "단축어로 정의된 명령어를 실행합니다."
            if len(line1) > cols - 5:
                line1 = f"{cmd} → {ALIASES[cmd]}"
                line2 = "단축 명령어 실행"
            content = f"{line1}\n{line2}"
        return HTML(f"<bottom-toolbar>{content}</bottom-toolbar>")

    if cmd in COMMANDS:
        content = format_toolbar_content("", cmd, COMMANDS[cmd])
        return HTML(f"<bottom-toolbar>{content}</bottom-toolbar>")

    similar = difflib.get_close_matches(cmd, list(COMMANDS.keys()) + list(ALIASES.keys()), n=1)

    if similar:
        line = f"'{cmd}' 명령어를 찾을 수 없습니다. 혹시 '{similar[0]}'를 입력하려고 했나요?"
        if len(line) <= cols - 5:
            return HTML(f"<bottom-toolbar>{line}</bottom-toolbar>")
        line1 = f"'{cmd}' 명령어를 찾을 수 없습니다."
        line2 = f"혹시 '{similar[0]}'를 입력하려고 했나요?"
        if len(line1) > cols - 5:
            line1 = f"'{cmd}' 찾을 수 없음"
            line2 = f"혹시 '{similar[0]}'?"
        return HTML(f"<bottom-toolbar>{line1}\n{line2}</bottom-toolbar>")

    line = "등록되지 않은 명령어입니다. 리눅스 표준 명령어라면 정상적으로 실행은 가능합니다."
    if len(line) <= cols - 5:
        return HTML(f"<bottom-toolbar>{line}</bottom-toolbar>")
    line1 = "등록되지 않은 명령어입니다."
    line2 = "리눅스 표준 명령어라면 정상적으로 실행은 가능합니다."
    if len(line1) > cols - 5:
        return HTML(f"<bottom-toolbar>등록되지 않은 명령어 (실행 시도함)</bottom-toolbar>")
    return HTML(f"<bottom-toolbar>{line1}\n{line2}</bottom-toolbar>")


def check_background_jobs():
    global background_processes
    still_running = []
    for job in background_processes:
        p = job["process"]
        cmd_line = job["line"]
        ret = p.poll()
        if ret is not None:
            print(f"\n[백그라운드 작업 완료] PID: {p.pid} (종료 코드: {ret}) - {cmd_line}")
        else:
            still_running.append(job)
    background_processes = still_running


def main():
    style = Style.from_dict({
        "prompt-cyan": "ansicyan bold",
        "prompt-path": "ansigreen bold",
        "bottom-toolbar": "reverse",
    })

    kb = KeyBindings()

    @kb.add("c-l")
    def _(event):
        os.system("cls" if os.name == "nt" else "clear")

    @kb.add("f2")
    def _(event):
        print_help()

    @kb.add("c-space")
    def _(event):
        event.app.current_buffer.start_completion(select_first=False)

    def get_prompt():
        try:
            app = get_app()
            cols = app.renderer.output.get_size().columns
        except Exception:
            import shutil
            cols, _ = shutil.get_terminal_size()
            
        cwd = os.getcwd()
        home = str(Path.home())
        username = getpass.getuser()
        
        # Shorten home directory
        if cwd.startswith(home):
            display_path = "~" + cwd[len(home):]
        else:
            display_path = cwd

        # Calculate max path length dynamically
        max_path_len = cols - len(username) - 10
        if max_path_len < 15:
            max_path_len = 15
            
        # Shorten path if it exceeds max path length or 30 characters
        if len(display_path) > max_path_len or len(display_path) > 30:
            parts = display_path.split(os.sep)
            if len(parts) > 3:
                sep = os.sep
                display_path = f"...{sep}{parts[-2]}{sep}{parts[-1]}"

        # Always return Kali Linux style 2-line prompt
        return HTML(
            f"<prompt-cyan>┌─[</prompt-cyan>"
            f"<prompt-path>{username}:{display_path}</prompt-path>"
            f"<prompt-cyan>]</prompt-cyan>\n"
            f"<prompt-cyan>└─$ </prompt-cyan>"
        )

    session = PromptSession(
        message=get_prompt,
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
        check_background_jobs()

        try:
            line = session.prompt()

        except KeyboardInterrupt:
            print("\nCtrl+C 입력됨. 종료하려면 exit를 입력하세요.")
            continue

        except EOFError:
            print("\n커스텀 쉘을 종료합니다.")
            break

        line = line.strip()

        if not line:
            continue

        # 환경 변수 및 로컬 변수 치환 ($VAR 및 ${VAR} 형태)
        line = expand_variables(line)

        # 백그라운드 실행 여부 파악 (& 기호)
        is_background = False
        if line.endswith("&"):
            is_background = True
            line = line[:-1].strip()

        line = expand_alias(line)

        try:
            args = shlex.split(line)
        except ValueError:
            print("오류: 따옴표 사용이 올바르지 않습니다.")
            continue

        if not args:
            continue

        # 백그라운드 파싱으로 인해 args 내부에서 & 제거
        if is_background and args and args[-1] == "&":
            args = args[:-1]

        if not args:
            continue

        # 로컬 변수 바인딩 처리 (예: MY_VAR=hello)
        if "=" in args[0]:
            parts = args[0].split("=", 1)
            import re
            if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', parts[0]):
                key, val = parts[0], parts[1]
                local_variables[key] = val
                print(f"변수 설정 완료 (로컬 스코프): {key} = '{val}'")
                continue

        # export/history/klas 등도 builtin으로 취급할 수 있도록 명시적으로 포함
        if args[0] in COMMANDS or args[0] in ["export", "history", "klas"]:
            handled = run_builtin(args, session=session)

            if not handled:
                run_external(line, args, is_background=is_background)
        else:
            run_external(line, args, is_background=is_background)


if __name__ == "__main__":
    main()

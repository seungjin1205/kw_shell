# Beginner Shell

리눅스 초보자를 위한 커스텀 쉘 프로젝트입니다.

## 프로젝트 소개

이 프로젝트는 리눅스 명령어 사용에 익숙하지 않은 초보자를 위해 만든 커스텀 쉘입니다.

주요 목표는 다음과 같습니다.

- 명령어 자동완성
- 명령어 파라미터 미리보기
- 초보자 친화적인 출력 설명
- 단축 명령어 제공
- 기본적인 리눅스 명령어 실행

## 실행 환경

- Ubuntu Linux
- Python 3
- prompt_toolkit

## 설치 방법

```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv -y

## 실행 방법

python3 -m venv venv
source venv/bin/activate
pip install prompt_toolkit

python3 beginner_shell.py

## 사용 예시

help
explain grep
ls
ll
df -h
free -h
exit
